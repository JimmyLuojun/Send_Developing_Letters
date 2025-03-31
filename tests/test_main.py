# tests/test_main.py

import pytest
from unittest.mock import patch, MagicMock
from src.main import run_process

@pytest.fixture(autouse=True)
def setup_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake_deepseek_key")
    monkeypatch.setenv("SENDER_EMAIL", "sender@example.com")
    monkeypatch.setenv("GMAIL_CREDENTIALS_PATH", str(tmp_path / "credentials.json"))
    monkeypatch.setenv("GMAIL_TOKEN_PATH", str(tmp_path / "token.json"))

    (tmp_path / "credentials.json").touch()
    (tmp_path / "token.json").touch()

    mock_project_root = tmp_path
    with patch("src.main.PROJECT_ROOT", mock_project_root):
        (mock_project_root / "config.ini").write_text("""
[PATHS]
skyfend_business_doc = skyfend.txt
company_data_excel = companies.xlsx
product_brochure_pdf = brochure.pdf
unified_images_dir = images
processed_data_excel = processed.xlsx

[EMAIL_DEFAULTS]
max_images_per_email = 2

[WEBSITE_SCRAPER]
max_content_length = 3000
timeout = 10

[API_CLIENT]
request_timeout = 20
""")

        (mock_project_root / "skyfend.txt").write_text("Skyfend business description")
        (mock_project_root / "companies.xlsx").touch()
        (mock_project_root / "brochure.pdf").touch()
        images_dir = mock_project_root / "images"
        images_dir.mkdir()
        (images_dir / "image1.jpg").touch()
        (images_dir / "image2.jpg").touch()

        yield

@patch("src.main.read_company_data")
@patch("src.main.read_skyfend_business")
@patch("src.main.fetch_website_content")
@patch("src.main.DeepSeekClient")
@patch("src.main.DeepSeekLetterGenerator")
@patch("src.main.select_relevant_images")
@patch("src.main.create_mime_email")
@patch("src.main.save_email_to_drafts")
@patch("src.main.save_processed_data")
def test_run_process(mock_save_processed, mock_save_drafts, mock_create_email, mock_select_images,
                     mock_letter_gen, mock_deepseek_client, mock_fetch_content,
                     mock_read_skyfend, mock_read_company):

    mock_read_skyfend.return_value = "Skyfend business description"

    # Define realistic company mocks
    test_co = MagicMock()
    test_co.company_name = "Test Co"
    test_co.recipient_email = "test@example.com"
    test_co.website = "http://test.com"
    test_co.should_process = True
    test_co.processing_status = None

    skipped_co = MagicMock()
    skipped_co.company_name = "Skipped Co"
    skipped_co.recipient_email = "skip@example.com"
    skipped_co.website = "http://skip.com"
    skipped_co.should_process = False
    skipped_co.processing_status = None

    invalid_email_co = MagicMock()
    invalid_email_co.company_name = "Invalid Email Co"
    invalid_email_co.recipient_email = "invalidemail"
    invalid_email_co.website = "http://invalid.com"
    invalid_email_co.should_process = True
    invalid_email_co.processing_status = None

    mock_read_company.return_value = [test_co, skipped_co, invalid_email_co]

    mock_fetch_content.return_value = "Test Co website content"
    mock_deepseek_client.return_value.extract_main_business.return_value = "Test Co Main Business"
    mock_deepseek_client.return_value.identify_cooperation_points.return_value = "Cooperation points"

    mock_letter_gen.return_value.generate.return_value.body_html = "Generated Letter HTML"
    mock_letter_gen.return_value.generate.return_value.subject = "Test Letter Subject"

    mock_select_images.return_value = ["image1.jpg", "image2.jpg"]

    mock_create_email.return_value = MagicMock()
    mock_save_drafts.return_value = "draft_id_123"

    run_process()

    assert mock_read_skyfend.call_count == 1
    assert mock_read_company.call_count == 1
    assert mock_fetch_content.call_count == 1  # Only one valid company processed
    mock_deepseek_client.return_value.extract_main_business.assert_called_once_with("Test Co website content")
    mock_deepseek_client.return_value.identify_cooperation_points.assert_called_once()
    mock_letter_gen.return_value.generate.assert_called_once()
    mock_select_images.assert_called_once()
    mock_create_email.assert_called_once()
    mock_save_drafts.assert_called_once()
    mock_save_processed.assert_called_once()

    processed_companies = mock_save_processed.call_args[0][0]
    assert len(processed_companies) == 1  # Only successfully processed companies recorded

    test_co.update_status.assert_called_with("Success: Draft ID draft_id_123")
    skipped_co.update_status.assert_called_with("Skipped: Process flag")
    invalid_email_co.update_status.assert_called_with("Skipped: Invalid email format")
