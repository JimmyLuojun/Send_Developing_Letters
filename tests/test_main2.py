import pathlib
import pandas as pd
import pytest
import src.main2 as main2  # Adjust the import if needed

@pytest.fixture
def temp_environment(tmp_path, monkeypatch):
    """
    Set up a temporary directory structure with dummy Excel and business document files.
    Patch external functions in main2.py so that they return dummy data, avoiding real API calls.
    """
    # Create a temporary project root directory
    base_dir = tmp_path / "Send_Developing_Letters"
    base_dir.mkdir()

    # Create data/raw folder and dummy Excel file for raw input data
    raw_dir = base_dir / "data" / "raw"
    raw_dir.mkdir(parents=True)
    test_excel_path = raw_dir / "test_to_read_website.xlsx"
    
    # Default raw data: one valid record
    df = pd.DataFrame({
        "company": ["Test Company"],
        "recipient_email": ["recipient@example.com"],
        "website": ["http://example.com"],
        "contact person": ["Test Contact"]
    })
    df.to_excel(test_excel_path, index=False)

    # Create a dummy Skyfend business document
    business_doc_path = raw_dir / "test_main Business of Skyfend.docx"
    business_doc_path.write_text("Dummy skyfend business content")

    # Create data/processed folder for processed Excel file
    processed_dir = base_dir / "data" / "processed"
    processed_dir.mkdir(parents=True)
    processed_excel_path = processed_dir / "saving_company_data_after_creating_letters.xlsx"

    # Create logs folder
    logs_dir = base_dir / "logs"
    logs_dir.mkdir(parents=True)

    # Patch the paths in main2.py to use our temporary environment
    monkeypatch.setattr(main2, "PROJECT_ROOT", base_dir)
    monkeypatch.setattr(main2, "RAW_EXCEL_PATH", test_excel_path)
    monkeypatch.setattr(main2, "SKYFEND_BUSINESS_DOC_PATH", business_doc_path)
    monkeypatch.setattr(main2, "PROCESSED_EXCEL_PATH", processed_excel_path)

    # Patch external function calls to avoid real network and API calls
    monkeypatch.setattr(main2, "get_website_content", lambda url, max_content_length=2000: "Dummy website content")
    monkeypatch.setattr(main2, "extract_main_business", lambda api, content: "Dummy main business")
    monkeypatch.setattr(main2, "identify_cooperation_points", lambda api, sb, mb: "Dummy cooperation points")
    monkeypatch.setattr(main2, "generate_developing_letter", lambda api, prompt, cp, comp, contact: "Dummy email body")
    monkeypatch.setattr(main2, "read_skyfend_business", lambda path: "Dummy skyfend business")
    # Patch save_email_to_drafts so it returns a dummy draft ID without doing a real API call
    monkeypatch.setattr(main2, "save_email_to_drafts", lambda *args, **kwargs: "dummy_draft_id")

    return base_dir, processed_excel_path

def read_processed_excel(processed_excel_path):
    """Helper function to read the processed Excel file (if it exists)."""
    if processed_excel_path.exists():
        return pd.read_excel(processed_excel_path)
    return pd.DataFrame()

def test_main2_valid_record(temp_environment):
    """
    Test the standard valid record processing.
    """
    base_dir, processed_excel_path = temp_environment
    # Run main2.main() with one valid record.
    try:
        main2.main()
    except Exception as e:
        pytest.fail(f"main2.main() raised an exception: {e}")

    df = read_processed_excel(processed_excel_path)
    assert not df.empty, "Processed Excel file should not be empty."
    # Check that the company name is correct.
    assert df.iloc[0]['company'] == "Test Company"

def test_main2_invalid_email(tmp_path, monkeypatch):
    """
    Test that a record with an invalid email address is skipped.
    """
    # Set up temporary environment with an invalid email record.
    base_dir = tmp_path / "Send_Developing_Letters"
    base_dir.mkdir()
    raw_dir = base_dir / "data" / "raw"
    raw_dir.mkdir(parents=True)
    test_excel_path = raw_dir / "test_to_read_website.xlsx"
    df = pd.DataFrame({
        "company": ["Invalid Email Company"],
        "recipient_email": ["invalid_email"],  # invalid email
        "website": ["http://example.com"],
        "contact person": ["Test Contact"]
    })
    df.to_excel(test_excel_path, index=False)
    business_doc_path = raw_dir / "test_main Business of Skyfend.docx"
    business_doc_path.write_text("Dummy business content")
    processed_dir = base_dir / "data" / "processed"
    processed_dir.mkdir(parents=True)
    processed_excel_path = processed_dir / "saving_company_data_after_creating_letters.xlsx"
    logs_dir = base_dir / "logs"
    logs_dir.mkdir(parents=True)

    # Patch paths in main2.py
    monkeypatch.setattr(main2, "PROJECT_ROOT", base_dir)
    monkeypatch.setattr(main2, "RAW_EXCEL_PATH", test_excel_path)
    monkeyatch_value = business_doc_path  # avoid lint error
    monkeypatch.setattr(main2, "SKYFEND_BUSINESS_DOC_PATH", business_doc_path)
    monkeypatch.setattr(main2, "PROCESSED_EXCEL_PATH", processed_excel_path)

    # Patch external functions as before.
    monkeypatch.setattr(main2, "get_website_content", lambda url, max_content_length=2000: "Dummy website content")
    monkeypatch.setattr(main2, "extract_main_business", lambda api, content: "Dummy main business")
    monkeypatch.setattr(main2, "identify_cooperation_points", lambda api, sb, mb: "Dummy cooperation points")
    monkeypatch.setattr(main2, "generate_developing_letter", lambda api, prompt, cp, comp, contact: "Dummy email body")
    monkeypatch.setattr(main2, "read_skyfend_business", lambda path: "Dummy skyfend business")
    monkeypatch.setattr(main2, "save_email_to_drafts", lambda *args, **kwargs: "dummy_draft_id")

    # Run main2.main()
    main2.main()
    df_processed = read_processed_excel(processed_excel_path)
    # Expect no record processed since email is invalid.
    assert df_processed.empty, "No records should be processed when email is invalid."

def test_main2_empty_website_content(tmp_path, monkeypatch):
    """
    Test that a record is skipped when get_website_content returns an empty string.
    """
    base_dir = tmp_path / "Send_Developing_Letters"
    base_dir.mkdir()
    raw_dir = base_dir / "data" / "raw"
    raw_dir.mkdir(parents=True)
    test_excel_path = raw_dir / "test_to_read_website.xlsx"
    df = pd.DataFrame({
        "company": ["No Website Content Company"],
        "recipient_email": ["recipient@example.com"],
        "website": ["http://example.com"],
        "contact person": ["Test Contact"]
    })
    df.to_excel(test_excel_path, index=False)
    business_doc_path = raw_dir / "test_main Business of Skyfend.docx"
    business_doc_path.write_text("Dummy business content")
    processed_dir = base_dir / "data" / "processed"
    processed_dir.mkdir(parents=True)
    processed_excel_path = processed_dir / "saving_company_data_after_creating_letters.xlsx"
    logs_dir = base_dir / "logs"
    logs_dir.mkdir(parents=True)

    monkeypatch.setattr(main2, "PROJECT_ROOT", base_dir)
    monkeypatch.setattr(main2, "RAW_EXCEL_PATH", test_excel_path)
    monkeypatch.setattr(main2, "SKYFEND_BUSINESS_DOC_PATH", business_doc_path)
    monkeypatch.setattr(main2, "PROCESSED_EXCEL_PATH", processed_excel_path)

    # Force get_website_content to return an empty string.
    monkeypatch.setattr(main2, "get_website_content", lambda url, max_content_length=2000: "")
    monkeypatch.setattr(main2, "extract_main_business", lambda api, content: "Dummy main business")
    monkeypatch.setattr(main2, "identify_cooperation_points", lambda api, sb, mb: "Dummy cooperation points")
    monkeypatch.setattr(main2, "generate_developing_letter", lambda api, prompt, cp, comp, contact: "Dummy email body")
    monkeypatch.setattr(main2, "read_skyfend_business", lambda path: "Dummy skyfend business")
    monkeypatch.setattr(main2, "save_email_to_drafts", lambda *args, **kwargs: "dummy_draft_id")

    main2.main()
    df_processed = read_processed_excel(processed_excel_path)
    # Since website content is empty, the record should be skipped.
    assert df_processed.empty, "Record should be skipped when website content is empty."

def test_main2_duplicate_record(temp_environment, tmp_path, monkeypatch):
    """
    Test that if two rows have the same company and recipient email, only the first record is processed.
    """
    base_dir, processed_excel_path = temp_environment
    # Overwrite raw Excel file with two rows having identical company and recipient email.
    raw_excel_path = base_dir / "data" / "raw" / "test_to_read_website.xlsx"
    df = pd.DataFrame({
        "company": ["Duplicate Company", "Duplicate Company"],
        "recipient_email": ["dup@example.com", "dup@example.com"],
        "website": ["http://example.com", "http://example.com"],
        "contact person": ["Contact 1", "Contact 1"]
    })
    df.to_excel(raw_excel_path, index=False)
    # Ensure external functions are patched as in the fixture.
    monkeypatch.setattr(main2, "get_website_content", lambda url, max_content_length=2000: "Dummy website content")
    monkeypatch.setattr(main2, "extract_main_business", lambda api, content: "Dummy main business")
    monkeypatch.setattr(main2, "identify_cooperation_points", lambda api, sb, mb: "Dummy cooperation points")
    monkeypatch.setattr(main2, "generate_developing_letter", lambda api, prompt, cp, comp, contact: "Dummy email body")
    monkeypatch.setattr(main2, "read_skyfend_business", lambda path: "Dummy skyfend business")
    monkeypatch.setattr(main2, "save_email_to_drafts", lambda *args, **kwargs: "dummy_draft_id")

    main2.main()
    df_processed = read_processed_excel(processed_excel_path)
    # According to main2.py, the second duplicate should be skipped.
    assert len(df_processed) == 1, "Duplicate record should be skipped; only one record expected."

def test_main2_multiple_companies(temp_environment, tmp_path, monkeypatch):
    """
    Test processing with multiple distinct companies.
    """
    base_dir, processed_excel_path = temp_environment
    raw_excel_path = base_dir / "data" / "raw" / "test_to_read_website.xlsx"
    df = pd.DataFrame({
        "company": ["Company A", "Company B"],
        "recipient_email": ["a@example.com", "b@example.com"],
        "website": ["http://example.com", "http://example.com"],
        "contact person": ["Contact A", "Contact B"]
    })
    df.to_excel(raw_excel_path, index=False)
    monkeypatch.setattr(main2, "get_website_content", lambda url, max_content_length=2000: "Dummy website content")
    monkeypatch.setattr(main2, "extract_main_business", lambda api, content: "Dummy main business")
    monkeypatch.setattr(main2, "identify_cooperation_points", lambda api, sb, mb: "Dummy cooperation points")
    monkeypatch.setattr(main2, "generate_developing_letter", lambda api, prompt, cp, comp, contact: "Dummy email body")
    monkeypatch.setattr(main2, "read_skyfend_business", lambda path: "Dummy skyfend business")
    monkeypatch.setattr(main2, "save_email_to_drafts", lambda *args, **kwargs: "dummy_draft_id")

    main2.main()
    df_processed = read_processed_excel(processed_excel_path)
    # Two distinct companies should yield two records.
    assert len(df_processed) == 2, "Two records should be processed for two distinct companies."
    assert set(df_processed['company']) == {"Company A", "Company B"}
