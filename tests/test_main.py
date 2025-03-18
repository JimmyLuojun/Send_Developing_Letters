# tests/test_main.py
import os
import pathlib
import pandas as pd
import pytest
from unittest.mock import patch

# Import the main function from main4.py (the updated module)
from src.main4 import main

@patch('src.main4.extract_company_data')
@patch('src.main4.read_skyfend_business')
@patch('src.main4.get_website_content')
@patch('src.main4.extract_main_business')
@patch('src.main4.identify_cooperation_points')
@patch('src.main4.generate_developing_letter')
@patch('src.main4.save_email_to_drafts')
@patch.dict(os.environ, {"API_KEY": "fake_api_key", "GMAIL_ACCOUNT": "test@example.com"})
def test_main_workflow(mock_save_draft, mock_gen_letter,
                       mock_coop_points, mock_extract_biz, mock_fetch,
                       mock_read_skyfend, mock_extract_data, monkeypatch, tmp_path):
    """
    Test the full workflow using main4.py.
    Instead of asserting on positional parameters for save_email_to_drafts,
    we check that it was called with a non-None 'mime_message' keyword argument.
    """
    # Setup a dedicated temporary directory for this test.
    test_dir = tmp_path / "main_test"
    test_dir.mkdir()
    
    raw_excel_file = test_dir / "test_to_read_website.xlsx"
    skyfend_file = test_dir / "test_main Business of Skyfend.docx"
    processed_excel_file = test_dir / "processed.xlsx"
    # Remove processed file if it exists.
    if processed_excel_file.exists():
        processed_excel_file.unlink()
    
    # Create dummy raw data with expected values.
    raw_data = pd.DataFrame({
        "company": ["Test Company"],
        "recipient_email": ["test@example.com"],
        "website": ["http://example.com"],
        "contact person": ["John Doe"]
    })
    raw_data.to_excel(raw_excel_file, index=False)
    
    # Patch the module-level attributes in main4.py.
    monkeypatch.setattr("src.main4.RAW_EXCEL_PATH", raw_excel_file)
    monkeypatch.setattr("src.main4.PROCESSED_EXCEL_PATH", processed_excel_file)
    skyfend_file.parent.mkdir(parents=True, exist_ok=True)
    skyfend_file.write_text("dummy content")
    monkeypatch.setattr("src.main4.SKYFEND_BUSINESS_DOC_PATH", skyfend_file)
    
    # Set dummy return values for dependencies.
    mock_extract_data.return_value = [
        {'website': 'http://example.com',
         'recipient_email': 'test@example.com',
         'company': 'Test Company',
         'contact person': 'John Doe'}
    ]
    mock_read_skyfend.return_value = "Skyfend's business."
    mock_fetch.return_value = "Website content"
    mock_extract_biz.return_value = "Test company business."
    mock_coop_points.return_value = "Cooperation points"
    mock_gen_letter.return_value = "Generated letter"
    mock_save_draft.return_value = "draft_id"
    
    # Run the workflow.
    main()
    
    # Verify that save_email_to_drafts was called once with a non-None mime_message keyword.
    assert mock_save_draft.call_count == 1
    _, kwargs = mock_save_draft.call_args
    assert 'mime_message' in kwargs, "Expected keyword 'mime_message' not found."
    assert kwargs['mime_message'] is not None, "mime_message is None."
    
    # Verify that the processed Excel file exists and contains the expected data.
    processed_file = pathlib.Path(processed_excel_file)
    assert processed_file.exists(), "Processed Excel file was not created."
    df = pd.read_excel(processed_file)
    assert not df.empty, "Processed Excel file is empty."
    row = df.iloc[0]
    # Expect the company name to match our dummy raw data.
    assert row['company'] == "Test Company", f"Expected 'Test Company', got '{row['company']}'"
