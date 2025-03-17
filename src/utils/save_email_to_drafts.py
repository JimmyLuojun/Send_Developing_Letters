# src/utils/save_email_to_drafts.py
import os.path
import base64
from email.mime.text import MIMEText
from typing import Optional
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError
import logging
import time
import json
import openpyxl

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.compose']

TOKEN_FILE = 'token.json'  # Put in the project root for simplicity
CREDENTIALS_FILE = 'credentials.json'  # Project root


def get_credentials():
    """Gets valid Google API credentials, handling initial authorization and refresh."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            logging.error(f"Error loading credentials from token file: {e}")
            # If loading fails for any reason, proceed to re-authentication.
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(GoogleAuthRequest())
            except RefreshError as e:
                logging.error(f"Token refresh failed: {e}")
                # Delete the invalid token.json file.  Force re-auth.
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)
                creds = None  # Ensure re-authentication happens

        if not creds:
            # Run the full authorization flow.
            try:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)

                # Save the credentials for the next run
                with open(TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())

            except Exception as e:
                logging.error(f"Authorization flow failed: {e}")
                return None  # Return None if auth fails

    return creds


def create_message(sender, to, subject, message_text):
    """Create a message for an email."""
    message = MIMEText(message_text, 'html') # Set the type
    message['to'] = to
    message['from'] = sender # Use sender parameter
    message['subject'] = subject
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw_message}


def save_email_to_drafts(*, sender=None, recipient=None, subject=None, body=None, mime_message=None):
    """
    Saves an email as a draft in Gmail. Supports both plain text/HTML emails and full MIME messages.
    
    Args:
        sender: Optional; Email address of the sender. Required if mime_message is None.
        recipient: Optional; Email address of the recipient. Required if mime_message is None.
        subject: Optional; Subject of the email. Required if mime_message is None.
        body: Optional; Body of the email. Required if mime_message is None.
        mime_message: Optional; The complete MIME message object (including attachments).
                     If provided, other parameters are ignored.

    Returns:
        The ID of the created draft, or None if an error occurred.
    """
    creds = get_credentials()
    if not creds:
        logging.error("Failed to retrieve valid credentials.")
        return None

    try:
        service = build('gmail', 'v1', credentials=creds)

        # Determine which message to send based on the inputs
        if mime_message:
            # Use the provided MIME message directly
            encoded_message = base64.urlsafe_b64encode(mime_message.as_bytes()).decode()
            message_dict = {'message': {'raw': encoded_message}}
        else:
            if not all([sender, recipient, subject]):
                logging.error("Missing required parameters for simple email creation")
                return None
            # Create a simple email message using the function create_message
            email_msg = create_message(sender, recipient, subject, body or '')
            message_dict = {'message': email_msg}

        # Save the message as a draft
        draft = service.users().drafts().create(userId="me", body=message_dict).execute()
        logging.info(f'Draft id: {draft["id"]}, Draft message: {draft["message"]["id"]}')
        return draft['id']

    except HttpError as error:
        logging.error(f'An HttpError occurred: {error}')
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        return None


def save_data_to_excel(data, file_path):  # Add file_path
    """Saves data to the Excel file in a new row."""
    try:
        if not os.path.exists(file_path):  # Use file_path
            # Create a new workbook and add headers if the file doesn't exist
            workbook = openpyxl.Workbook()
            sheet = workbook.active
            headers = list(data.keys())  # Get headers from the data keys
            sheet.append(headers)
        else:
            workbook = openpyxl.load_workbook(file_path)  # Use file_path
            sheet = workbook.active

        # Append the data values in a new row
        row_data = list(data.values())
        sheet.append(row_data)
        workbook.save(file_path)  # Use file_path
        logging.info(f"Data saved to Excel successfully.  File path: {file_path}") # Log file_path

    except Exception as e:
        logging.error(f"Error saving data to Excel: {e}, File path: {file_path}") # Log file_path



if __name__ == '__main__':
    # Example Usage (replace with your actual values and file path)
    email_account = 'your_email@example.com'
    recipient_email = 'recipient@example.com'
    email_subject = 'Test Email with Robust Auth'
    email_body = 'This is a test email.'
    logging.basicConfig(level=logging.INFO)

    draft_id = save_email_to_drafts(email_account, recipient_email, email_subject, email_body)
    if draft_id:
        print(f"Email saved to drafts. Draft ID: {draft_id}")
        current_time = time.strftime("%Y/%m/%d %H:%M")
        data_to_save = {
            'saving_file_time': current_time,
            'company': 'Test Company',
            'website': 'http://test.com',
            'main_business': 'Test business',
            'cooperation_letter_conter': 'Test letter',
            'recipient_email': recipient_email,
            'contact_person': 'Test Contact'
        }
        save_data_to_excel(data_to_save, 'test_output.xlsx') # Use a file path
    else:
        print("Failed to save email to drafts.")