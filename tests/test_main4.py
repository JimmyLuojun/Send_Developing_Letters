# tests/test_main4.py
import os
import pathlib
import pandas as pd
import pytest
from email.mime.multipart import MIMEMultipart

# Import the module under test. Adjust the import if needed.
from src import main4

# A dummy MIME message class for simulation.
class DummyMIMEMessage:
    def as_bytes(self):
        return b"dummy mime message bytes"

# Dummy implementations for external dependencies.
def dummy_read_skyfend_business(doc_path):
    return "dummy skyfend business content"

def dummy_extract_main_business(api_key, website_content):
    return "dummy main business"

def dummy_identify_cooperation_points(api_key, skyfend_business, main_business):
    return "dummy cooperation points"

def dummy_generate_developing_letter(api_key, prompt, cooperation_points, company, contact):
    return "dummy letter content\nLine2\nLine3\nLine4"

def dummy_save_email_to_drafts(*, mime_message):
    return "dummy_draft_id"

def dummy_get_website_content(url, max_content_length=2000):
    return "dummy website content"

def dummy_select_relevant_images(email_body, company_name):
    # Return 3 dummy image paths (they need not exist for this test)
    return ["dummy1.jpg", "dummy2.jpg", "dummy3.jpg"]

def dummy_create_email_with_inline_images_and_attachments(sender, recipient, subject, body, image_paths, attachment_paths):
    # Return a dummy MIME message (satisfies as_bytes() interface)
    return DummyMIMEMessage()

@pytest.fixture(autouse=True)
def patch_dependencies(monkeypatch, tmp_path):
    # Patch environment variables
    monkeypatch.setenv("API_KEY", "dummy_api_key")
    monkeyatch_setenv = monkeypatch.setenv
    monkeyatch_setenv("GMAIL_ACCOUNT", "dummy@gmail.com")

    # Patch functions in main4.
    monkeypatch.setattr(main4, "read_skyfend_business", dummy_read_skyfend_business)
    monkeypatch.setattr(main4, "extract_main_business", dummy_extract_main_business)
    monkeypatch.setattr(main4, "identify_cooperation_points", dummy_identify_cooperation_points)
    monkeypatch.setattr(main4, "generate_developing_letter", dummy_generate_developing_letter)
    monkeypatch.setattr(main4, "save_email_to_drafts", dummy_save_email_to_drafts)
    monkeypatch.setattr(main4, "get_website_content", dummy_get_website_content)
    monkeypatch.setattr(main4, "select_relevant_images", dummy_select_relevant_images)
    monkeypatch.setattr(main4, "create_email_with_inline_images_and_attachments", dummy_create_email_with_inline_images_and_attachments)

    # Create a temporary raw Excel file with a single valid row.
    raw_data = pd.DataFrame({
        "company": ["Test Company"],
        "recipient_email": ["test@example.com"],
        "website": ["http://example.com"],
        "contact person": ["Test Contact"]
    })
    raw_excel_file = tmp_path / "test_to_read_website.xlsx"
    raw_data.to_excel(raw_excel_file, index=False)
    monkeypatch.setattr(main4, "RAW_EXCEL_PATH", raw_excel_file)

    # Set a temporary path for processed data.
    processed_excel_file = tmp_path / "processed.xlsx"
    monkeypatch.setattr(main4, "PROCESSED_EXCEL_PATH", processed_excel_file)

    # Create a dummy skyfend business document.
    skyfend_business_file = tmp_path / "test_main Business of Skyfend.docx"
    skyfend_business_file.write_text("dummy content")
    monkeypatch.setattr(main4, "SKYFEND_BUSINESS_DOC_PATH", skyfend_business_file)

def test_main4(monkeypatch):
    # Run the main processing function.
    main4.main()

    # Check that the processed Excel file now exists and has one row with expected values.
    processed_file = pathlib.Path(main4.PROCESSED_EXCEL_PATH)
    assert processed_file.exists()

    df = pd.read_excel(processed_file)
    assert not df.empty
    row = df.iloc[0]
    assert row['company'] == "Test Company"
    assert row['recipient_email'] == "test@example.com"
