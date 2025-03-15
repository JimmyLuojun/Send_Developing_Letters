# src/main_v2.py
import os
import logging
import pandas as pd
from datetime import datetime
import pathlib
import requests
import re
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- Project Root (using pathlib) ---
PROJECT_ROOT = pathlib.Path(__file__).parent.parent

from src.models.extract_company_data import extract_company_data
from src.data.skyfend_business import read_skyfend_business
from src.models.business_extraction import extract_main_business
from src.models.identify_cooperation_points import identify_cooperation_points
from src.utils.generate_developing_letters import generate_developing_letter
from src.utils.save_email_to_drafts import save_email_to_drafts

# --- Load environment variables ---
load_dotenv()

# --- Configuration (PATHS SHOULD BE ABSOLUTE OR RELATIVE TO THE PROJECT ROOT) ---
RAW_EXCEL_PATH = PROJECT_ROOT / "data" / "raw" / "test_to_read_website.xlsx"
SKYFEND_BUSINESS_DOC_PATH = PROJECT_ROOT / "data" / "raw" / "test_main Business of Skyfend.docx"
PROCESSED_EXCEL_PATH = PROJECT_ROOT / "data" / "processed" / "saving_company_data_after_creating_letters.xlsx"

API_KEY = os.getenv("API_KEY")
GMAIL_ACCOUNT = os.getenv("GMAIL_ACCOUNT")

# --- Helper Functions ---
def load_processed_data(file_path):
    if os.path.exists(file_path):
        return pd.read_excel(file_path).fillna("")
    else:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        return pd.DataFrame(columns=['saving_file_time', 'company', 'website', 'main_business',
                                     'recipient_email', 'contact_person', 'cooperation_letter_content',
                                     'cooperation_points'])

def is_valid_email(email):
    pattern = r"^[^@]+@[^@]+\.[^@]+$"
    return re.match(pattern, email) is not None

def get_website_content(url, max_content_length=2000):
    if not url or not isinstance(url, str):
        logging.error(f"Invalid URL provided: {url}")
        return ""

    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    session = requests.Session()
    retries = Retry(total=3, backoff_factor=0.5,
                    status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"])
    session.mount('https://', HTTPAdapter(max_retries=retries))

    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        response = session.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.text[:max_content_length]
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch website {url}: {e}")
        return ""

def main():
    raw_data = pd.read_excel(RAW_EXCEL_PATH)
    raw_data.columns = raw_data.columns.str.strip().str.lower()
    processed_data = load_processed_data(PROCESSED_EXCEL_PATH)

    skyfend_business = read_skyfend_business(SKYFEND_BUSINESS_DOC_PATH)

    for _, row in raw_data.iterrows():
        company_name = str(row.get('company', '')).strip()
        recipient_email = str(row.get('recipient_email', '')).strip()
        website = str(row.get('website', '')).strip()
        contact_person = str(row.get('contact person', '')).strip()

        if not recipient_email or not is_valid_email(recipient_email):
            logging.warning(f"Skipping invalid recipient email '{recipient_email}' for company: {company_name}")
            continue

        existing_entry = processed_data[
            (processed_data['company'] == company_name) &
            (processed_data['recipient_email'].str.strip() == recipient_email)
        ]

        if not existing_entry.empty:
            logging.info(f"Email to {recipient_email} at {company_name} already processed. Skipping.")
            continue

        existing_company = processed_data[processed_data['company'] == company_name]

        if existing_company.empty:
            website_content = get_website_content(website)
            if not website_content:
                logging.warning(f"Skipping {company_name} due to empty website content.")
                continue

            main_business = extract_main_business(API_KEY, website_content)
            cooperation_points = identify_cooperation_points(API_KEY, skyfend_business, main_business)

            email_body = generate_developing_letter(
                API_KEY,
                "Generate a formal business development letter.",
                cooperation_points, company_name, contact_person)
        else:
            previous_main_business = existing_company.iloc[0]['main_business']
            previous_cooperation_points = existing_company.iloc[0]['cooperation_points']

            email_body = generate_developing_letter(
                API_KEY,
                "Rephrase this letter with a fresh tone.",
                previous_cooperation_points, company_name, contact_person)

            main_business = previous_main_business
            cooperation_points = previous_cooperation_points

        # Save to drafts and Excel
        try:
            draft_id = save_email_to_drafts(
                sender=GMAIL_ACCOUNT,
                recipient=recipient_email,
                subject=f"Potential Cooperation with Skyfend and {company_name}",
                body=email_body
            )
            logging.info(f"Draft saved successfully, ID: {draft_id}")
        except Exception as e:
            logging.error(f"Failed to save email draft for {recipient_email}: {e}")
            continue

        current_time = datetime.now().strftime("%Y/%m/%d %H:%M")
        new_record = {
            'saving_file_time': current_time,
            'company': company_name,
            'website': website,
            'recipient_email': recipient_email,
            'contact_person': contact_person,
            'main_business': main_business,
            'cooperation_letter_content': email_body,
            'cooperation_points': cooperation_points
        }

        processed_data = pd.concat([processed_data, pd.DataFrame([new_record])], ignore_index=True)
        processed_data.to_excel(PROCESSED_EXCEL_PATH, index=False)

        logging.info(f"Processed and saved data for {company_name} ({recipient_email})")

if __name__ == "__main__":
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)  # Ensures log directory exists

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / f"processing_{datetime.now().strftime('%Y%m%d')}.log"),
            logging.StreamHandler()
        ]
    )
    main()