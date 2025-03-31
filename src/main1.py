# src/main1.py
"""
Main orchestration script for the Send_Developing_Letters project.
Refactored with multi-language support including email TLD check.
Reads optional 'Language' column from Excel, otherwise detects language.
Generates letters in the target language.

Current time: Monday, March 31, 2025 at 03:06:59 AM (User Context).
"""

from datetime import datetime
import logging
import os
import sys
import time
import configparser
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd  # Import pandas for duplicate checking
from typing import List, Optional  # Import typing for type hints

# Assuming determine_language now accepts recipient_email
from src.language_detector import determine_language

# --- Determine Project Root ---
try:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
except NameError:
    # Fallback for interactive environments or alternative execution contexts
    PROJECT_ROOT = Path('.').resolve()
print(f"Project Root determined as: {PROJECT_ROOT}")  # Initial print before logging

# --- Load .env file ---
env_path = PROJECT_ROOT / '.env'
if load_dotenv(dotenv_path=env_path):
    print(f"Loaded environment variables from: {env_path}")
else:
    print(f"Warning: .env file not found at {env_path}. Proceeding without it (secrets must be set via environment).")

# --- Setup Logging (Needs to happen after env load but before most logic) ---
# Import setup_logging *after* potentially loading dotenv
# Use a try-except block in case utils or setup_logging itself fails
try:
    # Use the exposed function from utils package
    from src.utils import setup_logging
    log_dir = PROJECT_ROOT / (os.getenv('LOG_DIR_NAME') or "logs")  # Allow overriding log dir name via env
    # Determine log level: Check .env first, then default to INFO. Config is checked later.
    log_level_str = os.getenv('LOG_LEVEL', 'INFO')
    setup_logging(log_dir, log_level=log_level_str)
except Exception as log_e:
    # Use basic print for critical early errors as logging might not be working
    print(f"CRITICAL: Failed to import or set up logging from src.utils. Error: {log_e}", file=sys.stderr)
    # Fallback to basic logging config
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.error(f"Initial logging setup failed, using basic console logging. Error: {log_e}", exc_info=True)

# --- Import Project Modules (after path setup and initial logging) ---
try:
    from src.core import (
        MyOwnCompanyBusinessData,
        TargetCompanyData,
        DevelopingLetter,
        LetterGenerationInput  # Now a dataclass
    )
    from src.data_access import (
        read_skyfend_business,
        read_company_data,
        fetch_website_content
    )
    from src.api_clients import DeepSeekClient
    from src.letter_generator import DeepSeekLetterGenerator
    from src.email_handler import (
        create_mime_email,
        select_relevant_images,
        save_email_to_drafts
    )
    # Use the exposed function from utils package
    from src.utils import save_processed_data
except ImportError as import_err:
    # Use logging if available, otherwise print
    logging.critical(f"Failed to import necessary project modules: {import_err}. Ensure PYTHONPATH or project structure is correct.", exc_info=True)
    sys.exit(f"Import Error: {import_err}")

# --- Configuration Loading Function ---
def load_configuration(config_path: Path) -> Optional[configparser.ConfigParser]:
    """Loads configuration from the specified .ini file."""
    if not config_path.is_file():
        logging.error(f"Configuration file not found at: {config_path}")
        return None
    try:
        config = configparser.ConfigParser(interpolation=None)
        config.read(config_path, encoding='utf-8')
        logging.info(f"Configuration loaded from {config_path}")
        return config
    except configparser.Error as e:
        logging.error(f"Error parsing configuration file {config_path}: {e}", exc_info=True)
        return None
    except Exception as e:
        logging.error(f"Unexpected error loading configuration {config_path}: {e}", exc_info=True)
        return None

# --- Main Application Logic ---
def run_process():
    """Encapsulates the main processing workflow with language detection."""
    start_time = time.time()
    logging.info(f"Starting Send_Developing_Letters process (Multi-Language) at {time.strftime('%Y-%m-%d %H:%M:%S')}")

    config: Optional[configparser.ConfigParser] = None
    # Declare variable for partial results handling in finally block
    companies_processed_this_run: List[TargetCompanyData] = []
    processed_data_path: Optional[Path] = None  # Initialize path variable

    try:
        # --- Load Configuration ---
        config_file_path = PROJECT_ROOT / 'config.ini'
        config = load_configuration(config_file_path)
        if config is None:
            logging.critical("config.ini could not be loaded. Process cannot continue.")
            # Use return instead of sys.exit to allow potential testing without exiting interpreter
            print("Error: Could not load config.ini. See logs for details.")
            return

        # --- Refine Logging Level (Check config as fallback) ---
        initial_log_level = os.getenv('LOG_LEVEL', 'INFO')
        config_log_level = config.get('APP_SETTINGS', 'log_level', fallback=initial_log_level)
        if config_log_level.upper() != initial_log_level.upper():
            logging.info(f"Updating log level based on config.ini to: {config_log_level.upper()}")
            try:
                logging.getLogger().setLevel(config_log_level.upper())
            except ValueError:
                logging.warning(f"Invalid log level '{config_log_level}' in config.ini. Keeping level '{initial_log_level}'.")

        # --- Extract Config Values ---
        paths_config = config['PATHS'] if 'PATHS' in config else {}
        skyfend_business_path = PROJECT_ROOT / paths_config.get('skyfend_business_doc', 'DEFAULT_PATH_SF_DOC_MISSING')
        company_data_path = PROJECT_ROOT / paths_config.get('company_data_excel', 'DEFAULT_PATH_COMP_XLSX_MISSING')
        processed_data_path_str = paths_config.get('processed_data_excel', 'data/processed/processed_companies.xlsx') # Default relative path
        processed_data_path = PROJECT_ROOT / processed_data_path_str
        product_brochure_path_str = paths_config.get('product_brochure_pdf', 'DEFAULT_PATH_BROCHURE_MISSING')
        product_brochure_path = PROJECT_ROOT / product_brochure_path_str if product_brochure_path_str != 'DEFAULT_PATH_BROCHURE_MISSING' else None
        unified_images_dir_str = paths_config.get('unified_images_dir', 'DEFAULT_PATH_IMAGES_MISSING')
        unified_images_dir = PROJECT_ROOT / unified_images_dir_str if unified_images_dir_str != 'DEFAULT_PATH_IMAGES_MISSING' else None

        # Validate essential paths obtained from config before proceeding
        if not skyfend_business_path.is_file():
            raise FileNotFoundError(f"Skyfend business document not found at configured path: {skyfend_business_path}")
        if not company_data_path.is_file():
            raise FileNotFoundError(f"Company data Excel file not found at configured path: {company_data_path}")
        if not unified_images_dir or not unified_images_dir.is_dir():
             logging.warning(f"Unified images directory not found or not configured: {unified_images_dir}. Image selection will likely fail.")
             # Decide if this is critical - maybe proceed but warn? For now, warning.
             # raise FileNotFoundError(f"Unified images directory not found or invalid: {unified_images_dir}")
        if product_brochure_path and not product_brochure_path.is_file():
            logging.warning(f"Product brochure PDF not found at configured path: {product_brochure_path}. Proceeding without attachment.")
            product_brochure_path = None # Ensure it's None if not found

        # Get EMAIL section
        gmail_config = config['EMAIL'] if 'EMAIL' in config else {}
        # Prioritize .env for credentials path, fallback to config.ini
        credentials_json_path_str = os.getenv('GMAIL_CREDENTIALS_PATH') or gmail_config.get('credentials_json_path')
        if not credentials_json_path_str:
            raise ValueError("Gmail credentials path missing. Set GMAIL_CREDENTIALS_PATH in .env or credentials_json_path in [EMAIL] section of config.ini")
        credentials_json_path = PROJECT_ROOT / credentials_json_path_str
        if not credentials_json_path.is_file():
             raise FileNotFoundError(f"Gmail credentials file not found at: {credentials_json_path}")

        # Prioritize .env for token path, fallback to config.ini with default filename
        token_json_path_str = os.getenv('GMAIL_TOKEN_PATH') or gmail_config.get('token_json_path', 'token.json') # Default filename 'token.json'
        token_json_path = PROJECT_ROOT / token_json_path_str # Path relative to project root

        # Prioritize .env for sender email, fallback to config.ini
        sender_email = os.getenv('SENDER_EMAIL') or gmail_config.get('sender_email')
        if not sender_email:
            raise ValueError("Sender email missing. Set SENDER_EMAIL in .env or sender_email in [EMAIL] section of config.ini")

        # Get API section
        api_config = config['API'] if 'API' in config else {}
        # Prioritize .env for API key, fallback to config.ini
        deepseek_api_key = os.getenv('DEEPSEEK_API_KEY') or api_config.get('deepseek_api_key')
        if not deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY missing. Set in environment variables or deepseek_api_key in [API] section of config.ini")

        # Get other settings with fallbacks
        app_settings = config['APP_SETTINGS'] if 'APP_SETTINGS' in config else {}
        email_defaults = config['EMAIL_DEFAULTS'] if 'EMAIL_DEFAULTS' in config else {}
        scraper_config = config['WEBSITE_SCRAPER'] if 'WEBSITE_SCRAPER' in config else {}
        api_client_config = config['API_CLIENT'] if 'API_CLIENT' in config else {}
        lang_config = config['LANGUAGE_SETTINGS'] if 'LANGUAGE_SETTINGS' in config else {}

        # Extract specific settings with defaults
        default_language = lang_config.get('default_language', 'en').lower()
        logging.info(f"Default language set to: {default_language}")
        max_images_per_email = email_defaults.getint('max_images_per_email', 3)
        max_content_length = scraper_config.getint('max_content_length', 5000) # Increased default
        scraper_timeout = scraper_config.getint('timeout', 30) # Increased default
        api_request_timeout = api_client_config.getint('request_timeout', 60) # Increased default
        process_delay = app_settings.getfloat('process_delay_seconds', 0.5) # Optional delay

        # --- Initialize Services/Clients ---
        logging.info("Initializing API clients and generators...")
        # Pass relevant config directly if needed, e.g., timeout
        deepseek_client = DeepSeekClient(api_key=deepseek_api_key, request_timeout=api_request_timeout)
        letter_generator = DeepSeekLetterGenerator(deepseek_client=deepseek_client)

        # --- Initial Data Loading ---
        logging.info("Loading initial data...")
        # File existence checked earlier during config extraction
        skyfend_desc = read_skyfend_business(skyfend_business_path)
        if not skyfend_desc:
            # This should ideally not happen if FileNotFoundError is caught, but check defensively
            raise ValueError("Failed to read Skyfend business description. Cannot proceed.")
        skyfend_info = MyOwnCompanyBusinessData(description=skyfend_desc)

        companies: List[TargetCompanyData] = read_company_data(company_data_path)
        if not companies:
            logging.warning("No valid company data objects created from Excel file. Check file content and logs.")
            print("No companies found to process. Exiting.")
            return  # Exit gracefully if no companies

        logging.info(f"Loaded Skyfend info and {len(companies)} company data objects.")

        # --- Load previously processed data for duplicate checking ---
        processed_companies_df = pd.DataFrame(columns=['recipient_email'])
        already_processed_emails = set()
        if processed_data_path.exists():
            try:
                processed_companies_df = pd.read_excel(processed_data_path)
                if 'recipient_email' in processed_companies_df.columns:
                    # Convert to string, strip whitespace, lowercase, handle potential NaN/None
                    processed_companies_df.dropna(subset=['recipient_email'], inplace=True)
                    already_processed_emails = set(processed_companies_df['recipient_email'].astype(str).str.strip().str.lower())
                    logging.info(f"Loaded {len(already_processed_emails)} unique emails from previous run: {processed_data_path}")
                else:
                    logging.warning(f"'recipient_email' column not found in {processed_data_path}. Cannot check for duplicates accurately.")
            except Exception as e:
                logging.error(f"Error reading previously processed data file {processed_data_path}: {e}. Proceeding without duplicate check.", exc_info=True)
        else:
             logging.info(f"Processed data file not found at {processed_data_path}. Will start fresh.")


        # --- Main Processing Loop ---
        # companies_processed_this_run initialized earlier
        for i, company in enumerate(companies):
            start_loop_time = time.time()
            logging.info(f"--- Processing company {i+1}/{len(companies)}: {company.company_name} ({company.recipient_email}) ---")
            # Assume we should record unless explicitly skipped by flags/duplicate checks
            should_record_attempt = True
            website_content: Optional[str] = None  # Reset for each company

            try:
                # 1. Check if should process based on flag (using the property)
                if not company.should_process:
                    logging.info(f"Skipping '{company.company_name}' because 'process' flag is not 'yes' (value: '{company.process_flag}').")
                    company.update_status("Skipped: Process flag")
                    should_record_attempt = False # Don't record intentionally skipped items
                    continue

                # 2. Check if already processed (using the loaded set)
                current_email_lower = company.recipient_email.strip().lower()
                if not current_email_lower:
                     logging.warning(f"Skipping '{company.company_name}' due to empty email address.")
                     company.update_status("Skipped: Empty email")
                     should_record_attempt = False
                     continue

                if current_email_lower in already_processed_emails:
                    logging.info(f"Skipping '{company.company_name}' ({company.recipient_email}) as email already processed.")
                    company.update_status("Skipped: Already processed")
                    should_record_attempt = False # Don't record duplicates
                    continue

                # 3. Validate Email Format (Basic) - Re-check just in case
                if '@' not in current_email_lower or '.' not in current_email_lower.split('@')[-1]:
                    logging.warning(f"Skipping '{company.company_name}' due to invalid email format: {company.recipient_email}")
                    company.update_status("Skipped: Invalid email format")
                    should_record_attempt = False # Don't record invalid emails
                    continue

                # 4. Fetch Website Content
                if not company.website or not company.website.startswith(('http://', 'https://')):
                    logging.warning(f"Skipping website fetch for '{company.company_name}' due to invalid or missing URL: {company.website}")
                    website_content = None # Ensure content is None if URL is bad
                    # Decide if this is fatal for the company - maybe allow proceeding without content?
                    # For now, let's try to proceed, language/content steps will handle None
                else:
                    logging.info(f"Fetching website content for: {company.website}")
                    website_content = fetch_website_content(company.website, max_content_length, scraper_timeout)
                    if website_content is None:
                        logging.warning(f"Website content could not be fetched for '{company.company_name}'. Proceeding without website content.")
                        # Don't raise error, allow continuation, but content-dependent steps will be affected

                # --- 5. Determine Target Language ---
                # Check if manually specified in Excel first
                final_target_language = company.target_language
                detection_source = "Manual (Excel)"

                if final_target_language is None:
                    logging.info(f"No language specified in input for {company.company_name}. Detecting...")
                    detection_source = "Auto-detection"
                    try:
                        # *** MODIFIED CALL TO determine_language ***
                        final_target_language = determine_language(
                            content=website_content, # Pass content (can be None)
                            url=company.website,     # Pass URL (can be None/invalid)
                            recipient_email=company.recipient_email, # Pass recipient email
                            default_lang=default_language
                        )
                        # *** END MODIFIED CALL ***
                    except Exception as lang_e:
                        logging.error(f"Error during language determination for {company.company_name}: {lang_e}. Falling back to default '{default_language}'.", exc_info=True)
                        final_target_language = default_language
                        detection_source = "Error (fallback)"

                # Store the final language back on the object (even if it was manual)
                # Ensure it's lowercase for consistency
                company.target_language = final_target_language.lower()
                logging.info(f"Using target language '{company.target_language}' for {company.company_name} (Source: {detection_source}).")
                # --- End Language Determination ---


                # --- Content Dependent Steps (only if content was fetched) ---
                if website_content:
                    # 6. Extract Main Business
                    logging.info(f"Extracting main business for '{company.company_name}'...")
                    extracted_business = deepseek_client.extract_main_business(website_content)
                    company.main_business = extracted_business if extracted_business else "Not Available"
                    if company.main_business == "Not Available":
                        logging.warning(f"Could not extract main business for '{company.company_name}'.")

                    # 7. Identify Cooperation Points
                    # Requires main business, proceed even if "Not Available" to allow letter gen
                    logging.info(f"Identifying cooperation points for '{company.company_name}'...")
                    extracted_points = deepseek_client.identify_cooperation_points(
                        skyfend_business_desc=skyfend_info.description,
                        target_company_desc=company.main_business # Use potentially "Not Available"
                    )
                    # Filter out placeholder negative responses from API
                    if extracted_points and "no cooperation points identified" not in extracted_points.lower():
                        company.cooperation_points_str = extracted_points
                    else:
                        company.cooperation_points_str = "Not Available" # Standardize negative/failed result

                    if company.cooperation_points_str == "Not Available":
                        logging.warning(f"Could not identify specific cooperation points for '{company.company_name}'.")
                else:
                    # Handle cases where website content wasn't available
                    logging.warning(f"Skipping business extraction and cooperation point identification for '{company.company_name}' due to missing website content.")
                    company.main_business = "Not Available (No website content)"
                    company.cooperation_points_str = "Not Available (No website content)"
                # --- End Content Dependent Steps ---


                # 8. Generate Developing Letter in Target Language
                logging.info(f"Generating letter in '{company.target_language}'...")
                # Use company name as fallback if contact person is None or empty
                contact_person = company.contact_person or company.company_name
                letter_input = LetterGenerationInput(
                    # Pass cooperation points, even if "Not Available"
                    cooperation_points=company.cooperation_points_str,
                    target_company_name=company.company_name,
                    contact_person_name=contact_person
                )
                generated_letter: DevelopingLetter = letter_generator.generate(
                    input_data=letter_input,
                    target_language=company.target_language  # Pass final language
                )

                # Check for known error markers in the generated content
                if "error generating letter" in generated_letter.body_html.lower() or not generated_letter.subject:
                    logging.error(f"Failed to generate valid letter content/subject for {company.company_name}.")
                    # Store whatever was returned for debugging
                    company.set_letter_content(generated_letter.subject, generated_letter.body_html)
                    company.update_status("Error: Letter generation failed")
                    # Don't raise error here, just record status and continue loop iteration logic
                    # We still want to record this attempt in the output file
                else:
                    company.set_letter_content(generated_letter.subject, generated_letter.body_html)
                    logging.debug(f"Letter content generated successfully for {company.company_name}.")


                # Proceed only if letter generation seemed successful
                if "Error:" not in (company.processing_status or ""):
                    # 9. Select Relevant Images
                    if unified_images_dir: # Only proceed if dir is configured
                        logging.info(f"Selecting images for '{company.company_name}'...")
                        selected_images: List[Path] = select_relevant_images(
                            image_dir=unified_images_dir,
                            email_body=company.generated_letter_body or "", # Handle None body
                            company_name=company.company_name, # Pass for potential keyword matching
                            max_images=max_images_per_email
                        )

                        # Check if *any* images were found if max_images > 0
                        if max_images_per_email > 0 and not selected_images:
                             logging.warning(f"Could not select any images ({max_images_per_email} desired) for '{company.company_name}'. Proceeding without inline images.")
                             selected_images = [] # Ensure it's an empty list
                        elif len(selected_images) < max_images_per_email:
                             logging.warning(f"Selected {len(selected_images)} images, less than desired {max_images_per_email} for '{company.company_name}'.")
                        else:
                             logging.info(f"Selected {len(selected_images)} images.")

                    else:
                         logging.warning("Image directory not configured. Skipping image selection.")
                         selected_images = []


                    # 10. Create MIME Email
                    logging.info(f"Creating MIME email for '{company.company_name}'...")
                    attachments = []
                    if product_brochure_path: # Check if path is valid (not None)
                        attachments = [product_brochure_path]
                    # No warning here if None, handled during config load

                    mime_message = create_mime_email(
                        sender=sender_email,
                        to=company.recipient_email,
                        subject=company.generated_letter_subject or f"Potential Cooperation with {company.company_name}", # Fallback subject
                        body_html=company.generated_letter_body or "<p>Error: Missing body content.</p>", # Fallback body
                        inline_image_paths=selected_images, # Pass potentially empty list
                        attachment_paths=attachments # Pass potentially empty list
                    )

                    # 11. Save Email to Drafts
                    logging.info(f"Saving email draft for '{company.company_name}'...")
                    draft_id = save_email_to_drafts(
                        mime_message=mime_message,
                        credentials_path=str(credentials_json_path),
                        token_path=str(token_json_path) # Pass the path for token refresh/save
                    )

                    if draft_id:
                        company.set_draft_id(draft_id)
                        company.update_status(f"Success: Draft ID {draft_id}")
                        logging.info(f"Successfully processed and saved draft for {company.company_name}.")
                    else:
                        # Error logged within save_email_to_drafts
                        company.update_status("Error: Failed to save draft")
                        # Don't raise, just record status

            except Exception as e:
                # Catch any unexpected errors during a company's processing cycle
                error_msg = f"Error processing {company.company_name}: {type(e).__name__} - {e}"
                logging.error(error_msg, exc_info=True)
                # Update status only if not already set to a specific Error/Skip status
                if not company.processing_status or not ("Error:" in company.processing_status or "Skipped:" in company.processing_status):
                    company.update_status(f"Error: {type(e).__name__}")
                # Ensure this attempt is recorded despite the error
                should_record_attempt = True

            finally:
                # Record the company's final state (Success, Error, Skipped-but-recorded) for this run's output
                if should_record_attempt:
                    # Ensure status is set if somehow missed
                    if not company.processing_status:
                         company.update_status("Unknown")
                         logging.warning(f"Company {company.company_name} finished loop with unknown status.")
                    companies_processed_this_run.append(company)

                loop_duration = time.time() - start_loop_time
                logging.info(f"--- Finished processing {company.company_name} in {loop_duration:.2f}s. Status: {company.processing_status or 'Unknown'} ---")

                # Optional delay between processing companies
                if process_delay > 0:
                     logging.debug(f"Waiting for {process_delay}s before next company...")
                     time.sleep(process_delay)

        # --- Save All Processed Data for this Run ---
        if companies_processed_this_run:
            logging.info(f"Attempting to save results for {len(companies_processed_this_run)} companies processed or recorded in this run...")
            # Make sure processed_data_path is defined
            if processed_data_path:
                 save_processed_data(companies_processed_this_run, processed_data_path)
            else:
                 logging.error("Output path for processed data is not defined. Cannot save results.")
        else:
            logging.info("No company results were marked for recording in this run.")

    except FileNotFoundError as e:
        # Catch critical file not found errors during setup
        logging.critical(f"CRITICAL ERROR: Essential file not found: {e}. Process stopped.", exc_info=True)
        print(f"CRITICAL ERROR: File not found - {e}. Check config.ini paths and file existence.", file=sys.stderr)
        # sys.exit simulation for potential testing
        return # Stop execution
    except ValueError as e:
        # Catch critical configuration value errors during setup
        logging.critical(f"CRITICAL ERROR: Configuration or setup issue: {e}. Process stopped.", exc_info=True)
        print(f"CRITICAL ERROR: Configuration/Setup - {e}. Check config.ini and .env settings.", file=sys.stderr)
        return # Stop execution
    except KeyboardInterrupt:
        logging.warning("Process interrupted by user (Ctrl+C).")
        # Attempt to save partial results if any were recorded
        if processed_data_path and companies_processed_this_run:
            logging.info("Attempting to save partial results before exiting...")
            partial_path = processed_data_path.parent / f"PARTIAL_RESULTS_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            save_processed_data(companies_processed_this_run, partial_path)
        print("Process interrupted by user.")
        # Don't sys.exit here to allow cleanup if called from another script
        return # Stop execution
    except Exception as e:
        # Catch any other unexpected critical errors during setup or overall process flow
        logging.critical(f"An unexpected critical error occurred: {e}", exc_info=True)
        print(f"CRITICAL UNEXPECTED ERROR: {e}", file=sys.stderr)
        # Attempt to save partial results if possible
        if processed_data_path and companies_processed_this_run:
            logging.info("Attempting to save partial results due to critical error...")
            error_path = processed_data_path.parent / f"ERROR_RESULTS_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            save_processed_data(companies_processed_this_run, error_path)
        # Don't sys.exit here
        return # Stop execution
    finally:
        # Log total time regardless of success or failure
        end_time = time.time()
        duration = end_time - start_time
        logging.info(f"Total process finished or terminated in {duration:.2f} seconds.")
        print(f"Total process duration: {duration:.2f} seconds.")

# --- Script Entry Point ---
if __name__ == "__main__":
    run_process()