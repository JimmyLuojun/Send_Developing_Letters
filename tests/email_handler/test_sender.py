# tests/email_handler/test_sender.py
import pytest
import base64
import logging
import os
import sys # Need sys for monkeypatching sys.modules
from unittest.mock import patch, MagicMock, mock_open, ANY
from email.mime.text import MIMEText

# Define Mocks Globally (as before)
google_mock = MagicMock()
google_mock.oauth2.credentials.Credentials = MagicMock()
google_mock.auth.transport.requests.Request = MagicMock()
google_mock.oauth2.credentials.Credentials.from_authorized_user_file = MagicMock()
google_mock_flow = MagicMock()
google_mock_flow_instance = MagicMock(spec=['run_local_server']) # Define spec for instance methods
google_mock_flow.from_client_secrets_file.return_value = google_mock_flow_instance
google_mock_flow_instance.run_local_server.return_value = MagicMock(spec=['to_json', 'valid', 'expired', 'refresh_token', 'refresh'])
google_mock_oauthlib = MagicMock()
google_mock_oauthlib.flow.InstalledAppFlow = google_mock_flow

google_mock_build = MagicMock()
google_mock_service = MagicMock()
google_mock_drafts = MagicMock()
google_mock_build.return_value = google_mock_service
google_mock_service.users.return_value.drafts.return_value = google_mock_drafts
# Mock HttpError - define a simple Exception class for it
MockHttpError = type('MockHttpError', (Exception,), {})


# --- Fixture to apply mocks using monkeypatch ---
@pytest.fixture(autouse=True)
def mock_google_libs_via_monkeypatch(monkeypatch):
    """Uses pytest's monkeypatch fixture to mock imports."""
    # Mock the modules in sys.modules BEFORE sender is potentially imported by tests
    monkeypatch.setitem(sys.modules, 'google.oauth2.credentials', google_mock.oauth2.credentials)
    monkeypatch.setitem(sys.modules, 'google.auth.transport.requests', google_mock.auth.transport.requests)
    monkeypatch.setitem(sys.modules, 'google_auth_oauthlib.flow', google_mock_oauthlib.flow)
    monkeypatch.setitem(sys.modules, 'googleapiclient.discovery', MagicMock(build=google_mock_build))
    # Use the actual HttpError if available and needed for type checking, else mock it
    try:
        from googleapiclient.errors import HttpError
        monkeypatch.setitem(sys.modules, 'googleapiclient.errors', MagicMock(HttpError=HttpError))
    except ImportError:
        monkeypatch.setitem(sys.modules, 'googleapiclient.errors', MagicMock(HttpError=MockHttpError))


# --- Test Fixtures/Data ---
TEST_CREDENTIALS_PATH = "dummy_credentials.json"
TEST_TOKEN_PATH = "dummy_token.json"
DUMMY_USER_ID = "me"

@pytest.fixture
def dummy_mime_message():
    msg = MIMEText("This is the test body.")
    msg['Subject'] = 'Test Subject'
    msg['From'] = 'sender@test.com'
    msg['To'] = 'recipient@test.com'
    return msg

@pytest.fixture(autouse=True)
def reset_mocks_fixture(): # Renamed slightly to avoid confusion
    """Reset mocks before each test function."""
    # Use the global mock objects defined above
    google_mock.reset_mock(return_value=True, side_effect=True)
    google_mock_oauthlib.reset_mock(return_value=True, side_effect=True)
    google_mock_build.reset_mock(return_value=True, side_effect=True)
    google_mock_service.reset_mock(return_value=True, side_effect=True)
    google_mock_drafts.reset_mock(return_value=True, side_effect=True)
    google_mock_flow_instance.reset_mock(return_value=True, side_effect=True) # Reset flow instance too
    google_mock.oauth2.credentials.Credentials.from_authorized_user_file.reset_mock(return_value=True, side_effect=True)
    google_mock_flow.from_client_secrets_file.reset_mock(return_value=True, side_effect=True)
    google_mock_flow_instance.run_local_server.reset_mock(return_value=True, side_effect=True)


    # Reconfigure default mock behaviors needed for most tests
    google_mock_build.return_value = google_mock_service
    google_mock_service.users.return_value.drafts.return_value = google_mock_drafts
    # Default successful draft creation
    google_mock_drafts.create.return_value.execute.return_value = {'id': 'draft_123'}
    # Default flow success
    google_mock_flow.from_client_secrets_file.return_value = google_mock_flow_instance
    mock_flow_creds = MagicMock(valid=True, expired=False, refresh_token=None, spec=['to_json', 'valid', 'expired', 'refresh_token']) # Make it more realistic
    mock_flow_creds.to_json.return_value = '{"new_flow": "token"}'
    google_mock_flow_instance.run_local_server.return_value = mock_flow_creds



# --- Tests for _get_gmail_credentials ---

# Use patch decorators for things NOT handled by the module mock fixture (like os.path.exists, open)
@patch('src.email_handler.sender.os.path.exists')
# Patch 'Credentials.from_authorized_user_file' specifically where it's called
@patch('src.email_handler.sender.Credentials.from_authorized_user_file')
def test_get_credentials_token_valid(mock_creds_from_file, mock_os_exists):
    # Import sender *inside* the test to ensure mocks are active
    from src.email_handler import sender

    mock_os_exists.return_value = True # token.json exists
    mock_creds = MagicMock(valid=True, expired=False, refresh_token=None) # Ensure it's valid
    mock_creds_from_file.return_value = mock_creds

    creds = sender._get_gmail_credentials(TEST_CREDENTIALS_PATH, TEST_TOKEN_PATH)

    assert creds == mock_creds
    mock_creds_from_file.assert_called_once_with(TEST_TOKEN_PATH, sender.SCOPES)
    mock_os_exists.assert_called_once_with(TEST_TOKEN_PATH)
    # Ensure OAuth flow was NOT initiated (check the mock object directly)
    google_mock_oauthlib.flow.InstalledAppFlow.from_client_secrets_file.assert_not_called()


@patch('src.email_handler.sender.os.path.exists')
@patch('src.email_handler.sender.Credentials.from_authorized_user_file')
@patch('src.email_handler.sender.open', new_callable=mock_open)
def test_get_credentials_token_expired_refresh_ok(mock_open_file, mock_creds_from_file, mock_os_exists):
    from src.email_handler import sender
    mock_os_exists.return_value = True # token.json exists
    # Configure the mock credential object returned by from_authorized_user_file
    mock_creds = MagicMock(valid=False, expired=True, refresh_token="abc", spec=['valid', 'expired', 'refresh_token', 'refresh', 'to_json'])
    # Need to make 'valid' True *after* refresh is called
    def refresh_effect(*args):
        mock_creds.valid = True
        mock_creds.expired = False
    mock_creds.refresh.side_effect = refresh_effect
    mock_creds.to_json.return_value = '{"refreshed": "token"}'
    mock_creds_from_file.return_value = mock_creds

    creds = sender._get_gmail_credentials(TEST_CREDENTIALS_PATH, TEST_TOKEN_PATH)

    assert creds == mock_creds
    assert creds.valid is True # Check state after refresh
    mock_creds.refresh.assert_called_once()
    mock_open_file.assert_called_once_with(TEST_TOKEN_PATH, 'w')
    mock_open_file().write.assert_called_once_with('{"refreshed": "token"}')
    google_mock_oauthlib.flow.InstalledAppFlow.from_client_secrets_file.assert_not_called()


@patch('src.email_handler.sender.os.path.exists')
@patch('src.email_handler.sender.Credentials.from_authorized_user_file')
@patch('src.email_handler.sender.open', new_callable=mock_open)
def test_get_credentials_token_expired_refresh_fail_flow_ok(mock_open_file, mock_creds_from_file, mock_os_exists):
    from src.email_handler import sender
    # os.path.exists needs to handle two calls: token (True), credentials (True)
    mock_os_exists.side_effect = [True, True] # token exists, credentials.json exists

    # Configure creds returned by from_file to fail refresh
    mock_expired_creds = MagicMock(valid=False, expired=True, refresh_token="abc", spec=['valid', 'expired', 'refresh_token', 'refresh'])
    mock_expired_creds.refresh.side_effect = Exception("Refresh failed")
    mock_creds_from_file.return_value = mock_expired_creds

    # Flow success is configured in reset_mocks_fixture by default
    # Retrieve the mock creds the flow is configured to return
    expected_new_creds = google_mock_flow_instance.run_local_server.return_value

    creds = sender._get_gmail_credentials(TEST_CREDENTIALS_PATH, TEST_TOKEN_PATH)

    # ASSERTION: Now expects the creds from the flow because refresh fails
    assert creds == expected_new_creds
    mock_expired_creds.refresh.assert_called_once() # Refresh was attempted
    # Check flow was initiated (using the global mock object)
    google_mock_oauthlib.flow.InstalledAppFlow.from_client_secrets_file.assert_called_once_with(TEST_CREDENTIALS_PATH, sender.SCOPES)
    google_mock_flow_instance.run_local_server.assert_called_once_with(port=0)
    # Check token was saved (this corresponds to the *new* token from the flow)
    mock_open_file.assert_called_once_with(TEST_TOKEN_PATH, 'w')
    mock_open_file().write.assert_called_once_with('{"new_flow": "token"}') # Matches default flow creds


@patch('src.email_handler.sender.os.path.exists')
@patch('src.email_handler.sender.open', new_callable=mock_open)
def test_get_credentials_no_token_flow_ok(mock_open_file, mock_os_exists):
    from src.email_handler import sender
    # token.json doesn't exist, credentials.json exists
    mock_os_exists.side_effect = [False, True]
    # Flow success is default from fixture
    expected_new_creds = google_mock_flow_instance.run_local_server.return_value

    creds = sender._get_gmail_credentials(TEST_CREDENTIALS_PATH, TEST_TOKEN_PATH)

    assert creds == expected_new_creds
    google_mock_oauthlib.flow.InstalledAppFlow.from_client_secrets_file.assert_called_once_with(TEST_CREDENTIALS_PATH, sender.SCOPES)
    google_mock_flow_instance.run_local_server.assert_called_once_with(port=0)
    mock_open_file.assert_called_once_with(TEST_TOKEN_PATH, 'w')
    mock_open_file().write.assert_called_once_with('{"new_flow": "token"}')
    # Ensure from_authorized_user_file was NOT called (check global mock)
    google_mock.oauth2.credentials.Credentials.from_authorized_user_file.assert_not_called()


@patch('src.email_handler.sender.os.path.exists')
def test_get_credentials_no_creds_file(mock_os_exists, caplog):
    from src.email_handler import sender
    mock_os_exists.side_effect = [False, False] # token doesn't exist, credentials doesn't exist

    with caplog.at_level(logging.ERROR):
        creds = sender._get_gmail_credentials(TEST_CREDENTIALS_PATH, TEST_TOKEN_PATH)

    assert creds is None
    assert f"Credentials file not found at: {TEST_CREDENTIALS_PATH}" in caplog.text
    google_mock_oauthlib.flow.InstalledAppFlow.from_client_secrets_file.assert_not_called()


# --- Tests for save_email_to_drafts ---

# Patch _get_gmail_credentials specifically for these tests
@patch('src.email_handler.sender._get_gmail_credentials')
def test_save_email_to_drafts_success(mock_get_creds, dummy_mime_message, caplog):
    from src.email_handler import sender
    mock_creds = MagicMock()
    mock_get_creds.return_value = mock_creds
    # Default mock setup in reset_mocks_fixture handles successful API call

    with caplog.at_level(logging.INFO):
        draft_id = sender.save_email_to_drafts(dummy_mime_message, TEST_CREDENTIALS_PATH, TEST_TOKEN_PATH)

    assert draft_id == 'draft_123' # Default from reset_mocks_fixture
    mock_get_creds.assert_called_once_with(TEST_CREDENTIALS_PATH, TEST_TOKEN_PATH)
    # Check global mocks for API calls
    google_mock_build.assert_called_once_with('gmail', 'v1', credentials=mock_creds)
    expected_raw = base64.urlsafe_b64encode(dummy_mime_message.as_bytes()).decode()
    expected_body = {'message': {'raw': expected_raw}}
    google_mock_drafts.create.assert_called_once_with(userId=DUMMY_USER_ID, body=expected_body)
    google_mock_drafts.create.return_value.execute.assert_called_once()
    assert 'Draft created successfully. Draft ID: draft_123' in caplog.text


@patch('src.email_handler.sender._get_gmail_credentials')
def test_save_email_to_drafts_no_credentials(mock_get_creds, dummy_mime_message, caplog):
    from src.email_handler import sender
    mock_get_creds.return_value = None

    with caplog.at_level(logging.ERROR):
        draft_id = sender.save_email_to_drafts(dummy_mime_message, TEST_CREDENTIALS_PATH, TEST_TOKEN_PATH)

    assert draft_id is None
    assert "Failed to obtain Gmail credentials. Cannot save draft." in caplog.text
    # Ensure build was not called
    google_mock_build.assert_not_called()


@patch('src.email_handler.sender._get_gmail_credentials')
def test_save_email_to_drafts_api_http_error(mock_get_creds, dummy_mime_message, caplog):
    from src.email_handler import sender
    # Use the actual HttpError class if available from google libs, else use our mock one
    try:
        from googleapiclient.errors import HttpError as ActualHttpError
    except ImportError:
        ActualHttpError = MockHttpError # Fallback to the basic mock exception

    mock_creds = MagicMock()
    mock_get_creds.return_value = mock_creds
    # Override default mock behavior for execute to raise error
    google_mock_drafts.create.return_value.execute.side_effect = ActualHttpError(MagicMock(status=403), b"Forbidden") # Simulate HttpError more closely

    with caplog.at_level(logging.ERROR):
        draft_id = sender.save_email_to_drafts(dummy_mime_message, TEST_CREDENTIALS_PATH, TEST_TOKEN_PATH)

    assert draft_id is None
    # Check the exact error message format logged by the except block
    assert "An HTTP error occurred while saving draft:" in caplog.text # Check start of msg
    assert "Forbidden" in caplog.text # Check content of error
    google_mock_build.assert_called_once() # Build was called
    google_mock_drafts.create.assert_called_once() # Create was called
    google_mock_drafts.create.return_value.execute.assert_called_once() # Execute was called (and raised)


@patch('src.email_handler.sender._get_gmail_credentials')
def test_save_email_to_drafts_api_no_id(mock_get_creds, dummy_mime_message, caplog):
    from src.email_handler import sender
    mock_creds = MagicMock()
    mock_get_creds.return_value = mock_creds
    # Override default mock behavior for execute
    google_mock_drafts.create.return_value.execute.return_value = {'message': 'ok'} # No 'id' key

    with caplog.at_level(logging.ERROR):
        draft_id = sender.save_email_to_drafts(dummy_mime_message, TEST_CREDENTIALS_PATH, TEST_TOKEN_PATH)

    assert draft_id is None
    assert "Draft created but no ID returned by API." in caplog.text
    google_mock_build.assert_called_once()
    google_mock_drafts.create.assert_called_once()
    google_mock_drafts.create.return_value.execute.assert_called_once()