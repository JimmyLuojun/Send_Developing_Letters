# tests/test_main1.py

import pytest
from unittest.mock import MagicMock, patch, ANY
from pathlib import Path
import configparser
from src import main1
from src.core import TargetCompanyData, DevelopingLetter, LetterGenerationInput

@pytest.fixture
def mock_config():
    config = configparser.ConfigParser()
    config['PATHS'] = {
        'skyfend_business_doc': 'mock_skyfend.docx',
        'company_data_excel': 'mock_companies.xlsx',
        'processed_data_excel': 'mock_processed.xlsx',
        'product_brochure_pdf': 'mock_brochure.pdf',
        'unified_images_dir': 'mock_images',
    }
    config['EMAIL'] = {
        'credentials_json_path': 'mock_credentials.json',
        'token_json_path': 'mock_token.json',
        'sender_email': 'sender@example.com',
    }
    config['API'] = {
        'deepseek_api_key': 'mock_api_key',
    }
    config['EMAIL_DEFAULTS'] = {
        'max_images_per_email': '3',
    }
    config['WEBSITE_SCRAPER'] = {
        'max_content_length': '3000',
        'timeout': '20',
    }
    config['API_CLIENT'] = {
        'request_timeout': '45',
    }
    config['LANGUAGE_SETTINGS'] = {
        'default_language': 'en'
    }
    return config

@pytest.fixture(autouse=True)
def mocks(mocker, mock_config):
    mocker.patch('src.main1.load_configuration', return_value=mock_config)
    mocker.patch('src.main1.load_dotenv', return_value=True)
    mocker.patch('src.main1.setup_logging')
    mocker.patch('src.main1.read_skyfend_business', return_value="Skyfend Description")
    mocker.patch('src.main1.read_company_data', return_value=[])
    mocker.patch('src.main1.pd.read_excel', return_value=MagicMock(columns=['recipient_email']))
    mocker.patch('src.main1.save_processed_data')
    mocker.patch('src.main1.create_mime_email')
    mocker.patch('src.main1.save_email_to_drafts', return_value="draft_id_mock")
    mocker.patch('src.main1.select_relevant_images', return_value=[Path("img1"), Path("img2"), Path("img3")])
    mocker.patch('src.main1.DeepSeekClient')
    mocker.patch('src.main1.DeepSeekLetterGenerator.generate', return_value=DevelopingLetter(subject="Subject", body_html="HTML body"))
    mocker.patch('src.main1.fetch_website_content', return_value="Website content")
    mocker.patch('src.main1.determine_language', return_value="en")
    mocker.patch('pathlib.Path.is_file', return_value=True)

@pytest.fixture
def mock_target_company():
    mock_company = MagicMock(spec=TargetCompanyData)
    mock_company.company_name = "TestCorp"
    mock_company.recipient_email = "test@example.com"
    mock_company.website = "http://example.com"
    mock_company.should_process = True
    mock_company.contact_person = "John Doe"
    mock_company.target_language = None
    mock_company.processing_status = None

    def update_status_side_effect(status):
        mock_company.processing_status = status

    mock_company.update_status = MagicMock(side_effect=update_status_side_effect)
    mock_company.set_letter_content = MagicMock()
    mock_company.set_draft_id = MagicMock()
    return mock_company

def test_main1_manual_language_override(mocker, mock_target_company):
    mock_target_company.target_language = 'de'
    mocker.patch('src.main1.read_company_data', return_value=[mock_target_company])
    generate_mock = mocker.patch('src.main1.DeepSeekLetterGenerator.generate')
    main1.run_process()
    generate_mock.assert_called_once()
    _, kwargs = generate_mock.call_args
    assert kwargs['target_language'] == 'de'
    mock_target_company.update_status.assert_called_with("Success: Draft ID draft_id_mock")

def test_main1_detect_language_success(mocker, mock_target_company):
    mock_target_company.target_language = None
    mocker.patch('src.main1.read_company_data', return_value=[mock_target_company])
    determine_language_mock = mocker.patch('src.main1.determine_language', return_value='fr')
    generate_mock = mocker.patch('src.main1.DeepSeekLetterGenerator.generate')
    main1.run_process()
    determine_language_mock.assert_called_once()
    generate_mock.assert_called_once()
    _, kwargs = generate_mock.call_args
    assert kwargs['target_language'] == 'fr'
    mock_target_company.update_status.assert_called_with("Success: Draft ID draft_id_mock")

def test_main1_website_fetch_fail_stops_processing(mocker, mock_target_company):
    mock_target_company.target_language = None
    mocker.patch('src.main1.read_company_data', return_value=[mock_target_company])
    fetch_mock = mocker.patch('src.main1.fetch_website_content', return_value=None)
    determine_language_mock = mocker.patch('src.main1.determine_language')
    main1.run_process()
    fetch_mock.assert_called_once()
    determine_language_mock.assert_not_called()
    mock_target_company.update_status.assert_called_with("Error: ValueError")
