# tests/test_main4.py
import pandas as pd
import pytest
import pathlib
from unittest.mock import MagicMock
import src.main4 as main4

@pytest.fixture
def setup_test_environment(monkeypatch, tmp_path):
    # Setup temporary paths
    raw_excel_file = tmp_path / "test_to_read_website.xlsx"
    processed_excel_file = tmp_path / "processed.xlsx"
    skyfend_doc_file = tmp_path / "skyfend_business.docx"

    # Create dummy Excel file with valid data
    df = pd.DataFrame({
        "company": ["Test Company"],
        "recipient_email": ["test@example.com"],
        "website": ["http://example.com"],
        "contact person": ["John Doe"]
    })
    df.to_excel(raw_excel_file, index=False)

    # Create dummy Skyfend document
    skyfend_doc_file.write_text("Dummy Skyfend business content")

    # Monkeypatch paths in main4.py
    monkeypatch.setattr(main4, 'RAW_EXCEL_PATH', raw_excel_file)
    monkeypatch.setattr(main4, 'PROCESSED_EXCEL_PATH', processed_excel_file)
    monkeypatch.setattr(main4, 'SKYFEND_BUSINESS_DOC_PATH', skyfend_doc_file)

    # Mock dependencies to isolate test from external calls
    monkeypatch.setattr(main4, 'read_skyfend_business', lambda x: "Dummy Skyfend business content")
    monkeypatch.setattr(main4, 'get_website_content', lambda x: "Dummy website content")
    monkeypatch.setattr(main4, 'extract_main_business', lambda a,b: "Dummy main business")
    monkeypatch.setattr(main4, 'identify_cooperation_points', lambda a,b,c: "Dummy cooperation points")
    monkeypatch.setattr(main4, 'generate_developing_letter', lambda a,b,c,d,e: "Dummy letter content")
    monkeypatch.setattr(main4, 'select_relevant_images', lambda a,b: ["img1.jpg", "img2.jpg", "img3.jpg"])
    monkeypatch.setattr(main4, 'create_email_with_inline_images_and_attachments', lambda **kwargs: MagicMock())

    return {
        "processed_excel_file": processed_excel_file
    }

def test_main_workflow(setup_test_environment, monkeypatch):
    calls = []

    # Mock save_email_to_drafts to track if called
    def mock_save_email_to_drafts(*, mime_message):
        calls.append(mime_message)
        return "dummy_draft_id"

    monkeypatch.setattr(main4, 'save_email_to_drafts', mock_save_email_to_drafts)

    # Run main workflow
    main4.main()

    # Assert processed file created successfully
    processed_file = setup_test_environment["processed_excel_file"]
    assert processed_file.exists(), "Processed file does not exist."

    # Load the file and check content
    df_processed = pd.read_excel(processed_file)
    assert len(df_processed) == 1, "Processed file should have exactly one entry."

    row = df_processed.iloc[0]
    assert row['company'] == "Test Company", f"Expected 'Test Company', got '{row['company']}'"
    assert row['recipient_email'] == "test@example.com"

    # Assert email draft creation called exactly once
    assert len(calls) == 1, "Expected one call to save_email_to_drafts"
    assert calls[0] is not None, "Email draft message was None"
