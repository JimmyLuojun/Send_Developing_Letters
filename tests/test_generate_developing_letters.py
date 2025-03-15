import pytest
from unittest.mock import patch, MagicMock
from openai import OpenAI, types
from src.utils.generate_developing_letters import generate_developing_letter

# Mock the OpenAI ChatCompletion response
@pytest.fixture
def mock_chat_completion_letter():
    mock_response = MagicMock(spec=types.chat.ChatCompletion)
    mock_response.choices = [
        MagicMock(message=MagicMock(content="<p>Dear Mr. Smith,</p>..."))
    ]
    return mock_response

@patch('src.utils.generate_developing_letters.OpenAI')
def test_generate_developing_letter_success(mock_openai, mock_chat_completion_letter):
    mock_openai_instance = MagicMock()
    mock_openai.return_value = mock_openai_instance
    mock_openai_instance.chat.completions.create.return_value = mock_chat_completion_letter

    api_key = "dummy_key"
    instructions = "Generate a letter."
    cooperation_points = "1. Joint Marketing"
    company_name = "Example Corp"
    contact_person = "Mr. Smith"

    result = generate_developing_letter(api_key, instructions, cooperation_points, company_name, contact_person)
    assert result == "<p>Dear Mr. Smith,</p>..."
    mock_openai_instance.chat.completions.create.assert_called_once()

@patch('src.utils.generate_developing_letters.OpenAI')
def test_generate_developing_letter_failure(mock_openai):
    mock_openai_instance = MagicMock()
    mock_openai.return_value = mock_openai_instance
    mock_openai_instance.chat.completions.create.side_effect = Exception("API Error")

    api_key = "dummy_key"
    result = generate_developing_letter(api_key, "instructions", "points", "company", "person")
    assert result == 'No letter content generated'
    mock_openai_instance.chat.completions.create.assert_called_once()

@patch('src.utils.generate_developing_letters.OpenAI')
def test_generate_developing_letter_no_contact_person(mock_openai, mock_chat_completion_letter):
    mock_openai_instance = MagicMock()
    mock_openai.return_value = mock_openai_instance
    mock_openai_instance.chat.completions.create.return_value = mock_chat_completion_letter

    api_key = "dummy_key"
    instructions = "Generate a letter."
    cooperation_points = "1. Joint Marketing"
    company_name = "Example Corp"
    contact_person = ""
    result = generate_developing_letter(api_key, instructions, cooperation_points, company_name, contact_person)
    assert result == "<p>Dear Mr. Smith,</p>..."
    mock_openai_instance.chat.completions.create.assert_called_once() 