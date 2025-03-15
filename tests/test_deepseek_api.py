import pytest
from unittest.mock import patch, MagicMock
from src.models.deepseek_api import DeepSeekAPI, create_message
from openai import OpenAI, types

# Mock the OpenAI ChatCompletion response
@pytest.fixture
def mock_chat_completion():
    mock_response = MagicMock(spec=types.chat.ChatCompletion)
    mock_response.choices = [
        MagicMock(message=MagicMock(content="Paris is the capital."))
    ]
    return mock_response

# Correct the patching: patch the instance method, not the class method
@patch.object(DeepSeekAPI, 'get_completion') # Changed the patching
def test_get_completion_success(mock_get_completion, mock_chat_completion):
    # mock_create.return_value = mock_chat_completion # No need, use the return value
    mock_get_completion.return_value = "Paris is the capital." # Mock the return value
    deepseek = DeepSeekAPI(api_key="test_key")  # No need for a real key
    messages = [create_message("user", "What is the capital of France?")]
    result = deepseek.get_completion("deepseek-chat", messages)
    assert result == "Paris is the capital."
    mock_get_completion.assert_called_once_with("deepseek-chat", messages) # check the argument

@patch.object(DeepSeekAPI, 'get_completion', return_value=None) #Simplified
def test_get_completion_failure(mock_get_completion):
    deepseek = DeepSeekAPI(api_key="test_key")
    messages = [create_message("user", "What is the capital of France?")]
    result = deepseek.get_completion("deepseek-chat", messages)
    assert result is None
    mock_get_completion.assert_called_once()

def test_create_message():
    message = create_message("user", "Hello")
    assert message == {"role": "user", "content": "Hello"} 