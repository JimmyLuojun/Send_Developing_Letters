# tests/letter_generator/test_generator.py
import pytest
import logging
from unittest.mock import MagicMock, patch

# Import necessary components from your project
# Assuming 'src' layout managed by Poetry
from src.core import LetterGenerationInput as CoreLetterGenerationInput # Original definition
from src.core import DevelopingLetter
from src.letter_generator.generator import DeepSeekLetterGenerator
# We need a concrete implementation or mock for DeepSeekClient
# If DeepSeekClient is defined in your project:
# from src.api_clients import DeepSeekClient
# If it's just an interface/external, we can mock it entirely.

# --- Test Fixtures ---

# Create a simple concrete data class for testing based on LetterGenerationInput usage
@pytest.fixture
def sample_input_data() -> CoreLetterGenerationInput:
    # Using a simple dictionary-like object or a basic class instance
    # suffices if CoreLetterGenerationInput isn't directly instantiable.
    class TestInputData:
        cooperation_points: str = "1. Joint product bundles.\n2. Cross-promotion."
        target_company_name: str = "Innovate Corp"
        contact_person_name: str = "Dr. Evelyn Reed"
    return TestInputData()


@pytest.fixture
def mock_deepseek_client() -> MagicMock:
    """Provides a MagicMock instance simulating DeepSeekClient."""
    client = MagicMock()
    # Define spec if DeepSeekClient class is available and has type hints
    # client = MagicMock(spec=DeepSeekClient)
    client._get_completion = MagicMock() # Ensure the method exists on the mock
    return client


@pytest.fixture
def generator(mock_deepseek_client) -> DeepSeekLetterGenerator:
    """Provides an instance of DeepSeekLetterGenerator with a mocked client."""
    return DeepSeekLetterGenerator(deepseek_client=mock_deepseek_client)

# --- Test Cases ---

def test_generator_initialization(mock_deepseek_client):
    """Test if the generator initializes correctly with the client."""
    generator_instance = DeepSeekLetterGenerator(deepseek_client=mock_deepseek_client)
    assert generator_instance.client == mock_deepseek_client

def test_generate_success(generator, mock_deepseek_client, sample_input_data):
    """Test successful letter generation and parsing."""
    expected_subject = "Collaboration Opportunity: Skyfend & Innovate Corp"
    expected_body_html = "<p>Dear Dr. Evelyn Reed,</p><p>Introduction...</p><p>Cooperation points: Joint product bundles, Cross-promotion...</p><p>Call to action...</p><p>Attached is our brochure.</p><p>Sincerely,<br>Luo Jun<br>Business Development Manager<br>Skyfend</p>"
    mock_completion = f"Subject: {expected_subject}\n---BODY_SEPARATOR---\n{expected_body_html}"

    # Configure the mock client's method to return the successful completion
    mock_deepseek_client._get_completion.return_value = mock_completion

    # Call the method under test
    result_letter = generator.generate(sample_input_data)

    # Assertions
    assert isinstance(result_letter, DevelopingLetter)
    assert result_letter.subject == expected_subject
    assert result_letter.body_html == expected_body_html

    # Verify the mock client was called correctly
    mock_deepseek_client._get_completion.assert_called_once()
    call_args, call_kwargs = mock_deepseek_client._get_completion.call_args
    # Check model used (default)
    assert call_args[0] == "deepseek-chat"
    # Check messages structure (basic check)
    messages = call_args[1]
    assert isinstance(messages, list)
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    # Check if key info is in the prompt
    assert sample_input_data.target_company_name in messages[1]["content"]
    assert sample_input_data.contact_person_name in messages[1]["content"]
    assert sample_input_data.cooperation_points in messages[1]["content"]
    assert "---BODY_SEPARATOR---" in messages[1]["content"] # Ensure separator is requested


def test_generate_parsing_failure_no_separator(generator, mock_deepseek_client, sample_input_data, caplog):
    """Test generation failure when the separator is missing."""
    mock_completion = "Subject: Some Subject Body: Some Body Without Separator"
    mock_deepseek_client._get_completion.return_value = mock_completion

    default_subject = f"Potential Cooperation with {sample_input_data.target_company_name}"
    default_body = "<p>Error generating letter content.</p>"

    with caplog.at_level(logging.ERROR):
        result_letter = generator.generate(sample_input_data)

    # Assertions
    assert isinstance(result_letter, DevelopingLetter)
    assert result_letter.subject == default_subject
    assert result_letter.body_html == default_body
    assert f"Failed to parse generated letter structure for {sample_input_data.target_company_name}" in caplog.text
    assert f"Completion: {mock_completion}" in caplog.text # Check completion is logged

    mock_deepseek_client._get_completion.assert_called_once()


def test_generate_parsing_failure_empty_completion(generator, mock_deepseek_client, sample_input_data, caplog):
    """Test generation failure with empty or None completion."""
    completions_to_test = [None, ""]
    default_subject = f"Potential Cooperation with {sample_input_data.target_company_name}"
    default_body = "<p>Error generating letter content.</p>"

    for mock_completion in completions_to_test:
        mock_deepseek_client.reset_mock() # Reset mock for the next iteration
        caplog.clear() # Clear logs for the next iteration
        mock_deepseek_client._get_completion.return_value = mock_completion

        with caplog.at_level(logging.ERROR):
            result_letter = generator.generate(sample_input_data)

        # Assertions
        assert isinstance(result_letter, DevelopingLetter)
        assert result_letter.subject == default_subject
        assert result_letter.body_html == default_body
        assert f"Failed to parse generated letter structure for {sample_input_data.target_company_name}" in caplog.text

        mock_deepseek_client._get_completion.assert_called_once()


def test_generate_api_call_exception(generator, mock_deepseek_client, sample_input_data, caplog):
    """Test generation failure when the API client raises an exception."""
    api_error_message = "API connection timed out"
    mock_deepseek_client._get_completion.side_effect = Exception(api_error_message)

    default_subject = f"Potential Cooperation with {sample_input_data.target_company_name}"
    default_body = "<p>Error generating letter content.</p>"

    with caplog.at_level(logging.ERROR):
        result_letter = generator.generate(sample_input_data)

    # Assertions
    assert isinstance(result_letter, DevelopingLetter)
    assert result_letter.subject == default_subject
    assert result_letter.body_html == default_body
    assert f"Error during letter generation API call for {sample_input_data.target_company_name}" in caplog.text
    assert api_error_message in caplog.text # Check if the exception message is logged

    mock_deepseek_client._get_completion.assert_called_once()

def test_generate_uses_specified_model(generator, mock_deepseek_client, sample_input_data):
    """Test that the specified model parameter is used in the API call."""
    custom_model = "deepseek-coder" # Example custom model
    mock_deepseek_client._get_completion.return_value = "Subject: S\n---BODY_SEPARATOR---\n<p>B</p>" # Minimal valid response

    generator.generate(sample_input_data, model=custom_model)

    # Verify the mock client was called with the custom model
    mock_deepseek_client._get_completion.assert_called_once()
    call_args, call_kwargs = mock_deepseek_client._get_completion.call_args
    assert call_args[0] == custom_model # Check the first argument was the custom model 