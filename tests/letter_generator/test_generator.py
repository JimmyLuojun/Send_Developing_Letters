# tests/letter_generator/test_generator.py

import pytest
from unittest.mock import MagicMock, call
import logging # Import logging
from src.api_clients.deepseek_client import DeepSeekClient
from src.letter_generator.generator import DeepSeekLetterGenerator, _create_message # Import helper too if needed locally
from src.core import LetterGenerationInput, DevelopingLetter
# Assuming DeepSeekClient has _get_completion method, otherwise mock the public method called by generate
# from src.api_clients import DeepSeekClient # Only needed if typing the mock strictly

# --- Fixtures ---

@pytest.fixture
def mock_deepseek_client():
    """Provides a mock DeepSeekClient with a mockable _get_completion method."""
    mock_client = MagicMock(spec=DeepSeekClient) # Use spec if class is importable
    # Mock the specific method called by the generator's generate method
    mock_client._get_completion = MagicMock()
    return mock_client

@pytest.fixture
def letter_generator(mock_deepseek_client):
    """Provides an instance of DeepSeekLetterGenerator with a mocked client."""
    return DeepSeekLetterGenerator(deepseek_client=mock_deepseek_client)

@pytest.fixture
def sample_input_data():
    """Provides sample input data for letter generation."""
    return LetterGenerationInput(
        cooperation_points="Point 1: Integrate tech.\nPoint 2: Joint marketing.",
        target_company_name="TargetCorp",
        contact_person_name="Ms. Contact"
    )

# --- Test Cases ---

def test_generate_success_default_language(letter_generator, mock_deepseek_client, sample_input_data, caplog):
    """Test successful generation using default English language."""
    caplog.set_level(logging.INFO) # Capture info logs

    # Mock the API response for English
    mock_response = """Subject: Skyfend & TargetCorp: Exploring Synergy
---BODY_SEPARATOR---
<p>Dear Ms. Contact,</p>
<p>Introduction paragraph...</p>
[IMAGE1]
<p>Cooperation points paragraph...</p>
[IMAGE2]
<p>Further points or benefits...</p>
[IMAGE3]
<p>We have attached our product brochure for your reference...</p>
<p>Call to action paragraph...</p>
<p>Sincerely,<br>Jimmy<br>Overseas Sales Manager<br>Skyfend</p>
    """
    mock_deepseek_client._get_completion.return_value = mock_response

    # Call generate with target_language=None (should default to 'en')
    result = letter_generator.generate(input_data=sample_input_data, target_language=None, model="test-model")

    # Assertions
    assert isinstance(result, DevelopingLetter)
    assert result.subject == "Skyfend & TargetCorp: Exploring Synergy"
    assert "<p>Dear Ms. Contact,</p>" in result.body_html
    assert "[IMAGE1]" in result.body_html # Check placeholder presence
    assert "<br>Jimmy<br>" in result.body_html # Check sender name

    # Check that the prompt sent to the API was correct
    mock_deepseek_client._get_completion.assert_called_once()
    call_args, _ = mock_deepseek_client._get_completion.call_args
    # call_args[0] is model, call_args[1] is messages list
    assert call_args[0] == "test-model"
    messages = call_args[1]
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "language corresponding to the code: en" in messages[0]["content"] # Check default lang in system msg
    assert messages[1]["role"] == "user"
    user_prompt = messages[1]["content"]
    assert "Target Language for Output: en" in user_prompt # Check lang in user prompt
    assert "Jimmy, Overseas Sales Manager" in user_prompt # Check sender consistency
    assert "[IMAGE1]" in user_prompt # Check placeholder instruction in prompt

    assert f"Generating letter for TargetCorp in language 'en'..." in caplog.text


def test_generate_success_specific_language(letter_generator, mock_deepseek_client, sample_input_data, caplog):
    """Test successful generation using a specific language (e.g., German)."""
    caplog.set_level(logging.INFO)
    target_lang = 'de'

    # Mock the API response (pretend it's German)
    mock_response = f"""Subject: Skyfend & TargetCorp: Kooperationspotenzial
---BODY_SEPARATOR---
<p>Sehr geehrte Frau Contact,</p>
<p>Einleitung...</p>
[IMAGE1]
<p>Kooperationspunkte...</p>
[IMAGE2]
<p>Weitere Punkte...</p>
[IMAGE3]
<p>Anbei die Broschüre...</p>
<p>Handlungsaufforderung...</p>
<p>Mit freundlichen Grüßen,<br>Jimmy<br>Overseas Sales Manager<br>Skyfend</p>
    """
    mock_deepseek_client._get_completion.return_value = mock_response

    # Call generate with target_language='de'
    result = letter_generator.generate(input_data=sample_input_data, target_language=target_lang, model="test-model-de")

    # Assertions
    assert isinstance(result, DevelopingLetter)
    assert result.subject == "Skyfend & TargetCorp: Kooperationspotenzial" # German subject
    assert "<p>Sehr geehrte Frau Contact,</p>" in result.body_html # German body start
    assert "[IMAGE1]" in result.body_html

    # Check prompt sent to API
    mock_deepseek_client._get_completion.assert_called_once()
    call_args, _ = mock_deepseek_client._get_completion.call_args
    assert call_args[0] == "test-model-de"
    messages = call_args[1]
    assert "language corresponding to the code: de" in messages[0]["content"] # Check target lang in system msg
    user_prompt = messages[1]["content"]
    assert f"Target Language for Output: {target_lang}" in user_prompt # Check lang in user prompt
    assert f"Compose IN {target_lang.upper()}" in user_prompt
    assert f"Write IN {target_lang.upper()}" in user_prompt
    assert f"output (Subject and Body HTML) is in {target_lang.upper()}" in user_prompt

    assert f"Generating letter for TargetCorp in language '{target_lang}'..." in caplog.text

def test_generate_parsing_error(letter_generator, mock_deepseek_client, sample_input_data, caplog):
    """Test handling when API response lacks the separator."""
    caplog.set_level(logging.ERROR)
    # Mock response without the separator
    mock_deepseek_client._get_completion.return_value = "Subject: Test\nBody: Test Body"

    result = letter_generator.generate(input_data=sample_input_data, target_language='en')

    assert isinstance(result, DevelopingLetter)
    assert result.subject == f"Potential Cooperation with {sample_input_data.target_company_name}"
    assert "Error generating letter content" in result.body_html
    assert f"Failed to parse generated letter structure for {sample_input_data.target_company_name}" in caplog.text


def test_generate_api_error(letter_generator, mock_deepseek_client, sample_input_data, caplog):
    """Test handling when the API call itself raises an exception."""
    caplog.set_level(logging.ERROR)
    # Mock client method to raise an error
    mock_deepseek_client._get_completion.side_effect = Exception("API connection failed")

    result = letter_generator.generate(input_data=sample_input_data, target_language='en')

    assert isinstance(result, DevelopingLetter)
    assert result.subject == f"Potential Cooperation with {sample_input_data.target_company_name}"
    assert "Error generating letter content" in result.body_html
    assert f"Error during letter generation API call for {sample_input_data.target_company_name}" in caplog.text
    assert "API connection failed" in caplog.text


def test_generate_empty_completion(letter_generator, mock_deepseek_client, sample_input_data, caplog):
    """Test handling when the API returns None or empty completion."""
    caplog.set_level(logging.ERROR)
    mock_deepseek_client._get_completion.return_value = None

    result = letter_generator.generate(input_data=sample_input_data, target_language='en')

    assert isinstance(result, DevelopingLetter)
    assert result.subject == f"Potential Cooperation with {sample_input_data.target_company_name}"
    assert "Error generating letter content" in result.body_html
    # Check specific log for parsing failure because completion was None
    assert f"Failed to parse generated letter structure for {sample_input_data.target_company_name}" in caplog.text