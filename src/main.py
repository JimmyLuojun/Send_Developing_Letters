# src/main.py
"""
Main orchestration script for the Send_Developing_Letters project.
Refactored to use modular components, .env for secrets, and config.ini for settings.

Current time: Sunday, March 30, 2025 at 8:26:49 AM (User Context).
"""

from datetime import datetime
import logging
import os
import sys
import time
import configparser
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd # Import pandas for duplicate checking
from typing import List, Optional # Import typing for type hints

# --- Determine Project Root ---
# Assumes main.py is in the src/ directory relative to the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
print(f"Project Root determined as: {PROJECT_ROOT}") # Initial print before logging

# --- Load .env file ---
# Looks for .env in current dir or parent dirs, explicitly point to project root's .env
env_path = PROJECT_ROOT / '.env'
if load_dotenv(dotenv_path=env_path):
    print(f"Loaded environment variables from: {env_path}")
else:
    print(f"Warning: .env file not found at {env_path}. Proceeding without it (secrets must be set via environment).")

# --- Setup Logging (Needs to happen after env load but before most logic) ---
# Import setup_logging *after* potentially loading dotenv
# Use a try-except block in case utils or setup_logging itself fails
try:
    from src.utils import setup_logging
    log_dir = PROJECT_ROOT / (os.getenv('LOG_DIR_NAME') or "logs") # Allow overriding log dir name via env
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
        LetterGenerationInput # Now a dataclass
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
    from src.utils import save_processed_data # Use the specific save function
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
    """Encapsulates the main processing workflow."""
    start_time = time.time()
    logging.info(f"Starting Send_Developing_Letters process at {time.strftime('%Y-%m-%d %H:%M:%S')}")

    config: Optional[configparser.ConfigParser] = None
    # Declare variable for partial results handling in finally block
    companies_processed_this_run: List[TargetCompanyData] = []
    processed_data_path: Optional[Path] = None # Initialize path variable

    try:
        # --- Load Configuration ---
        config_file_path = PROJECT_ROOT / 'config.ini'
        config = load_configuration(config_file_path)
        if config is None:
             logging.critical("config.ini could not be loaded. Process cannot continue.")
             sys.exit("Error: Could not load config.ini. See logs for details.")
             # --- ADDED RETURN ---
             return # Ensures execution stops here if sys.exit is mocked
             # --- END ADDITION ---

        # --- Refine Logging Level (Check config as fallback) ---
        # Use initial log_level_str from .env/default as fallback
        initial_log_level = os.getenv('LOG_LEVEL', 'INFO')
        config_log_level = config.get('APP_SETTINGS', 'log_level', fallback=initial_log_level)
        if config_log_level.upper() != initial_log_level.upper():
             logging.info(f"Updating log level based on config.ini to: {config_log_level.upper()}")
             try:
                  logging.getLogger().setLevel(config_log_level.upper())
             except ValueError:
                  logging.warning(f"Invalid log level '{config_log_level}' in config.ini. Keeping level '{initial_log_level}'.")

        # --- Extract Config Values ---
        # Get Paths section, default to empty dict if missing
        paths_config = config['PATHS'] if 'PATHS' in config else {}
        skyfend_business_path = PROJECT_ROOT / paths_config.get('skyfend_business_doc', 'DEFAULT_PATH_SF_DOC_MISSING')
        company_data_path = PROJECT_ROOT / paths_config.get('company_data_excel', 'DEFAULT_PATH_COMP_XLSX_MISSING')
        processed_data_path = PROJECT_ROOT / paths_config.get('processed_data_excel', 'data/processed/processed_companies.xlsx') # Provide a default
        product_brochure_path = PROJECT_ROOT / paths_config.get('product_brochure_pdf', 'DEFAULT_PATH_BROCHURE_MISSING')
        unified_images_dir = PROJECT_ROOT / paths_config.get('unified_images_dir', 'DEFAULT_PATH_IMAGES_MISSING')

        # Get EMAIL section
        gmail_config = config['EMAIL'] if 'EMAIL' in config else {}
        credentials_json_path_str = os.getenv('GMAIL_CREDENTIALS_PATH') or gmail_config.get('credentials_json_path')
        if not credentials_json_path_str:
             raise ValueError("Gmail credentials path not found in .env (GMAIL_CREDENTIALS_PATH) or config.ini ([EMAIL] credentials_json_path)")
        credentials_json_path = PROJECT_ROOT / credentials_json_path_str
        token_json_path_str = os.getenv('GMAIL_TOKEN_PATH') or gmail_config.get('token_json_path', 'token.json') # Default filename
        token_json_path = PROJECT_ROOT / token_json_path_str
        sender_email = os.getenv('SENDER_EMAIL') or gmail_config.get('sender_email')
        if not sender_email:
             raise ValueError("Sender email not found in .env (SENDER_EMAIL) or config.ini ([EMAIL] sender_email)")

        # Get API section
        api_config = config['API'] if 'API' in config else {}
        deepseek_api_key = os.getenv('DEEPSEEK_API_KEY') or api_config.get('deepseek_api_key')
        if not deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY not found in environment variables or config.ini")

        # Get other settings with fallbacks
        email_defaults = config['EMAIL_DEFAULTS'] if 'EMAIL_DEFAULTS' in config else {}
        scraper_config = config['WEBSITE_SCRAPER'] if 'WEBSITE_SCRAPER' in config else {}
        api_client_config = config['API_CLIENT'] if 'API_CLIENT' in config else {}

        max_images_per_email = email_defaults.getint('max_images_per_email', 3)
        max_content_length = scraper_config.getint('max_content_length', 3000)
        scraper_timeout = scraper_config.getint('timeout', 20)
        api_request_timeout = api_client_config.getint('request_timeout', 45)


        # --- Initialize Services/Clients ---
        logging.info("Initializing API clients and generators...")
        deepseek_client = DeepSeekClient(api_key=deepseek_api_key, request_timeout=api_request_timeout)
        letter_generator = DeepSeekLetterGenerator(deepseek_client=deepseek_client)

        # --- Initial Data Loading ---
        logging.info("Loading initial data...")
        if not skyfend_business_path.is_file():
            raise FileNotFoundError(f"Skyfend business document not found at: {skyfend_business_path}")
        if not company_data_path.is_file():
             raise FileNotFoundError(f"Company data Excel file not found at: {company_data_path}")

        skyfend_desc = read_skyfend_business(skyfend_business_path)
        if not skyfend_desc:
             raise ValueError("Failed to read Skyfend business description. Cannot proceed.")
        skyfend_info = MyOwnCompanyBusinessData(description=skyfend_desc)

        companies: List[TargetCompanyData] = read_company_data(company_data_path)
        if not companies:
             logging.warning("No valid company data loaded from Excel file. Check file content and logs.")
             print("No companies found to process. Exiting.")
             return # Exit gracefully if no companies

        logging.info(f"Loaded Skyfend info and data for {len(companies)} target companies.")

        # --- Load previously processed data for duplicate checking ---
        processed_companies_df = pd.DataFrame(columns=['recipient_email'])
        if processed_data_path.exists():
             try:
                  processed_companies_df = pd.read_excel(processed_data_path)
                  if 'recipient_email' in processed_companies_df.columns:
                       processed_companies_df['recipient_email'] = processed_companies_df['recipient_email'].astype(str).str.strip().str.lower()
                       logging.info(f"Loaded {len(processed_companies_df)} records from previous run: {processed_data_path}")
                  else:
                       logging.warning(f"'recipient_email' column not found in {processed_data_path}. Cannot check for duplicates accurately.")
                       processed_companies_df = pd.DataFrame(columns=['recipient_email']) # Ensure it's an empty DF
             except Exception as e:
                  logging.error(f"Error reading previously processed data file {processed_data_path}: {e}. Proceeding without duplicate check.", exc_info=True)
                  processed_companies_df = pd.DataFrame(columns=['recipient_email'])

        already_processed_emails = set(processed_companies_df['recipient_email']) if 'recipient_email' in processed_companies_df.columns else set()

        # --- Main Processing Loop ---
        # companies_processed_this_run initialized earlier
        for i, company in enumerate(companies):
            start_loop_time = time.time()
            logging.info(f"--- Processing company {i+1}/{len(companies)}: {company.company_name} ---")
            should_record_attempt = True

            try:
                # 1. Check if should process based on flag
                if not company.should_process:
                    logging.info(f"Skipping '{company.company_name}' because 'process' flag is not 'yes'.")
                    company.update_status("Skipped: Process flag")
                    # No need to record if skipped by design
                    should_record_attempt = False
                    continue

                # 2. Check if already processed
                current_email_lower = company.recipient_email.strip().lower()
                if current_email_lower in already_processed_emails:
                     logging.info(f"Skipping '{company.company_name}' ({company.recipient_email}) as email already processed.")
                     company.update_status("Skipped: Already processed")
                     should_record_attempt = False
                     continue

                # 3. Validate Email Format (Basic)
                if '@' not in company.recipient_email or '.' not in company.recipient_email.split('@')[-1]:
                     logging.warning(f"Skipping '{company.company_name}' due to invalid email format: {company.recipient_email}")
                     company.update_status("Skipped: Invalid email format")
                     should_record_attempt = False
                     continue

                # 4. Fetch Website Content
                logging.info(f"Fetching website content for: {company.website}")
                website_content = fetch_website_content(company.website, max_content_length, scraper_timeout)
                if website_content is None:
                    logging.warning(f"Setting status due to error fetching website content for '{company.company_name}'.")
                    company.update_status("Error: Failed to fetch website") # Set status before raising
                    raise ValueError("Website fetch failed")

                # 5. Extract Main Business
                logging.info(f"Extracting main business for '{company.company_name}'...")
                extracted_business = deepseek_client.extract_main_business(website_content or "") # Use result directly
                company.main_business = extracted_business if extracted_business else "Not Available"
                if company.main_business == "Not Available":
                    logging.warning(f"Could not extract main business for '{company.company_name}'.")

                # 6. Identify Cooperation Points
                logging.info(f"Identifying cooperation points for '{company.company_name}'...")
                extracted_points = deepseek_client.identify_cooperation_points(
                    skyfend_business_desc=skyfend_info.description,
                    target_company_desc=company.main_business # Use potentially updated main_business
                )
                company.cooperation_points_str = extracted_points if extracted_points and "No cooperation points identified" not in extracted_points else "Not Available"
                if company.cooperation_points_str == "Not Available":
                     logging.warning(f"Could not identify cooperation points for '{company.company_name}'.")

                # 7. Generate Developing Letter
                logging.info(f"Generating letter for '{company.company_name}'...")
                contact_person = company.contact_person or company.company_name # Use company name if contact empty
                # Ensure cooperation points are passed, even if "Not Available"
                letter_input = LetterGenerationInput(
                     cooperation_points=company.cooperation_points_str,
                     target_company_name=company.company_name,
                     contact_person_name=contact_person
                 )
                generated_letter: DevelopingLetter = letter_generator.generate(letter_input)
                # Check for error marker in the *returned* letter object
                if "Error generating letter content" in generated_letter.body_html:
                     logging.error(f"Failed to generate valid letter content for {company.company_name}.")
                     company.set_letter_content(generated_letter.subject, generated_letter.body_html) # Save error content
                     company.update_status("Error: Letter generation failed")
                     raise ValueError("Letter generation failed")
                else:
                     company.set_letter_content(generated_letter.subject, generated_letter.body_html)

                # 8. Select Relevant Images
                logging.info(f"Selecting images for '{company.company_name}'...")
                selected_images: List[Path] = select_relevant_images(
                    image_dir=unified_images_dir,
                    email_body=company.generated_letter_body or "", # Handle potential None
                    company_name=company.company_name,
                    max_images=max_images_per_email
                )
                if len(selected_images) != max_images_per_email:
                    logging.warning(f"Could not select exactly {max_images_per_email} images for '{company.company_name}' (found {len(selected_images)}). Skipping email draft.")
                    company.update_status(f"Skipped: Found {len(selected_images)}/{max_images_per_email} images")
                    # Treat as a skippable condition, not a critical error for the whole run
                    should_record_attempt = True # Record the attempt and skip status
                    continue # Skip draft creation for this company

                # 9. Create MIME Email
                logging.info(f"Creating MIME email for '{company.company_name}'...")
                attachments = []
                if product_brochure_path.is_file():
                     attachments = [product_brochure_path]
                else:
                     logging.warning(f"Attachment file not found: {product_brochure_path}. Proceeding without attachment.")

                mime_message = create_mime_email(
                    sender=sender_email,
                    to=company.recipient_email,
                    subject=company.generated_letter_subject or f"Potential Cooperation with {company.company_name}", # Fallback subject
                    body_html=company.generated_letter_body or "<p>Error: Missing body content.</p>", # Fallback body
                    inline_image_paths=selected_images,
                    attachment_paths=attachments
                )

                # 10. Save Email to Drafts
                logging.info(f"Saving email draft for '{company.company_name}'...")
                draft_id = save_email_to_drafts(
                    mime_message=mime_message,
                    credentials_path=str(credentials_json_path),
                    token_path=str(token_json_path)
                    )

                if draft_id:
                    company.set_draft_id(draft_id)
                    company.update_status(f"Success: Draft ID {draft_id}")
                    logging.info(f"Successfully processed and saved draft for {company.company_name}.")
                else:
                    # Error logged within save_email_to_drafts
                    company.update_status("Error: Failed to save draft")
                    raise ValueError("Failed to save draft") # Treat failure to save draft as error

            except Exception as e:
                # Catch errors during the processing of a single company
                logging.error(f"Error processing {company.company_name}: {e}", exc_info=True)
                # Update status if not already specifically set to an Error/Skip status
                if not company.processing_status or not ("Error:" in company.processing_status or "Skipped:" in company.processing_status):
                     company.update_status(f"Error: {type(e).__name__}")
                # Default: log error and continue with next company

            finally:
                # Ensure the company's result (success or failure state) is recorded if not skipped initially
                if should_record_attempt:
                    companies_processed_this_run.append(company)
                loop_duration = time.time() - start_loop_time
                logging.info(f"--- Finished processing {company.company_name} in {loop_duration:.2f}s. Status: {company.processing_status or 'Unknown'} ---")
                # Optional delay between processing companies
                # time.sleep(1)


        # --- Save All Processed Data for this Run ---
        if companies_processed_this_run:
             logging.info(f"Saving results for {len(companies_processed_this_run)} companies processed or skipped this run...")
             save_processed_data(companies_processed_this_run, processed_data_path)
        else:
             logging.info("No companies were processed or recorded in this run.")

    except FileNotFoundError as e:
         logging.critical(f"CRITICAL ERROR: Essential file not found: {e}. Process stopped.", exc_info=True)
         sys.exit(f"Error: File not found - {e}")
    except ValueError as e: # Catch config/setup value errors
         logging.critical(f"CRITICAL ERROR: Configuration or setup issue: {e}. Process stopped.", exc_info=True)
         sys.exit(f"Error: Configuration/Setup - {e}")
    except KeyboardInterrupt:
         logging.warning("Process interrupted by user (Ctrl+C).")
         if processed_data_path and companies_processed_this_run: # Check if variables are defined
              logging.info("Attempting to save partial results before exiting...")
              partial_path = processed_data_path.parent / f"PARTIAL_RESULTS_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
              save_processed_data(companies_processed_this_run, partial_path)
         sys.exit("Process interrupted.")
    except Exception as e:
        # Catch any other unexpected errors during setup or overall process
        logging.critical(f"An unexpected critical error occurred: {e}", exc_info=True)
        if processed_data_path and companies_processed_this_run:
             logging.info("Attempting to save partial results due to critical error...")
             error_path = processed_data_path.parent / f"ERROR_RESULTS_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
             save_processed_data(companies_processed_this_run, error_path)
        sys.exit(f"Critical Error: {e}")
    finally:
        end_time = time.time()
        logging.info(f"Total process finished or terminated in {end_time - start_time:.2f} seconds.")


# --- Script Entry Point ---
if __name__ == "__main__":
    run_process()