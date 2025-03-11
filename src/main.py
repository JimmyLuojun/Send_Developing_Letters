import os
import pandas as pd
import logging
from dotenv import load_dotenv
import requests  # Needed for fetch_website_content
import datetime  # Import datetime

# from src.models.extract_websites_from_excel import extract_company_websites # Rename the file
from src.models.extract_company_data import extract_company_data
from src.data.skyfend_business import read_skyfend_business
from src.models.business_extraction import extract_main_business
from src.models.identify_cooperation_points import identify_cooperation_points
from src.utils.generate_developing_letters import generate_developing_letter
# from src.utils.format_and_send_email import format_and_send_email # No send email
from src.utils.save_email_to_drafts import save_email_to_drafts  # Save draft

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration (READ FROM ENVIRONMENT VARIABLES) ---
EXCEL_FILE_PATH = "/Users/junluo/Documents/Send_Developing_Letters/data/raw/test_to_read_website.xlsx"
SKYFEND_BUSINESS_PATH = "/Users/junluo/Documents/Send_Developing_Letters/data/raw/test_main Business of Skyfend.docx"

# BUSINESS_EXTRACTION_API_URL = os.getenv("BUSINESS_EXTRACTION_API_URL")
# COOPERATION_POINTS_API_URL = os.getenv("COOPERATION_POINTS_API_URL")
# LETTER_GENERATION_API_URL = os.getenv("LETTER_GENERATION_API_URL")
API_KEY = os.getenv("API_KEY")
OUTPUT_CSV_PATH = os.getenv("OUTPUT_CSV_PATH")
GMAIL_ACCOUNT = 'jimluoggac@gmail.com'  # Add GMAIL_ACCOUNT

# --- Helper Function ---
def fetch_website_content(url: str) -> str:
    """Fetches the content of a website (using requests)."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.text
    except requests.exceptions.HTTPError as e:
        logging.error(f"Error fetching website content for {url}: {e.response.status_code} {e.response.reason}")  # log the error code
        return ""
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching website content for {url}: {e}")
        return ""

def main():
    """Main workflow for the project."""

    # Create the processed data directory if it doesn't exist
    processed_data_dir = os.path.dirname(OUTPUT_CSV_PATH)
    if not os.path.exists(processed_data_dir):
        os.makedirs(processed_data_dir)

    # Step 1: Extract company data (including emails)
    logging.info("Extracting company data from Excel...")
    companies_data = extract_company_data(EXCEL_FILE_PATH)  # Get a list of dictionaries
    logging.info(f"Number of companies extracted: {len(companies_data)}")

    if not companies_data:
        logging.error("No company data found. Exiting.")
        return

    # Step 2: Read Skyfend's main business
    logging.info("Reading Skyfend's business description...")
    skyfend_business = read_skyfend_business(SKYFEND_BUSINESS_PATH)
    if not skyfend_business:
        logging.error("Skyfend's business description is empty. Exiting.")
        return
    logging.info(f"Skyfend's business: {skyfend_business}")

    # Step 3 & 4 & 5: Process each company
    all_company_data = []  # Store all processed data
    for company_data in companies_data:
        website = company_data['website']
        recipient_email = company_data['recipient_email']
        company_name = company_data['company']
        contact_person = company_data['contact person'] # Get contact person

        logging.info(f"Processing website: {website}, Recipient: {recipient_email}")

        # Fetch website content
        website_content = fetch_website_content(website)
        if not website_content:
            logging.warning(f"Could not retrieve content for {website}. Skipping.")
            continue

        # Extract main business (using the API)
        main_business = extract_main_business(API_KEY, website_content)
        if not main_business or main_business == "Unknown":
            logging.warning(f"Could not extract business for {website}. Skipping.")
            continue
        logging.info(f"Extracted business for {website}: {main_business}")

        # Identify cooperation points
        cooperation_points = identify_cooperation_points(API_KEY, skyfend_business, main_business)
        logging.info(f"Cooperation points for {website}: {cooperation_points}")
        if cooperation_points == "No cooperation points identified":
            logging.warning(f"No cooperation points identified for {website}. Skipping.")
            continue

        # Generate developing letter
        instructions = "Please write a formal letter highlighting the cooperation opportunities."
        # Pass contact_person and company_name
        letter_content = generate_developing_letter(API_KEY, instructions, cooperation_points, company_name, contact_person)
        logging.info(f"Generated letter for {website}")
        if letter_content == 'No letter content generated':
            logging.warning(f"No letter content generated for {website}. Skipping.")
            continue

        # Get domain name from website
        # domain_name = website.split("//")[-1].split("/")[0] # No need for domain_name
        # if domain_name.startswith("www."):
        #     domain_name = domain_name[4:]

        email_subject = f"Potential Cooperation with Skyfend and {company_name}" # Use company name
        email_body = letter_content

        # Save email to drafts
        try:
            save_email_to_drafts(GMAIL_ACCOUNT, recipient_email, email_subject, email_body)
            logging.info(f"Email draft saved for {recipient_email}")
        except Exception as e:
            logging.error(f"Failed to save email draft for {recipient_email}: {e}")

        # --- Add timestamp and prepare data for saving ---
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

        all_company_data.append({
            "saving_file_time": timestamp,
            "company": company_name,  # Correct key name
            "website": website,
            "main_business": main_business,
            "cooperation_points": cooperation_points,
            "letter_content": letter_content,
            "recipient_email": recipient_email,
            "contact_person": contact_person,
        })

    # --- Step 6: Save all data to CSV (append if exists) ---
    df = pd.DataFrame(all_company_data)
    if not df.empty:  # Only save if there's data
        if os.path.exists(OUTPUT_CSV_PATH):
            # Append without header
            df.to_csv(OUTPUT_CSV_PATH, mode='a', header=False, index=False)
        else:
            # Create with header
             df.to_csv(OUTPUT_CSV_PATH, index=False)
        logging.info(f"Company data saved to {OUTPUT_CSV_PATH}")
    else:
        logging.info("No data to save.")


if __name__ == "__main__":
    main()
