# src/main3.py
import os
import re
import logging
import pathlib
import pandas as pd
import requests
from datetime import datetime
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

# --- Project Root (using pathlib) ---
PROJECT_ROOT = pathlib.Path(__file__).parent.parent

# --- Import project modules ---
from src.models.extract_company_data import extract_company_data
from src.data.skyfend_business import read_skyfend_business
from src.models.business_extraction import extract_main_business
from src.models.identify_cooperation_points import identify_cooperation_points
from src.utils.generate_developing_letters import generate_developing_letter
from src.utils.save_email_to_drafts import save_email_to_drafts  # This function now accepts a MIME message

# --- Load environment variables ---
load_dotenv()

# --- Configuration (adjust paths as needed) ---
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
        return pd.DataFrame(columns=[
            'saving_file_time', 'company', 'website', 'main_business',
            'recipient_email', 'contact_person', 'cooperation_letter_content',
            'cooperation_points'
        ])

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
                    status_forcelist=[429, 500, 502, 503, 504],
                    allowed_methods=["GET"])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = session.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.text[:max_content_length]
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch website {url}: {e}")
        return ""

def extract_keywords_from_filename(filename):
    """
    Extract keywords from an image filename.
    Example: "1.2solution for airport security_C.png" yields keywords like 'solution', 'for', 'airport', 'security', 'c'
    """
    base = pathlib.Path(filename).stem
    base = re.sub(r'^[\d\.\s]+', '', base)
    base = base.replace('_', ' ')
    keywords = set(base.lower().split())
    return keywords

def select_relevant_images(email_body, company_name):
    """
    Select three images from the image folder that best match the context based on keywords.
    The images are stored at: PROJECT_ROOT/data/raw/images.
    """
    images_folder = PROJECT_ROOT / "data" / "raw" / "images"
    candidate_images = list(images_folder.glob("*.jpg")) + list(images_folder.glob("*.png"))
    if not candidate_images:
        logging.warning("No candidate images found in the images folder.")
        return []
    
    context_text = f"{email_body} {company_name}".lower()
    context_words = set(re.findall(r'\w+', context_text))
    
    image_scores = []
    for img in candidate_images:
        keywords = extract_keywords_from_filename(str(img))
        score = len(keywords.intersection(context_words))
        image_scores.append((img, score))
    
    image_scores.sort(key=lambda x: x[1], reverse=True)
    selected = [str(img) for img, _ in image_scores[:3]]
    if len(selected) < 3:
        for img in candidate_images:
            if str(img) not in selected:
                selected.append(str(img))
            if len(selected) == 3:
                break
    return selected

def create_email_with_inline_images(sender, recipient, subject, body, image_paths):
    """
    Create a MIME email message by splitting the body into four segments
    and inserting each of the three images between the segments.
    Each image is centered and given consistent spacing to appear symmetrical.
    """
    # Create the primary multipart container (using 'related' for inline images).
    message = MIMEMultipart('related')
    message['From'] = sender
    message['To'] = recipient
    message['Subject'] = subject

    # Create an alternative part for HTML content.
    msg_alternative = MIMEMultipart('alternative')
    message.attach(msg_alternative)

    # Split the body into sections using newline as a delimiter.
    sections = body.split('\n')
    if len(sections) < 4:
        # Fallback: distribute images after each section, up to 3 images.
        segments = []
        for i, sec in enumerate(sections):
            # Wrap each section in a paragraph, justifying text.
            segments.append(f'<p style="text-align:justify;">{sec}</p>')
            # Insert an image (centered) after each section, up to 3 images.
            if i < 3:
                segments.append(f'''
                <div style="text-align:center; margin: 20px 0;">
                  <img src="cid:image{i+1}" style="max-width:600px;"/>
                </div>
                ''')
        html_body = "".join(segments)
    else:
        # Evenly split into 4 segments.
        total_sections = len(sections)
        part_length = total_sections // 4
        seg1 = "\n".join(sections[:part_length])
        seg2 = "\n".join(sections[part_length:2*part_length])
        seg3 = "\n".join(sections[2*part_length:3*part_length])
        seg4 = "\n".join(sections[3*part_length:])

        # Insert each image (centered) after seg1, seg2, seg3.
        html_body = f"""
        <p style="text-align:justify;">{seg1}</p>
        <div style="text-align:center; margin: 20px 0;">
          <img src="cid:image1" style="max-width:600px;"/>
        </div>

        <p style="text-align:justify;">{seg2}</p>
        <div style="text-align:center; margin: 20px 0;">
          <img src="cid:image2" style="max-width:600px;"/>
        </div>

        <p style="text-align:justify;">{seg3}</p>
        <div style="text-align:center; margin: 20px 0;">
          <img src="cid:image3" style="max-width:600px;"/>
        </div>

        <p style="text-align:justify;">{seg4}</p>
        """
    # Attach the HTML to the 'alternative' part of the email.
    msg_alternative.attach(MIMEText(html_body, 'html'))

    # Attach each image with a corresponding Content-ID.
    for idx, image_path in enumerate(image_paths, start=1):
        try:
            with open(image_path, 'rb') as f:
                img_data = f.read()
            image = MIMEImage(img_data)
            image.add_header('Content-ID', f'<image{idx}>')
            message.attach(image)
        except Exception as e:
            logging.error(f"Error attaching image {image_path}: {e}")

    return message

# --- Main Processing Function ---
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

        # Data Validation: Skip rows with missing or invalid critical fields.
        if not company_name or company_name.lower() == 'nan':
            logging.warning(f"Skipping row with invalid company name: '{company_name}'")
            continue
        if not recipient_email or recipient_email.lower() == 'nan' or not is_valid_email(recipient_email):
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

        # --- Image Selection ---
        inline_images = select_relevant_images(email_body, company_name)
        if len(inline_images) != 3:
            logging.warning(f"Expected 3 inline images, but found {len(inline_images)}. Skipping email draft creation for {company_name}.")
            continue

        subject = f"Potential Cooperation with Skyfend and {company_name}"
        # Create the MIME email message with inline images attached.
        email_message = create_email_with_inline_images(
            sender=GMAIL_ACCOUNT,
            recipient=recipient_email,
            subject=subject,
            body=email_body,
            image_paths=inline_images
        )

        # --- Save Email Draft ---
        try:
            # IMPORTANT: Pass the MIME message using the keyword 'mime_message'
            draft_id = save_email_to_drafts(mime_message=email_message)
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
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / f"processing_{datetime.now().strftime('%Y%m%d')}.log"),
            logging.StreamHandler()
        ]
    )
    main()
