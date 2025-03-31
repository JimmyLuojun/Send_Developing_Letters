# tests/api_clients/test_deepseek_client.py
import pytest
import time
import json
import logging
from typing import Optional, List, Dict
from unittest.mock import patch, MagicMock, call
import httpx

# Import specific errors and types
from openai import OpenAI, RateLimitError, Timeout, APIConnectionError, APIError, BadRequestError

# --- DIAGNOSTIC CHECK AT TOP (Keep this) ---
print("\n--- Type Checks START ---")
print(f"Type of Timeout imported: {type(Timeout)}")
print(f"Is Timeout subclass of BaseException? {issubclass(Timeout, BaseException)}")
print(f"Is APIError subclass of BaseException? {issubclass(APIError, BaseException)}")
print(f"Is RateLimitError subclass of BaseException? {issubclass(RateLimitError, BaseException)}")
print(f"Is APIConnectionError subclass of BaseException? {issubclass(APIConnectionError, BaseException)}")
print(f"Is BadRequestError subclass of BaseException? {issubclass(BadRequestError, BaseException)}")
print(f"Is ValueError subclass of BaseException? {issubclass(ValueError, BaseException)}")
print("--- Type Checks END ---\n")
# --- END DIAGNOSTIC CHECK ---

# (Keep the try/except block for openai types if needed)
try:
    from openai.types.chat import ChatCompletion, ChatCompletionMessage
    from openai.types.chat.chat_completion import Choice
    from openai.types.completion_usage import CompletionUsage
    OPENAI_TYPES_AVAILABLE = True
except ImportError:
    # ... (fallback mocks) ...
    OPENAI_TYPES_AVAILABLE = False
    ChatCompletion = MagicMock; ChatCompletionMessage = MagicMock; Choice = MagicMock; CompletionUsage = MagicMock

# Import the client to be tested and its helper
from src.api_clients.deepseek_client import DeepSeekClient, _create_message

# Constants (keep as before)
API_KEY = "test-dummy-api-key"
BASE_URL = DeepSeekClient.DEFAULT_BASE_URL
TEST_MODEL = "deepseek-chat"
TEST_MESSAGES = [{"role": "user", "content": "test prompt"}]
TEST_RESPONSE_CONTENT = "This is the test response content."

# --- Mock Helpers ---
# (Keep create_mock_request, create_mock_response, create_mock_completion, create_mock_completion_no_choices)
def create_mock_request(method: str = "POST", url: str = f"{BASE_URL}/chat/completions") -> MagicMock:
    # ... (implementation as before) ...
    mock_req = MagicMock(spec=httpx.Request); mock_req.method = method; mock_req.url = httpx.URL(url)
    mock_req.headers = httpx.Headers({'content-type': 'application/json'}); mock_req.content = json.dumps({"model": TEST_MODEL, "messages": TEST_MESSAGES}).encode('utf-8')
    return mock_req

def create_mock_response(status_code: int, headers: Optional[dict] = None, request: Optional[MagicMock] = None, json_body: Optional[dict] = None) -> MagicMock:
     # ... (implementation as before) ...
    mock_resp = MagicMock(spec=httpx.Response); mock_resp.status_code = status_code; mock_resp.headers = httpx.Headers(headers or {})
    mock_resp.request = request if request else create_mock_request(); error_body = json_body if json_body is not None else {"error": {"message": f"Mock error for status {status_code}", "type": "mock_error"}}
    mock_resp.json.return_value = error_body; mock_resp.text = json.dumps(error_body); mock_resp.content = mock_resp.text.encode('utf-8')
    mock_resp.iter_bytes.return_value = iter([]); mock_resp.iter_text.return_value = iter([]); mock_resp.read.return_value = b""; mock_resp.close = MagicMock()
    return mock_resp

def create_mock_completion(content: Optional[str] = TEST_RESPONSE_CONTENT, finish_reason: str = 'stop', model: str = TEST_MODEL) -> MagicMock:
    # ... (implementation as before) ...
    mock_completion = MagicMock(spec=ChatCompletion); mock_completion.id = f"chatcmpl-mockid-{int(time.time()*1000)}"; mock_completion.created = int(time.time())
    mock_completion.model = model; mock_completion.object = "chat.completion"
    if content is not None:
        mock_msg = MagicMock(spec=ChatCompletionMessage); mock_msg.role = 'assistant'; mock_msg.content = content; mock_msg.function_call = None; mock_msg.tool_calls = None
        mock_choice = MagicMock(spec=Choice); mock_choice.finish_reason = finish_reason; mock_choice.index = 0; mock_choice.message = mock_msg; mock_choice.logprobs = None
        mock_completion.choices = [mock_choice]; mock_usage = MagicMock(spec=CompletionUsage); prompt_tokens = sum(len(m["content"].split()) for m in TEST_MESSAGES if m.get("content"))
        completion_tokens = len(content.split()); mock_usage.prompt_tokens = prompt_tokens; mock_usage.completion_tokens = completion_tokens; mock_usage.total_tokens = prompt_tokens + completion_tokens
        mock_completion.usage = mock_usage
    else:
        mock_msg = MagicMock(spec=ChatCompletionMessage); mock_msg.role = 'assistant'; mock_msg.content = None; mock_msg.function_call = None; mock_msg.tool_calls = None
        mock_choice = MagicMock(spec=Choice); mock_choice.finish_reason = 'stop'; mock_choice.index = 0; mock_choice.message = mock_msg; mock_choice.logprobs = None
        mock_completion.choices = [mock_choice]; mock_usage = MagicMock(spec=CompletionUsage); prompt_tokens = sum(len(m["content"].split()) for m in TEST_MESSAGES if m.get("content"))
        mock_usage.prompt_tokens = prompt_tokens; mock_usage.completion_tokens = 0; mock_usage.total_tokens = prompt_tokens; mock_completion.usage = mock_usage
    mock_completion.system_fingerprint = "mock_fingerprint"
    return mock_completion

def create_mock_completion_no_choices() -> MagicMock:
     # ... (implementation as before) ...
    mock_completion = MagicMock(spec=ChatCompletion); mock_completion.id = f"chatcmpl-mockid-nochoice-{int(time.time()*1000)}"; mock_completion.created = int(time.time())
    mock_completion.model=TEST_MODEL; mock_completion.object = "chat.completion"; mock_completion.choices = []
    mock_usage = MagicMock(spec=CompletionUsage); prompt_tokens = sum(len(m["content"].split()) for m in TEST_MESSAGES if m.get("content"))
    mock_usage.prompt_tokens = prompt_tokens; mock_usage.completion_tokens = 0; mock_usage.total_tokens = prompt_tokens; mock_completion.usage = mock_usage
    mock_completion.system_fingerprint = "mock_fingerprint_nochoice"
    return mock_completion


# --- HELPER FUNCTION for side_effect (Keep diagnostics) ---
def raise_exception(exc):
    """Returns a function that raises the given exception when called."""
    log_msg = f"[raise_exception] Attempting to raise: type={type(exc)}, object={exc!r}, isinstance(BaseException)={isinstance(exc, BaseException)}"
    print(log_msg) # Print for visibility with -s
    logging.info(log_msg)
    def raiser(*args, **kwargs):
        print(f"[raiser] Executing raise for: {exc!r}") # Add print
        logging.info(f"[raiser] Executing raise for: {exc!r}")
        raise exc # This was the line causing internal TypeError
    return raiser

# --- Test Cases ---

# Initialization Tests (These don't need mocking changes)
# (Keep test_client_init_success, test_client_init_requires_api_key, test_client_init_custom_params)
def test_client_init_success():
    with patch('src.api_clients.deepseek_client.OpenAI') as mock_openai_constructor:
        mock_instance = MagicMock(spec=OpenAI); mock_openai_constructor.return_value = mock_instance
        client = DeepSeekClient(api_key=API_KEY); assert client.client == mock_instance
        mock_openai_constructor.assert_called_once_with(api_key=API_KEY, base_url=DeepSeekClient.DEFAULT_BASE_URL, timeout=DeepSeekClient.DEFAULT_REQUEST_TIMEOUT, max_retries=0)
def test_client_init_requires_api_key():
    with pytest.raises(ValueError, match="API key is required"): DeepSeekClient(api_key="")
    with pytest.raises(ValueError, match="API key is required"): DeepSeekClient(api_key=None)
def test_client_init_custom_params():
    custom_url = "http://localhost:8080"; custom_timeout = 60
    with patch('src.api_clients.deepseek_client.OpenAI') as mock_openai_constructor:
        client = DeepSeekClient(api_key=API_KEY, base_url=custom_url, request_timeout=custom_timeout)
        mock_openai_constructor.assert_called_once_with(api_key=API_KEY, base_url=custom_url, timeout=custom_timeout, max_retries=0)

# Helper Function Test (No mocking needed)
# (Keep test_create_message_helper)
def test_create_message_helper():
    assert _create_message("user", "hello") == {"role": "user", "content": "hello"}
    assert _create_message("system", "system prompt") == {"role": "system", "content": "system prompt"}
    assert _create_message("assistant", "hi") == {"role": "assistant", "content": "hi"}
    assert _create_message("invalid_role", "test") == {"role": "user", "content": "test"}


# _get_completion Success Test (Patching inside test)
def test_get_completion_success():
    """Test _get_completion successful retrieval."""
    client = DeepSeekClient(api_key=API_KEY)
    mock_response = create_mock_completion(TEST_RESPONSE_CONTENT)
    # Patch the instance method
    with patch.object(client.client.chat.completions, 'create', return_value=mock_response) as mock_create_method:
        result = client._get_completion(TEST_MODEL, TEST_MESSAGES)
        mock_create_method.assert_called_once_with(model=TEST_MODEL, messages=TEST_MESSAGES, stream=False)
        assert result == TEST_RESPONSE_CONTENT

# _get_completion Invalid Response Test (Patching inside test)
def test_get_completion_invalid_response_structure():
    """Test _get_completion handling of various invalid response structures."""
    client = DeepSeekClient(api_key=API_KEY)
    mock_response_no_choices = create_mock_completion_no_choices()
    mock_response_no_content = create_mock_completion(content=None)
    mock_response_empty_object = MagicMock(spec=ChatCompletion); mock_response_empty_object.choices = []
    side_effects = [None, mock_response_empty_object, mock_response_no_choices, mock_response_no_content]
    # Patch the instance method with multiple side effects
    with patch.object(client.client.chat.completions, 'create', side_effect=side_effects) as mock_create_method:
        assert client._get_completion(TEST_MODEL, TEST_MESSAGES, max_retries=0) is None
        assert client._get_completion(TEST_MODEL, TEST_MESSAGES, max_retries=0) is None
        assert client._get_completion(TEST_MODEL, TEST_MESSAGES, max_retries=0) is None
        assert client._get_completion(TEST_MODEL, TEST_MESSAGES, max_retries=0) is None
        assert mock_create_method.call_count == 4


# _get_completion Error/Retry Tests (Patching inside test)
@patch('time.sleep', return_value=None, autospec=True)
def test_get_completion_rate_limit_retry_success(mock_sleep): # Removed fixture arg
    """Test _get_completion successful retry after RateLimitError."""
    client = DeepSeekClient(api_key=API_KEY)
    mock_response_success = create_mock_completion(TEST_RESPONSE_CONTENT)
    mock_err_response = create_mock_response(status_code=429, headers={'Retry-After': '5'})
    rate_limit_error = RateLimitError(message="Rate limited", response=mock_err_response, body={"error": {"code": "rate_limit_exceeded"}})
    # Patch instance method with sequence of side effects
    with patch.object(client.client.chat.completions, 'create', side_effect=[rate_limit_error, mock_response_success]) as mock_create_method:
        result = client._get_completion(TEST_MODEL, TEST_MESSAGES, max_retries=1, initial_delay=0.01)
        assert mock_create_method.call_count == 2
        mock_sleep.assert_called_once_with(0.01)
        assert result == TEST_RESPONSE_CONTENT

@patch('time.sleep', return_value=None, autospec=True)
def test_get_completion_retry_failure_after_max_retries(mock_sleep):
    """Test _get_completion failure after exhausting retries (Timeout)."""
    client = DeepSeekClient(api_key=API_KEY)
    timeout_error = httpx.ReadTimeout("Request timed out")

    with patch.object(client.client.chat.completions, 'create', side_effect=raise_exception(timeout_error)) as mock_create_method:
        result = client._get_completion(TEST_MODEL, TEST_MESSAGES, max_retries=1, initial_delay=0.01)
        assert mock_create_method.call_count == 2  # Initial call + 1 retry
        mock_sleep.assert_called_once_with(0.01)
        assert result is None

@patch('time.sleep', return_value=None, autospec=True)
def test_get_completion_bad_request_no_retry(mock_sleep):
    """Test _get_completion does not retry on BadRequestError (400)."""
    client = DeepSeekClient(api_key=API_KEY)
    # Create a mock response with a non-None request attribute.
    mock_error_response = MagicMock()
    mock_error_response.request = MagicMock()  # Ensure request is not None.
    bad_request_error = BadRequestError(
        message="Invalid request parameters",
        response=mock_error_response,
        body={"error": {"code": "invalid_request"}}
    )
    with patch.object(client.client.chat.completions, 'create', side_effect=raise_exception(bad_request_error)) as mock_create_method:
        result = client._get_completion(TEST_MODEL, TEST_MESSAGES, max_retries=2)
        # For non-retriable error, only one call should be made.
        assert result is None
        assert mock_create_method.call_count == 1
        mock_sleep.assert_not_called()

@patch('time.sleep', return_value=None, autospec=True)
def test_get_completion_server_error_500_retries(mock_sleep): # Removed fixture arg
    """Test _get_completion retries on a 500 Internal Server Error."""
    client = DeepSeekClient(api_key=API_KEY)
    mock_request = create_mock_request(); mock_error_response = create_mock_response(status_code=500, request=mock_request)
    api_error_instance = APIError(message="Internal Server Error", request=mock_request, body={"error": {"code": "server_error"}})
    api_error_instance.status_code = 500; api_error_instance.response = mock_error_response
    # Patch instance method using the raise_exception helper
    with patch.object(client.client.chat.completions, 'create', side_effect=raise_exception(api_error_instance)) as mock_create_method:
        result = client._get_completion(TEST_MODEL, TEST_MESSAGES, max_retries=1, initial_delay=0.01)
        assert result is None
        assert mock_create_method.call_count == 2 # Expect 2 calls
        mock_sleep.assert_called_once_with(0.01)

@patch('time.sleep', return_value=None, autospec=True)
def test_get_completion_connection_error_retries(mock_sleep):
    """Test _get_completion retries on APIConnectionError."""
    client = DeepSeekClient(api_key=API_KEY)
    # Create a retriable APIConnectionError.
    connection_error = APIConnectionError(message="Could not connect", request=None)
    with patch.object(client.client.chat.completions, 'create', side_effect=raise_exception(connection_error)) as mock_create_method:
        result = client._get_completion(TEST_MODEL, TEST_MESSAGES, max_retries=1, initial_delay=0.01)
        # For retriable errors, _get_completion should retry (1 initial + 1 retry).
        assert result is None
        assert mock_create_method.call_count == 2
        mock_sleep.assert_called_once_with(0.01)

@patch('time.sleep', return_value=None, autospec=True)
def test_get_completion_unexpected_error_no_retry(mock_sleep):
    """Test _get_completion does not retry on unexpected generic exceptions."""
    client = DeepSeekClient(api_key=API_KEY)
    unexpected_error = ValueError("Unexpected value")
    with patch.object(client.client.chat.completions, 'create', side_effect=raise_exception(unexpected_error)) as mock_create_method:
        result = client._get_completion(TEST_MODEL, TEST_MESSAGES, max_retries=2)
        # For non-retriable unexpected errors, it should return immediately.
        assert result is None
        assert mock_create_method.call_count == 1
        mock_sleep.assert_not_called()


# Public Method Tests (Patching inside test)
def test_extract_main_business_success(): # Removed fixture arg
    """Test successful extraction of main business."""
    client = DeepSeekClient(api_key=API_KEY)
    website_content = "..." # Keep content
    expected_business = "..." # Keep expected
    mock_response = create_mock_completion(expected_business)
    # Patch the instance method
    with patch.object(client.client.chat.completions, 'create', return_value=mock_response) as mock_create_method:
        result = client.extract_main_business(website_content)
        assert result == expected_business
        mock_create_method.assert_called_once() # Check the actual mock
        # (Keep other assertions about args/kwargs if needed)

@patch('time.sleep', return_value=None, autospec=True)
def test_extract_main_business_api_failure(mock_sleep):
    """Test extract_main_business returns None when _get_completion fails."""
    client = DeepSeekClient(api_key=API_KEY)
    timeout_error = httpx.ReadTimeout("API timed out")
    with patch.object(client.client.chat.completions, 'create', side_effect=raise_exception(timeout_error)) as mock_create_method:
        result = client.extract_main_business("Some content", model="deepseek-chat")
        # Since timeout is retriable, _get_completion will retry (DEFAULT_MAX_RETRIES + 1 calls).
        assert result is None
        assert mock_create_method.call_count == client.DEFAULT_MAX_RETRIES + 1
        assert mock_sleep.call_count == client.DEFAULT_MAX_RETRIES

def test_extract_main_business_empty_content(): # Removed fixture arg, but no mocking needed
    """Test extract_main_business handles empty or invalid input."""
    client = DeepSeekClient(api_key=API_KEY)
    # No need to patch here as the API call shouldn't happen
    assert client.extract_main_business("") is None
    assert client.extract_main_business("   ") is None
    assert client.extract_main_business(None) is None
    # We can assert the mocked method wasn't called if we patch it,
    # but it's simpler to just know it shouldn't be called.

def test_identify_cooperation_points_success(): # Removed fixture arg
    """Test successful identification of cooperation points."""
    client = DeepSeekClient(api_key=API_KEY)
    sky_desc = "..." # Keep desc
    target_desc = "..." # Keep desc
    expected_points = "..." # Keep points
    mock_response = create_mock_completion(expected_points)
    # Patch the instance method
    with patch.object(client.client.chat.completions, 'create', return_value=mock_response) as mock_create_method:
        result = client.identify_cooperation_points(sky_desc, target_desc, company_a_name="Skyfend Test")
        assert result == expected_points
        mock_create_method.assert_called_once() # Check the actual mock
        # (Keep other assertions about args/kwargs if needed)

@patch('time.sleep', return_value=None, autospec=True)
def test_identify_cooperation_points_api_fail_returns_default_message(mock_sleep):
    """Test identify_cooperation_points returns default message on API failure."""
    client = DeepSeekClient(api_key=API_KEY)
    timeout_error = httpx.ReadTimeout("API timed out")
    with patch.object(client.client.chat.completions, 'create', side_effect=raise_exception(timeout_error)) as mock_create_method:
        result = client.identify_cooperation_points("Company A desc", "Company B desc")
        assert result == "No cooperation points identified"
        assert mock_create_method.call_count == client.DEFAULT_MAX_RETRIES + 1
        assert mock_sleep.call_count == client.DEFAULT_MAX_RETRIES

def test_identify_cooperation_points_api_returns_none_found(): # Removed fixture arg
    """Test identify_cooperation_points returns default message when API explicitly finds none."""
    client = DeepSeekClient(api_key=API_KEY)
    api_none_found_text = "Based on the descriptions provided, no specific cooperation points were identified."
    mock_response = create_mock_completion(api_none_found_text)
    # Patch the instance method
    with patch.object(client.client.chat.completions, 'create', return_value=mock_response) as mock_create_method:
        result = client.identify_cooperation_points("Company A desc", "Company B desc")
        assert result == "No cooperation points identified"
        mock_create_method.assert_called_once()

def test_identify_cooperation_points_empty_desc(): # Removed fixture arg, no mocking needed
    """Test identify_cooperation_points handles empty or invalid input descriptions."""
    client = DeepSeekClient(api_key=API_KEY)
    # No need to patch here
    assert client.identify_cooperation_points("", "target") is None
    assert client.identify_cooperation_points("sky", "") is None
    # (Keep other empty/invalid checks)