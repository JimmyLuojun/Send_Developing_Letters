# tests/test_main.py

import pytest
from unittest.mock import patch, MagicMock
from src.main import main, fetch_website_content
import requests
import os
import pathlib

# --- Fixture to override PROJECT_ROOT ---
@pytest.fixture
def mock_project_root(tmp_path):
    with patch('src.main.PROJECT_ROOT', tmp_path):
        yield tmp_path

# --- Tests for fetch_website_content ---
@patch('requests.get')
def test_fetch_website_content_success(mock_get):
    """Test successful website content fetching."""
    mock_response = MagicMock()
    mock_response.text = "<html><body><h1>Test Website</h1></body></html>"
    mock_response.raise_for_status.return_value = None  # No exception
    mock_get.return_value = mock_response

    content = fetch_website_content("http://example.com")
    assert content == "<html><body><h1>Test Website</h1></body></html>"
    mock_get.assert_called_once_with("http://example.com", timeout=10)

@patch('requests.get')
def test_fetch_website_content_failure(mock_get):
    """Test website content fetching failure."""
    mock_get.side_effect = requests.exceptions.RequestException("Test Error")

    content = fetch_website_content("http://example.com")
    assert content == ""

# --- Tests for main() workflow ---

@patch('src.main.extract_company_data')
@patch('src.main.read_skyfend_business')
@patch('src.main.fetch_website_content')
@patch('src.main.extract_main_business')
@patch('src.main.identify_cooperation_points')
@patch('src.main.generate_developing_letter')
@patch('src.main.save_email_to_drafts')
@patch('src.main.save_data_to_excel')
@patch.dict(os.environ, {"API_KEY": "fake_api_key", "GMAIL_ACCOUNT": "test@example.com"})
def test_main_workflow(mock_save_data, mock_save_draft, mock_gen_letter,
                       mock_coop_points, mock_extract_biz, mock_fetch,
                       mock_read_skyfend, mock_extract_data, mock_project_root):
    """Test the full workflow with successful operations."""
    # Setup files and directories
    mock_excel_file = mock_project_root / "data" / "raw" / "test_to_read_website.xlsx"
    mock_excel_file.parent.mkdir(parents=True, exist_ok=True)
    mock_excel_file.touch()
    mock_skyfend_file = mock_project_root / "data" / "raw" / "test_main Business of Skyfend.docx"
    mock_skyfend_file.parent.mkdir(parents=True, exist_ok=True)
    mock_skyfend_file.touch()
    (mock_project_root / "data" / "processed").mkdir(parents=True, exist_ok=True)

    # Mock return values
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

    main()

    mock_extract_data.assert_called_once()
    mock_read_skyfend.assert_called_once()
    mock_fetch.assert_called_once_with('http://example.com')
    mock_extract_biz.assert_called_once()
    mock_coop_points.assert_called_once()
    mock_gen_letter.assert_called_once()
    mock_save_draft.assert_called_once_with("test@example.com",
                                              'test@example.com', 
                                              "Potential Cooperation with Skyfend and Test Company", 
                                              "Generated letter")
    mock_save_data.assert_called_once()

@patch('src.main.extract_company_data', return_value=[])
@patch('src.main.read_skyfend_business')
@patch.dict(os.environ, {"API_KEY": "fake_api_key", "GMAIL_ACCOUNT": "test@example.com"})
def test_main_no_company_data(mock_read_skyfend, mock_extract_data, mock_project_root):
    """Test when no company data is found."""
    # Setup necessary files
    mock_excel_file = mock_project_root / "data" / "raw" / "test_excel.xlsx"
    mock_excel_file.parent.mkdir(parents=True, exist_ok=True)
    mock_excel_file.touch()
    mock_skyfend_file = mock_project_root / "data" / "raw" / "test_skyfend.docx"
    mock_skyfend_file.touch()

    mock_read_skyfend.return_value = "Skyfend business"
    main()
    mock_extract_data.assert_called_once()
    # Since extract_company_data returns an empty list, read_skyfend_business should not be called
    mock_read_skyfend.assert_not_called()

@patch('src.main.extract_company_data')
@patch('src.main.read_skyfend_business', return_value="")
@patch.dict(os.environ, {"API_KEY": "fake_api_key", "GMAIL_ACCOUNT": "test@example.com"})
def test_main_no_skyfend_business(mock_read_skyfend, mock_extract_data, mock_project_root):
    """Test with an empty Skyfend business description."""
    # Setup files
    mock_excel_file = mock_project_root / "data" / "raw" / "test_excel.xlsx"
    mock_excel_file.parent.mkdir(parents=True, exist_ok=True)
    mock_excel_file.touch()
    mock_skyfend_file = mock_project_root / "data" / "raw" / "test_skyfend.docx"
    mock_skyfend_file.touch()

    mock_extract_data.return_value = [{'website': 'http://ex.com', 'recipient_email': 'a@b.com'}]
    main()
    mock_read_skyfend.assert_called_once()
    # The workflow should exit early when Skyfend's business is empty

@patch('src.main.extract_company_data')
@patch('src.main.read_skyfend_business')
@patch('src.main.fetch_website_content', return_value="")
@patch('src.main.extract_main_business')
@patch('src.main.identify_cooperation_points')
@patch('src.main.generate_developing_letter')
@patch('src.main.save_email_to_drafts')
@patch('src.main.save_data_to_excel')
@patch.dict(os.environ, {"API_KEY": "fake_api_key", "GMAIL_ACCOUNT": "test@example.com"})
def test_main_empty_website_content(mock_save_data, mock_save_draft, mock_gen_letter,
                                    mock_coop_points, mock_extract_biz, mock_fetch,
                                    mock_read_skyfend, mock_extract_data, mock_project_root):
    """Test when website content fetching fails."""
    # Setup files
    mock_excel_file = mock_project_root / "data" / "raw" / "test_excel.xlsx"
    mock_excel_file.parent.mkdir(parents=True, exist_ok=True)
    mock_excel_file.touch()
    mock_skyfend_file = mock_project_root / "data" / "raw" / "test_skyfend.docx"
    mock_skyfend_file.touch()

    mock_extract_data.return_value = [
        {'website': 'http://example.com', 'recipient_email': 'test@example.com',
         'company': 'Test Company', 'contact person': 'John Doe'}
    ]
    mock_read_skyfend.return_value = "Skyfend's business."
    mock_extract_biz.return_value = "Test company business."
    mock_coop_points.return_value = "Cooperation points"
    mock_gen_letter.return_value = "Generated letter"
    mock_save_draft.return_value = "draft_id"

    main()
    mock_extract_data.assert_called_once()
    mock_read_skyfend.assert_called_once()
    mock_fetch.assert_called_once_with('http://example.com')
    # If website content is empty, extract_main_business should not be called
    mock_extract_biz.assert_not_called()

@patch('src.main.extract_company_data')
@patch('src.main.read_skyfend_business')
@patch('src.main.fetch_website_content')
@patch('src.main.extract_main_business', return_value=None)
@patch('src.main.identify_cooperation_points')
@patch('src.main.generate_developing_letter')
@patch('src.main.save_email_to_drafts')
@patch('src.main.save_data_to_excel')
@patch.dict(os.environ, {"API_KEY": "fake_api_key", "GMAIL_ACCOUNT": "test@example.com"})
def test_main_no_business_extract(mock_save_data, mock_save_draft, mock_gen_letter,
                                  mock_coop_points, mock_extract_biz, mock_fetch,
                                  mock_read_skyfend, mock_extract_data, mock_project_root):
    """Test when main business extraction fails."""
    # Setup files
    mock_excel_file = mock_project_root / "data" / "raw" / "test_excel.xlsx"
    mock_excel_file.parent.mkdir(parents=True, exist_ok=True)
    mock_excel_file.touch()
    mock_skyfend_file = mock_project_root / "data" / "raw" / "test_skyfend.docx"
    mock_skyfend_file.touch()

    mock_extract_data.return_value = [
        {'website': 'http://example.com', 'recipient_email': 'test@example.com',
         'company': 'Test Company', 'contact person': 'John Doe'}
    ]
    mock_read_skyfend.return_value = "Skyfend's business."
    mock_fetch.return_value = "Website content"
    mock_coop_points.return_value = "Cooperation points"
    mock_gen_letter.return_value = "Generated letter"
    mock_save_draft.return_value = "draft_id"

    main()
    mock_extract_data.assert_called_once()
    mock_read_skyfend.assert_called_once()
    mock_fetch.assert_called_once_with('http://example.com')
    mock_extract_biz.assert_called_once()
    # Since business extraction failed, identify_cooperation_points should not be called
    mock_coop_points.assert_not_called()

@patch('src.main.extract_company_data')
@patch('src.main.read_skyfend_business')
@patch('src.main.fetch_website_content')
@patch('src.main.extract_main_business')
@patch('src.main.identify_cooperation_points', return_value="No cooperation points identified")
@patch('src.main.generate_developing_letter')
@patch('src.main.save_email_to_drafts')
@patch('src.main.save_data_to_excel')
@patch.dict(os.environ, {"API_KEY": "fake_api_key", "GMAIL_ACCOUNT": "test@example.com"})
def test_main_no_coopertion_points(mock_save_data, mock_save_draft, mock_gen_letter,
                                   mock_coop_points, mock_extract_biz, mock_fetch,
                                   mock_read_skyfend, mock_extract_data, mock_project_root):
    """Test when no cooperation points are identified."""
    # Setup files
    mock_excel_file = mock_project_root / "data" / "raw" / "test_excel.xlsx"
    mock_excel_file.parent.mkdir(parents=True, exist_ok=True)
    mock_excel_file.touch()
    mock_skyfend_file = mock_project_root / "data" / "raw" / "test_skyfend.docx"
    mock_skyfend_file.touch()

    mock_extract_data.return_value = [
        {'website': 'http://example.com', 'recipient_email': 'test@example.com',
         'company': 'Test Company', 'contact person': 'John Doe'}
    ]
    mock_read_skyfend.return_value = "Skyfend's business."
    mock_fetch.return_value = "Website content"
    mock_extract_biz.return_value = "Test company business."
    mock_gen_letter.return_value = "Generated letter"
    mock_save_draft.return_value = "draft_id"

    main()
    mock_extract_data.assert_called_once()
    mock_read_skyfend.assert_called_once()
    mock_fetch.assert_called_once_with('http://example.com')
    mock_extract_biz.assert_called_once()
    mock_coop_points.assert_called_once()
    # With no cooperation points, letter generation should not proceed
    mock_gen_letter.assert_not_called()

@patch('src.main.extract_company_data')
@patch('src.main.read_skyfend_business')
@patch('src.main.fetch_website_content')
@patch('src.main.extract_main_business')
@patch('src.main.identify_cooperation_points')
@patch('src.main.generate_developing_letter', return_value='No letter content generated')
@patch('src.main.save_email_to_drafts')
@patch('src.main.save_data_to_excel')
@patch.dict(os.environ, {"API_KEY": "fake_api_key", "GMAIL_ACCOUNT": "test@example.com"})
def test_main_no_letter_generated(mock_save_data, mock_save_draft, mock_gen_letter,
                                  mock_coop_points, mock_extract_biz, mock_fetch,
                                  mock_read_skyfend, mock_extract_data, mock_project_root):
    """Test when no letter content is generated."""
    # Setup files
    mock_excel_file = mock_project_root / "data" / "raw" / "test_excel.xlsx"
    mock_excel_file.parent.mkdir(parents=True, exist_ok=True)
    mock_excel_file.touch()
    mock_skyfend_file = mock_project_root / "data" / "raw" / "test_skyfend.docx"
    mock_skyfend_file.touch()

    mock_extract_data.return_value = [
        {'website': 'http://example.com', 'recipient_email': 'test@example.com',
         'company': 'Test Company', 'contact person': 'John Doe'}
    ]
    mock_read_skyfend.return_value = "Skyfend's business."
    mock_fetch.return_value = "Website content"
    mock_extract_biz.return_value = "Test company business."
    mock_coop_points.return_value = "Cooperation points"
    # Letter generation returns no content
    mock_gen_letter.return_value = "No letter content generated"
    mock_save_draft.return_value = "draft_id"

    main()
    mock_extract_data.assert_called_once()
    mock_read_skyfend.assert_called_once()
    mock_fetch.assert_called_once_with('http://example.com')
    mock_extract_biz.assert_called_once()
    mock_coop_points.assert_called_once()
    mock_gen_letter.assert_called_once()
    # Since no letter is generated, save_email_to_drafts should not be successful
    # (We assume main() will skip saving when letter content is "No letter content generated")

@patch('src.main.extract_company_data')
@patch('src.main.read_skyfend_business')
@patch('src.main.fetch_website_content')
@patch('src.main.extract_main_business')
@patch('src.main.identify_cooperation_points')
@patch('src.main.generate_developing_letter')
@patch('src.main.save_email_to_drafts', return_value=None)  # Simulate save failure
@patch('src.main.save_data_to_excel')
@patch.dict(os.environ, {"API_KEY": "fake_api_key", "GMAIL_ACCOUNT": "test@example.com"})
def test_main_no_draft_saved(mock_save_data, mock_save_draft, mock_gen_letter,
                             mock_coop_points, mock_extract_biz, mock_fetch,
                             mock_read_skyfend, mock_extract_data, mock_project_root):
    """Test when saving the email draft fails."""
    # Setup files
    mock_excel_file = mock_project_root / "data" / "raw" / "test_excel.xlsx"
    mock_excel_file.parent.mkdir(parents=True, exist_ok=True)
    mock_excel_file.touch()
    mock_skyfend_file = mock_project_root / "data" / "raw" / "test_skyfend.docx"
    mock_skyfend_file.touch()

    mock_extract_data.return_value = [
        {'website': 'http://example.com', 'recipient_email': 'test@example.com',
         'company': 'Test Company', 'contact person': 'John Doe'}
    ]
    mock_read_skyfend.return_value = "Skyfend's business."
    mock_fetch.return_value = "Website content"
    mock_extract_biz.return_value = "Test company business."
    mock_coop_points.return_value = "Cooperation points"
    mock_gen_letter.return_value = "Generated letter"

    main()
    # Assert that save_data_to_excel was not called because draft saving failed.
    mock_save_data.assert_not_called()
