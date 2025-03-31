# tests/data_access/test_website_scraper.py
import pytest
import requests
import requests_mock # Requires pip install requests-mock
from src.data_access.website_scraper import fetch_website_content

# Define constants for URLs and content used in tests
VALID_URL = "https://example.com"
VALID_HTTP_URL = "http://example.com"
NOT_FOUND_URL = "https://example.com/notfound"
TIMEOUT_URL = "https://example.com/timeout"
ERROR_URL = "https://example.com/error"
REDIRECT_URL = "https://example.com/redirect"
FINAL_REDIRECT_URL = "https://example.com/final"

HTML_CONTENT = """<!DOCTYPE html><html><head><title>Test Page</title></head>
<body><h1>Hello</h1><p>World</p></body></html>"""
SHORT_HTML_CONTENT = "<html><body>Hi</body></html>"

# --- Test Cases ---

@pytest.mark.parametrize("input_url, expected_url_base", [
    ("example.com", "https://example.com"),
    ("http://example.com", "http://example.com"),
    ("https://example.com", "https://example.com"),
])
def test_fetch_content_url_prefixing(input_url, expected_url_base, requests_mock):
    """Test that https:// is added correctly and existing schemes are kept."""
    # requests library often adds a trailing slash, mock with it included
    mock_url = expected_url_base.rstrip('/') + '/'
    requests_mock.get(mock_url, text=SHORT_HTML_CONTENT)
    fetch_website_content(input_url)
    assert requests_mock.called
    # FIX: Compare URLs ignoring potential trailing slash differences
    assert requests_mock.last_request.url.rstrip('/') == expected_url_base.rstrip('/')

def test_fetch_content_success(requests_mock):
    """Test successful content fetching."""
    requests_mock.get(VALID_URL, text=HTML_CONTENT)
    content = fetch_website_content(VALID_URL, max_content_length=500)
    assert content == HTML_CONTENT
    # Check that the default User-Agent is being sent
    assert requests_mock.last_request.headers['User-Agent'].startswith('Mozilla/5.0')

def test_fetch_content_truncation(requests_mock):
    """Test content truncation based on max_content_length."""
    requests_mock.get(VALID_URL, text=HTML_CONTENT)
    max_len = 20
    content = fetch_website_content(VALID_URL, max_content_length=max_len)
    assert content == HTML_CONTENT[:max_len]
    assert len(content) == max_len

def test_fetch_content_404_error(requests_mock):
    """Test handling of 404 Not Found error (should return None)."""
    requests_mock.get(NOT_FOUND_URL, status_code=404)
    content = fetch_website_content(NOT_FOUND_URL)
    # The function catches RequestException (incl HTTPError) and returns None
    assert content is None

def test_fetch_content_500_error(requests_mock): # Renamed test
    """Test handling of 500 Internal Server Error (should return None)."""
    requests_mock.get(ERROR_URL, status_code=500)
    content = fetch_website_content(ERROR_URL)
    # FIX: Assert None because raise_for_status() triggers RequestException handler
    assert content is None

# Note: Testing the *retry* logic itself with requests_mock can be complex
# as requests_mock replaces the adapter where urllib3's Retry operates.
# The above test confirms the function returns None on a 5xx error, which is
# the end result whether retries happened or not before failing.

def test_fetch_content_timeout(requests_mock):
    """Test handling of connection timeout (should return None)."""
    requests_mock.get(TIMEOUT_URL, exc=requests.exceptions.Timeout("Timeout occurred"))
    content = fetch_website_content(TIMEOUT_URL)
    assert content is None

def test_fetch_content_connection_error(requests_mock):
    """Test handling of generic connection error (should return None)."""
    requests_mock.get(ERROR_URL, exc=requests.exceptions.ConnectionError("Connection failed"))
    content = fetch_website_content(ERROR_URL)
    assert content is None

def test_fetch_content_too_many_redirects(requests_mock):
    """Test handling of too many redirects (should return None)."""
    # Simulate a redirect loop
    requests_mock.get(REDIRECT_URL, status_code=301, headers={'Location': REDIRECT_URL})
    content = fetch_website_content(REDIRECT_URL)
    # The underlying requests library should raise TooManyRedirects, caught by RequestException
    assert content is None

def test_fetch_content_successful_redirect(requests_mock):
    """Test following a redirect successfully."""
    requests_mock.get(REDIRECT_URL, status_code=301, headers={'Location': FINAL_REDIRECT_URL})
    requests_mock.get(FINAL_REDIRECT_URL, text=HTML_CONTENT)
    content = fetch_website_content(REDIRECT_URL)
    assert content == HTML_CONTENT
    # Check that both URLs were requested
    assert requests_mock.call_count == 2
    history = requests_mock.request_history
    assert history[0].url.rstrip('/') == REDIRECT_URL.rstrip('/')
    assert history[1].url.rstrip('/') == FINAL_REDIRECT_URL.rstrip('/')


@pytest.mark.parametrize("invalid_url", [
    None, "", 123, [], object() # Added object()
])
def test_fetch_content_invalid_url_input(invalid_url):
    """Test invalid URL inputs (should return None)."""
    content = fetch_website_content(invalid_url)
    assert content is None

def test_fetch_content_with_encoding(requests_mock):
    """Test content fetching with specified encoding."""
    # Simulate content that needs a specific encoding
    encoded_content = "Héllö Wörld".encode('latin-1')
    requests_mock.get(VALID_URL, content=encoded_content, headers={'Content-Type': 'text/html; charset=latin-1'})
    content = fetch_website_content(VALID_URL)
    assert content == "Héllö Wörld"

# Removed test_fetch_content_with_custom_headers as function doesn't support it
# Removed test_fetch_content_with_compression as mocking requires actual compressed data
# Removed test_fetch_content_with_robots_txt as function doesn't implement it

# Example test for rate limiting (similar to 500 error test)
def test_fetch_content_with_rate_limiting(requests_mock):
     """Test handling of 429 Rate Limit error (should return None after retries fail)."""
     requests_mock.get(ERROR_URL, status_code=429)
     content = fetch_website_content(ERROR_URL)
     # Retry logic in fetch_website_content should retry on 429, but eventually fail.
     # The exception handler catches RequestException (incl HTTPError) and returns None.
     assert content is None