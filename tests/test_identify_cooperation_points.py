import pytest
from unittest.mock import patch
from src.models.identify_cooperation_points import identify_cooperation_points
from src.models.deepseek_api import DeepSeekAPI

@patch.object(DeepSeekAPI, 'get_completion')
def test_identify_cooperation_points_success(mock_get_completion):
    mock_get_completion.return_value = "1. Joint Marketing\n2. Tech Integration"
    api_key = "dummy_key"
    skyfend_business = "Drone detection."
    target_business = "Drone manufacturing."
    result = identify_cooperation_points(api_key, skyfend_business, target_business)
    assert result == "1. Joint Marketing\n2. Tech Integration"
    mock_get_completion.assert_called_once()

@patch.object(DeepSeekAPI, 'get_completion', return_value=None)
def test_identify_cooperation_points_failure(mock_get_completion):
    api_key = "dummy_key"
    result = identify_cooperation_points(api_key, "skyfend", "target")
    assert result == "No cooperation points identified"
    mock_get_completion.assert_called_once()
