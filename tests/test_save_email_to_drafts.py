# tests/test_save_email_to_drafts.py 
import pytest
from unittest.mock import patch, MagicMock
from src.utils.save_email_to_drafts import save_email_to_drafts, get_credentials, save_data_to_excel
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import openpyxl


# Mock the Google API service and credentials
@pytest.fixture
def mock_service():
    mock_service = MagicMock()  # No spec here!
    mock_drafts = MagicMock()
    mock_service.users.return_value.drafts.return_value = mock_drafts
    return mock_service, mock_drafts

@patch('src.utils.save_email_to_drafts.build')
@patch('src.utils.save_email_to_drafts.get_credentials')
def test_save_email_to_drafts_success(mock_get_credentials, mock_build, mock_service):
    mock_get_credentials.return_value = MagicMock()  # Mock credentials
    mock_build.return_value = mock_service[0] # return mock_service
    mock_service[1].create.return_value.execute.return_value = {'id': 'draft_id', 'message': {'id': 'msg_id'}}

    draft_id = save_email_to_drafts('test@example.com', 'recipient@example.com', 'Subject', 'Body')
    assert draft_id == 'draft_id'
    mock_service[1].create.assert_called_once() # Verify the calling
    mock_service[1].create.return_value.execute.assert_called_once()

@patch('src.utils.save_email_to_drafts.build')
@patch('src.utils.save_email_to_drafts.get_credentials')
def test_save_email_to_drafts_http_error(mock_get_credentials, mock_build, mock_service):
    mock_get_credentials.return_value = MagicMock()
    mock_build.return_value = mock_service[0]

    # Create a mock response object with the necessary attributes
    mock_resp = MagicMock()
    mock_resp.reason = "Bad Request"  # Add a reason
    mock_resp.status = 400         # Add a status code!  VERY IMPORTANT
    mock_resp.headers = {} # Add headers

    # Use the mock_resp in the HttpError
    mock_service[1].create.return_value.execute.side_effect = HttpError(resp=mock_resp, content=b'Error')

    draft_id = save_email_to_drafts('test@example.com', 'recipient@example.com', 'Subject', 'Body')
    assert draft_id is None
    mock_service[1].create.assert_called_once()
    mock_service[1].create.return_value.execute.assert_called_once()

@patch('src.utils.save_email_to_drafts.get_credentials', return_value=None)
def test_save_email_to_drafts_no_credentials(mock_get_credentials):
    draft_id = save_email_to_drafts('test@example.com', 'recipient@example.com', 'Subject', 'Body')
    assert draft_id is None
    mock_get_credentials.assert_called_once()

# test the save_data_to_excel function
def test_save_data_to_excel_existing_file(tmp_path):
    test_file = tmp_path / "test_excel.xlsx"
    # Create initial data
    initial_data = {'col1': 'initial1', 'col2': 'initial2'}
    save_data_to_excel(initial_data, str(test_file))  # CORRECTED

    # Add new data
    data = {'col1': 'value1', 'col2': 'value2'}
    save_data_to_excel(data, str(test_file))  # CORRECTED

    assert os.path.exists(str(test_file))
    # Verify content
    workbook = openpyxl.load_workbook(str(test_file))
    sheet = workbook.active
    # Check headers (first row)
    assert [cell.value for cell in sheet[1]] == ['col1', 'col2']
    # Check initial data (second row)
    assert [cell.value for cell in sheet[2]] == ['initial1', 'initial2']
    # Check new data (third row)
    assert [cell.value for cell in sheet[3]] == ['value1', 'value2']


def test_save_data_to_excel_new_file(tmp_path):
    test_file = tmp_path / "test_excel.xlsx"
    data = {'colA': 'valueA', 'colB': 'valueB'}
    save_data_to_excel(data, str(test_file))  # CORRECTED

    assert os.path.exists(str(test_file))
    workbook = openpyxl.load_workbook(str(test_file))
    sheet = workbook.active
    # Check headers
    assert [cell.value for cell in sheet[1]] == ['colA', 'colB']
    # Check data
    assert [cell.value for cell in sheet[2]] == ['valueA', 'valueB']

def test_save_data_to_excel_exception(tmp_path, caplog):
    # Test that an exception during saving is handled and logged.
    test_file = tmp_path / "test_excel.xlsx"
    data = {'col1': 'value1', 'col2': 'value2'}

    # Mock openpyxl.Workbook to raise an exception
    with patch('openpyxl.Workbook', side_effect=Exception("Workbook error")):
        save_data_to_excel(data, str(test_file))  # Pass file path
        assert "Error saving data to Excel" in caplog.text
        assert f"File path: {test_file}" in caplog.text