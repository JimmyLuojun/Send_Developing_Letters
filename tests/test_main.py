import pytest
from unittest.mock import patch, MagicMock
from src.main import main, fetch_website_content
import requests
import os
import pathlib

# --- Mock the project root for consistent path handling ---
@pytest.fixture
def mock_project_root(tmp_path):
    with patch('src.main.PROJECT_ROOT', tmp_path):
        yield tmp_path

# Test fetch website content
@patch('requests.get')
def test_fetch_website_content_success(mock_get):
    mock_response = MagicMock()
    mock_response.text = "<html><body><h1>Test Website</h1></body></html>"
    mock_response.raise_for_status.return_value = None  # No exception
    mock_get.return_value = mock_response

    content = fetch_website_content("http://example.com")
    assert content == "<html><body><h1>Test Website</h1></body></html>"
    mock_get.assert_called_once_with("http://example.com", timeout=10)

@patch('requests.get')
def test_fetch_website_content_failure(mock_get):
    mock_get.side_effect = requests.exceptions.RequestException("Test Error")

    content = fetch_website_content("http://example.com")
    assert content == ""  # Should return an empty string on error

@patch('src.main.extract_company_data')
@patch('src.main.read_skyfend_business')
@patch('src.main.fetch_website_content')
@patch('src.main.extract_main_business')
@patch('src.main.identify_cooperation_points')
@patch('src.main.generate_developing_letter')
@patch('src.main.save_email_to_drafts')
@patch('src.main.save_data_to_excel')
def test_main_workflow(mock_save_data, mock_save_draft, mock_gen_letter,
                      mock_coop_points, mock_extract_biz, mock_fetch,
                      mock_read_skyfend, mock_extract_data, mock_project_root):

    # --- Setup for the test, using the mock_project_root ---
    mock_excel_file = mock_project_root / "data" / "raw" / "test_to_read_website.xlsx"
    mock_excel_file.parent.mkdir(parents=True, exist_ok=True)  # Create directories
    mock_excel_file.touch() # create the file
    mock_skyfend_file = mock_project_root / "data" / "raw" / "test_main Business of Skyfend.docx"
    mock_skyfend_file.parent.mkdir(parents=True, exist_ok=True)  # Create directories
    mock_skyfend_file.touch() # create the file

    # Create processed data directory
    processed_dir = mock_project_root / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    # Mock return values for all the functions called in main()
    mock_extract_data.return_value = [
        {'website': 'http://example.com', 'recipient_email': 'test@example.com',
        'company': 'Test Company', 'contact person': 'John Doe'}
    ]
    mock_read_skyfend.return_value = "Skyfend's business."
    mock_fetch.return_value = "Website content"
    mock_extract_biz.return_value = "Test company business."
    mock_coop_points.return_value = "Cooperation points"
    mock_gen_letter.return_value = "Generated letter"
    mock_save_draft.return_value = "draft_id"


    # Call the main function
    main()

    # Assert that the functions were called with the expected arguments
    mock_extract_data.assert_called_once() # Check the function call
    mock_read_skyfend.assert_called_once()
    mock_fetch.assert_called_once_with('http://example.com')
    mock_extract_biz.assert_called_once()
    mock_coop_points.assert_called_once()
    mock_gen_letter.assert_called_once()
    mock_save_draft.assert_called_once()
    mock_save_data.assert_called_once()

@patch('src.main.extract_company_data', return_value=[]) # Mock to return empty list
@patch('src.main.read_skyfend_business')
def test_main_no_company_data(mock_read_skyfend, mock_extract_data, mock_project_root):
    # --- Setup for the test, using the mock_project_root ---
    mock_excel_file = mock_project_root / "data" / "raw" / "test_to_read_website.xlsx"
    mock_excel_file.parent.mkdir(parents=True, exist_ok=True)  # Create directories
    mock_excel_file.touch() # create the file
    
    main() # Call the main function
    mock_extract_data.assert_called_once() # Check if it is called
    mock_read_skyfend.assert_not_called()  # Should not be called

@patch('src.main.extract_company_data')
@patch('src.main.read_skyfend_business', return_value="") # Mock return empty
def test_main_no_skyfend_business(mock_read_skyfend, mock_extract_data, mock_project_root):
    # --- Setup for the test, using the mock_project_root ---
    mock_excel_file = mock_project_root / "data" / "raw" / "test_to_read_website.xlsx"
    mock_excel_file.parent.mkdir(parents=True, exist_ok=True)  # Create directories
    mock_excel_file.touch() # create the file
    mock_skyfend_file = mock_project_root / "data" / "raw" / "test_main Business of Skyfend.docx"
    mock_skyfend_file.parent.mkdir(parents=True, exist_ok=True)  # Create directories
    mock_skyfend_file.touch() # create the file

    mock_extract_data.return_value = [{'website': 'http://ex.com', 'recipient_email': 'a@b.com'}] # Mock return value
    main() # Call the main
    mock_extract_data.assert_called_once() # Check it was called
    mock_read_skyfend.assert_called_once() # Check the reading was attempted

@patch('src.main.extract_company_data')
@patch('src.main.read_skyfend_business')
@patch('src.main.fetch_website_content', return_value="") # Return empty website content
def test_main_empty_website_content(mock_fetch, mock_read_skyfend, mock_extract_data, mock_project_root):
    # --- Setup for directories ---
    mock_excel_file = mock_project_root / "data" / "raw" / "test_to_read_website.xlsx"
    mock_excel_file.parent.mkdir(parents=True, exist_ok=True)
    mock_excel_file.touch()
    mock_skyfend_file = mock_project_root / "data" / "raw" / "test_main Business of Skyfend.docx"
    mock_skyfend_file.parent.mkdir(parents=True, exist_ok=True)
    mock_skyfend_file.touch()
    
    # Mock returns
    mock_extract_data.return_value = [{'website': 'http://ex.com', 'recipient_email': 'a@b.com', 'company': 'Test Co', 'contact person': 'John'}]
    mock_read_skyfend.return_value = "Skyfend business"
    
    main()
    
    mock_extract_data.assert_called_once()
    mock_read_skyfend.assert_called_once() 
    mock_fetch.assert_called_once_with('http://ex.com')
    # No further processing should happen with empty website content 