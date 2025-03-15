# tests/test_business_extraction.py
import pytest
from unittest.mock import patch, MagicMock
from src.models.business_extraction import extract_main_business
from src.models.deepseek_api import DeepSeekAPI  # Import DeepSeekAPI

@patch.object(DeepSeekAPI, 'get_completion')
def test_extract_main_business_success(mock_get_completion):
    # Mock the get_completion method of DeepSeekAPI
    mock_get_completion.return_value = "Skyfend specializes in drone detection."

    # Call the function with dummy data
    api_key = "dummy_key"
    website_content = "Some website content about drones."
    result = extract_main_business(api_key, website_content)

    # Assert that the result is as expected
    assert result == "Skyfend specializes in drone detection."
    mock_get_completion.assert_called_once()


@patch.object(DeepSeekAPI, 'get_completion', return_value=None)
def test_extract_main_business_failure(mock_get_completion):
    # Mock get_completion to simulate an API failure.
    api_key = "dummy_key"
    website_content = "Some website content."
    result = extract_main_business(api_key, website_content)
    assert result is None
    mock_get_completion.assert_called_once()