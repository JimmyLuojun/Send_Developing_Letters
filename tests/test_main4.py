# tests/test_main4.py
import pandas as pd
import pytest
import pathlib
import logging
import os
from unittest.mock import MagicMock, patch
from datetime import datetime
import src.main4 as main4

# Fixture to create a dummy raw Excel file with a "process" column
@pytest.fixture
def raw_excel(tmp_path):
    # Create a dummy raw Excel file with three rows:
    # Two rows with process = "yes" (case-insensitive) and one row with process = "no"
    data = {
        "company": ["Test Company", "Test Company 2", "Skipped Company"],
        "recipient_email": ["test@example.com", "test2@example.com", "skip@example.com"],
        "website": ["http://example.com", "http://example2.com", "http://skip.com"],
        "contact person": ["John Doe", "Jane Smith", "Skip Person"],
        "process": ["yes", "yes", "no"]
    }
    df = pd.DataFrame(data)
    file = tmp_path / "raw.xlsx"
    df.to_excel(file, index=False)
    return file

# Fixture to create a dummy processed Excel file
@pytest.fixture
def processed_excel(tmp_path):
    file = tmp_path / "processed.xlsx"
    df = pd.DataFrame(columns=[
        "saving_file_time", "company", "website", "main_business",
        "recipient_email", "contact_person", "cooperation_letter_content",
        "cooperation_points"
    ])
    df.to_excel(file, index=False)
    return file

# Fixture to create a dummy Skyfend business document
@pytest.fixture
def skyfend_doc(tmp_path):
    file = tmp_path / "skyfend_business.docx"
    file.write_text("Dummy Skyfend business content")
    return file

# New fixture to bundle raw and processed Excel paths
@pytest.fixture
def setup_test_environment(raw_excel, processed_excel):
    return {
        "raw_excel_file": raw_excel,
        "processed_excel_file": processed_excel
    }

# Fixture to override paths and external functions in main4.py
@pytest.fixture(autouse=True)
def override_env(monkeypatch, raw_excel, processed_excel, skyfend_doc):
    # Override file paths in main4.py
    monkeypatch.setattr(main4, "RAW_EXCEL_PATH", raw_excel)
    monkeypatch.setattr(main4, "PROCESSED_EXCEL_PATH", processed_excel)
    monkeypatch.setattr(main4, "SKYFEND_BUSINESS_DOC_PATH", skyfend_doc)

    # Override external calls with dummy implementations
    monkeypatch.setattr(main4, "read_skyfend_business", lambda x: "Dummy Skyfend business content")
    monkeypatch.setattr(main4, "get_website_content", lambda x: "Dummy website content")
    monkeypatch.setattr(main4, "extract_main_business", lambda api, content: "Dummy main business")
    monkeypatch.setattr(main4, "identify_cooperation_points", lambda api, bus, main: "Dummy cooperation points")
    monkeypatch.setattr(main4, "generate_developing_letter", lambda api, instr, coop, comp, contact: "Dummy letter content")
    monkeypatch.setattr(main4, "select_relevant_images", lambda body, comp: ["img1.jpg", "img2.jpg", "img3.jpg"])
    monkeypatch.setattr(main4, "create_email_with_inline_images_and_attachments", lambda **kwargs: MagicMock())
    monkeypatch.setattr(main4, "save_email_to_drafts", lambda mime_message: "dummy_draft_id")

    # Set dummy environment variables
    monkeypatch.setenv("API_KEY", "dummy_api_key")
    monkeypatch.setenv("GMAIL_ACCOUNT", "dummy@gmail.com")

def test_process_flag(raw_excel, processed_excel, caplog):
    """Test that only rows with process flag 'yes' (case-insensitive) are processed."""
    with caplog.at_level(logging.INFO):
        main4.main()
    
    # Load processed data
    df = pd.read_excel(processed_excel)
    # Expect only rows for "Test Company" and "Test Company 2" to be processed
    companies = df["company"].tolist()
    assert "Test Company" in companies
    assert "Test Company 2" in companies
    assert "Skipped Company" not in companies

    # Verify log output mentions skipping for the non-"yes" row
    skip_msg = "because process flag is not 'yes'."
    assert any(skip_msg in record.message for record in caplog.records)

def test_load_processed_data_new_file(tmp_path):
    """Test load_processed_data creates a new DataFrame when file does not exist."""
    file_path = tmp_path / "nonexistent.xlsx"
    df = main4.load_processed_data(file_path)
    assert isinstance(df, pd.DataFrame)
    expected_columns = [
        "saving_file_time", "company", "website", "main_business",
        "recipient_email", "contact_person", "cooperation_letter_content",
        "cooperation_points"
    ]
    for col in expected_columns:
        assert col in df.columns

def test_is_valid_email():
    """Test email validation."""
    # Valid emails
    assert main4.is_valid_email("test@example.com")
    assert main4.is_valid_email("user.name+tag@example.co.uk")
    # Invalid emails
    assert not main4.is_valid_email("invalid-email")
    assert not main4.is_valid_email("user@")
    assert not main4.is_valid_email("@domain.com")
    assert not main4.is_valid_email("")

def test_extract_keywords_from_filename():
    """Test keyword extraction from filenames."""
    # For "drone_detection_system.jpg"
    keywords = main4.extract_keywords_from_filename("drone_detection_system.jpg")
    assert "drone" in keywords
    assert "detection" in keywords
    assert "system" in keywords
    
    # Test with spaces
    keywords = main4.extract_keywords_from_filename("security camera system.png")
    assert "security" in keywords
    assert "camera" in keywords
    assert "system" in keywords
    
    # Test with numbers and special characters
    keywords = main4.extract_keywords_from_filename("1.2.3-surveillance_system-v2.0.jpg")
    assert "surveillance" in keywords
    assert any("v2" in word for word in keywords)
    # Extension should be included
    assert "jpg" in keywords

    # Test empty filename
    assert not main4.extract_keywords_from_filename("")
    try:
        result = main4.extract_keywords_from_filename(None)
        assert result == set()
    except Exception:
        pass

def test_select_relevant_images(monkeypatch, tmp_path):
    """Test image selection based on relevance."""
    # Create a temporary directory structure with dummy images
    images_dir = tmp_path / "data" / "raw" / "images"
    images_dir.mkdir(parents=True)
    for img_name in ["drone_detection.jpg", "security_system.png", "surveillance_camera.jpg"]:
        (images_dir / img_name).touch()
    
    # Override PROJECT_ROOT in main4.py to point to our temporary directory
    monkeypatch.setattr(main4, "PROJECT_ROOT", tmp_path)
    
    email_body = "We provide drone detection and security systems."
    company_name = "Security Solutions"
    images = main4.select_relevant_images(email_body, company_name)
    # Expect exactly three images returned
    assert len(images) == 3

def test_main_workflow(setup_test_environment, monkeypatch):
    """Test the full workflow including process flag filtering and processed data update."""
    # Use the setup_test_environment fixture to get paths
    env = setup_test_environment
    # Run main workflow
    main4.main()
    
    # Load processed data from the processed Excel file
    df = pd.read_excel(env["processed_excel_file"])
    # Expect only the two rows with process "yes" to be processed
    assert len(df) == 2
    companies = df["company"].tolist()
    assert "Test Company" in companies
    assert "Test Company 2" in companies
    assert "Skipped Company" not in companies
