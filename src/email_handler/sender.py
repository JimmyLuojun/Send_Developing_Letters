# src/email_handler/sender.py
"""Module for sending emails or saving them to drafts using Gmail API."""
import base64
import logging
import os.path
import time
from email.message import Message # Use Message for type hint
from typing import Optional, List

# Ensure necessary imports for google libraries are present
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.compose', # To create drafts
          'https://www.googleapis.com/auth/gmail.modify'] # Also needed for drafts

DEFAULT_TOKEN_PATH = 'token.json' # Store token in root by default

def _get_gmail_credentials(credentials_path: str, token_path: str = DEFAULT_TOKEN_PATH) -> Optional[Credentials]:
    """Gets valid user credentials from storage or initiates OAuth flow."""
    creds = None
    # --- Try loading existing token ---
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            logging.info(f"Loaded credentials from {token_path}")
        except Exception as e:
            logging.warning(f"Could not load credentials from {token_path}: {e}. Will attempt re-authentication.")
            creds = None

    # --- Check validity or attempt refresh ---
    if creds and creds.valid:
        logging.debug("Existing credentials are valid.")
        return creds # Valid token loaded, we are done

    if creds and creds.expired and creds.refresh_token:
        logging.info("Existing credentials expired, attempting refresh...")
        try:
            creds.refresh(Request())
            logging.info("Credentials refreshed successfully.")
            # Save the refreshed credentials immediately
            try:
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
                logging.info(f"Refreshed credentials saved to {token_path}")
            except Exception as e:
                 logging.error(f"Failed to save refreshed credentials to {token_path}: {e}")
            return creds # Return refreshed credentials
        except Exception as e:
            # --- LOGIC FIX: Log error and clear creds to trigger flow below ---
            logging.error(f"Failed to refresh token: {e}. Proceeding to manual re-authentication.")
            creds = None # Ensure we trigger the flow below

    # --- Attempt OAuth Flow if no valid/refreshed creds exist ---
    # This block runs if:
    # 1. token.json didn't exist OR failed to load
    # 2. token.json existed but creds were invalid (and had no refresh_token)
    # 3. Refresh attempt failed in the block above
    if not creds: # Check if we need to run the flow
        logging.info("Valid credentials not found or refresh failed. Initiating new OAuth flow...")
        if not os.path.exists(credentials_path):
             logging.error(f"Credentials file not found at: {credentials_path}. Cannot initiate OAuth flow.")
             return None

        flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
        try:
             # Run flow in console
             creds = flow.run_local_server(port=0) # Assign new creds here
             logging.info("OAuth flow completed successfully.")
             # Save the new credentials
             try:
                 with open(token_path, 'w') as token:
                     token.write(creds.to_json())
                 logging.info(f"New credentials saved to {token_path}")
             except Exception as e:
                  logging.error(f"Failed to save new credentials to {token_path}: {e}")
             # Return newly obtained credentials whether saved or not
             # (though saving failure is problematic)
             return creds
        except Exception as e:
             logging.error(f"OAuth flow failed: {e}", exc_info=True)
             return None # Failed to get credentials via flow

    # Should technically not be reached if logic above is correct, but return creds if it holds a value.
    # If refresh failed and flow wasn't triggered somehow, it would be None here.
    return creds


def save_email_to_drafts(
    mime_message: Message,
    credentials_path: str,
    token_path: str = DEFAULT_TOKEN_PATH,
    user_id: str = 'me'
    ) -> Optional[str]:
    """
    Creates a draft email in the user's Gmail account.

    Args:
        mime_message: An email.message.Message object.
        credentials_path: Path to the Google Cloud credentials.json file.
        token_path: Path where the token.json file is stored/will be stored.
        user_id: User's email address. The special value 'me' can be used
                 to indicate the authenticated user.

    Returns:
        The ID of the created draft, or None if an error occurred.
    """
    creds = _get_gmail_credentials(credentials_path, token_path)
    if not creds:
        logging.error("Failed to obtain Gmail credentials. Cannot save draft.")
        return None

    try:
        service = build('gmail', 'v1', credentials=creds)
        # Encode message to base64url format
        encoded_message = base64.urlsafe_b64encode(mime_message.as_bytes()).decode()
        create_draft_request_body = {'message': {'raw': encoded_message}}

        # pylint: disable=E1101
        draft = service.users().drafts().create(
            userId=user_id,
            body=create_draft_request_body
        ).execute()

        draft_id = draft.get('id')
        if draft_id:
             logging.info(f'Draft created successfully. Draft ID: {draft_id}')
             return draft_id
        else:
             logging.error("Draft created but no ID returned by API.")
             return None

    except HttpError as error:
        # Make sure HttpError is imported or handled appropriately
        logging.error(f'An HTTP error occurred while saving draft: {error}')
        return None
    except Exception as e:
        logging.error(f'An unexpected error occurred while saving draft: {e}', exc_info=True)
        return None