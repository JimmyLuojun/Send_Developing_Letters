# src/main.py
import os
import logging
from dotenv import load_dotenv
import requests
import datetime
import pathlib  # Import pathlib
from openai import OpenAI

# --- Project Root (using pathlib) ---
PROJECT_ROOT = pathlib.Path(__file__).parent.parent

from src.models.extract_company_data import extract_company_data
from src.data.skyfend_business import read_skyfend_business
from src.models.business_extraction import extract_main_business
from src.models.identify_cooperation_points import identify_cooperation_points
from src.utils.generate_developing_letters import generate_developing_letter
# from src.utils.format_and_send_email import format_and_send_email  # Not used
from src.utils.save_email_to_drafts import save_email_to_drafts, save_data_to_excel

# --- Load environment variables ---
load_dotenv()

# --- Configuration (PATHS SHOULD BE ABSOLUTE OR RELATIVE TO THE PROJECT ROOT) ---
EXCEL_FILE_PATH = PROJECT_ROOT / "data" / "raw" / "test_to_read_website.xlsx"
SKYFEND_BUSINESS_PATH = PROJECT_ROOT / "data" / "raw" / "test_main Business of Skyfend.docx"
PROCESSED_EXCEL_FILE_PATH = PROJECT_ROOT / "data" / "processed" / "saving_company_data_after_creating_letters.xlsx" # New file path

API_KEY = os.getenv("API_KEY")  # Get API key from .env
GMAIL_ACCOUNT = os.getenv("GMAIL_ACCOUNT")  #  Your Gmail account


# --- Helper Function (Corrected Error Handling) ---
def fetch_website_content(url: str) -> str:
    """Fetches the content of a website (using requests), with error handling."""
    try:
        response = requests.get(url, timeout=10)  # 10-second timeout
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.text
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching website content for {url}: {e}")
        return ""  # Return an empty string on error


# --- Main Function ---
def main():
    """Main workflow for generating and saving developing letters."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Step 1: Extract company data
    logging.info("Extracting company data from Excel...")
    companies_data = extract_company_data(str(EXCEL_FILE_PATH))
    logging.info(f"Number of companies extracted: {len(companies_data)}")

    if not companies_data:
        logging.error("No company data found. Exiting.")
        return

    # Step 2: Read Skyfend's business
    logging.info("Reading Skyfend's business description...")
    skyfend_business = read_skyfend_business(str(SKYFEND_BUSINESS_PATH))
    if not skyfend_business:
        logging.error("Skyfend's business description is empty. Exiting.")
        return
    logging.info(f"Skyfend's business: {skyfend_business}")

    # Step 3, 4, 5: Process each company
    for company_data in companies_data:
        website = company_data.get('website')
        recipient_email = company_data.get('recipient_email')
        company_name = company_data.get('company')
        contact_person = company_data.get('contact person')  # Corrected key

        # --- Input Validation ---
        if not website or not recipient_email:
            logging.warning(f"Skipping company due to missing website/recipient: {company_data}")
            continue

        logging.info(f"Processing website: {website}, Recipient: {recipient_email}")

        # --- Fetch Website Content ---
        website_content = fetch_website_content(website)
        if not website_content:
            logging.warning(f"Could not retrieve content for {website}. Skipping.")
            continue

        # --- Extract Main Business ---
        main_business = extract_main_business(API_KEY, website_content)
        if not main_business or main_business == "Unknown":
            logging.warning(f"Could not extract business for {website}. Skipping.")
            continue
        logging.info(f"Extracted business for {website}: {main_business}")

        # --- Identify Cooperation Points ---
        cooperation_points = identify_cooperation_points(API_KEY, skyfend_business, main_business)
        logging.info(f"Cooperation points for {website}: {cooperation_points}")
        if cooperation_points == "No cooperation points identified":
            logging.warning(f"No cooperation points identified for {website}. Skipping.")
            continue

        # --- Generate Developing Letter ---
        instructions = "Please write a formal letter highlighting the cooperation opportunities."
        letter_content = generate_developing_letter(API_KEY, instructions, cooperation_points, company_name, contact_person)
        logging.info(f"Generated letter for {website}")
        if letter_content == 'No letter content generated': # Check the return
            logging.warning(f"No letter content generated for {website}. Skipping.")
            continue
        # --- Prepare Email ---
        email_subject = f"Potential Cooperation with Skyfend and {company_name}"
        email_body = letter_content

        # --- Save Email Draft and Data ---
        draft_id = save_email_to_drafts(GMAIL_ACCOUNT, recipient_email, email_subject, email_body) # Use sender
        if draft_id:
            logging.info(f"Email draft saved for {recipient_email}")

            # Prepare data for saving (consistent with your Excel file structure)
            current_time = datetime.datetime.now().strftime("%Y/%m/%d %H:%M")
            data_to_save = {
                'saving_file_time': current_time,
                'company': company_name,
                'website': website,
                'main_business': main_business,
                'cooperation_letter_conter': letter_content, # Use letter_content
                'recipient_email': recipient_email,
                'contact_person': contact_person,
            }

            # --- CRITICAL: Call save_data_to_excel with the *new* path ---
            save_data_to_excel(data_to_save, str(PROCESSED_EXCEL_FILE_PATH))  # Use the new path!

        else:
            logging.error(f"Failed to save draft for {recipient_email}")


if __name__ == "__main__":
    main()