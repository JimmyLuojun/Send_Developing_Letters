#/Users/junluo/Documents/Send_Developing_Letters/src/utils/save_email_to_drafts.py

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
import json # Import json

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.compose']

TOKEN_FILE = 'token.json'  # Put in the project root for simplicity
CREDENTIALS_FILE = 'credentials.json' # Project root

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

def create_draft(service, user_id, message):
    """
    Creates a draft email.

    Args:
        service: Authorized Gmail API service instance.
        user_id: User's email address. The special value "me"
        can be used to indicate the authenticated user.
        message: Message to be placed in the draft.

    Returns:
        Draft object, including draft id and message meta data.  None on error.
    """
    try:
        draft = {'message': message}
        draft = service.users().drafts().create(userId=user_id, body=draft).execute()
        print(f"Draft id: {draft['id']}, Message id: {draft['message']['id']}")
        return draft
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

def save_email_to_drafts(account: str, recipient: str, subject: str, body: str) -> Optional[str]:
    """
    Saves an email as a draft in Gmail.
    """
    creds = get_credentials()  # Get valid credentials
    if not creds:
        logging.error("Failed to obtain valid credentials. Cannot save draft.")
        return None

    try:
        service = build('gmail', 'v1', credentials=creds)

        message = MIMEText(body, 'html')
        message['to'] = recipient
        message['subject'] = subject
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        create_message = {'message': {'raw': encoded_message}}
        draft = service.users().drafts().create(userId=account, body=create_message).execute()
        logging.info(f'Draft id: {draft["id"]}, Message id: {draft["message"]["id"]}')
        return draft['id']

    except HttpError as error:
        logging.error(f'An HttpError occurred: {error}')
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        return None

if __name__ == '__main__':
    # Example Usage (replace with your actual values)
    email_account = 'jimluoggac@gmail.com' #Your Gmail
    recipient_email = 'recipient@example.com'# Test email
    email_subject = 'Test Email with Robust Auth'
    email_body = 'This is a <b>test</b> email with <i>robust</i> authorization handling.'
    logging.basicConfig(level=logging.INFO)  # For testing

    draft_id = save_email_to_drafts(email_account, recipient_email, email_subject, email_body)
    if draft_id:
        print(f"Email saved to drafts. Draft ID: {draft_id}")
    else:
        print("Failed to save email to drafts.")