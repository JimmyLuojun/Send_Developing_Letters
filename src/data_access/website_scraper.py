# src/data_access/website_scraper.py
"""Module for fetching website content."""
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional

def fetch_website_content(url: str, max_content_length: int = 2000, timeout: int = 15) -> Optional[str]:
    """
    Fetches content from a given URL with retries and timeout.

    Args:
        url: The URL to fetch.
        max_content_length: Maximum number of characters to return.
        timeout: Request timeout in seconds.

    Returns:
        The website content as a string (truncated), or None on error.
    """
    if not url or not isinstance(url, str):
        logging.error(f"Invalid URL provided for scraping: {url}")
        return None

    # Ensure URL has a scheme
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
        logging.debug(f"Prepended 'https://' to URL: {url}")

    session = requests.Session()
    # Configure retries for common transient errors
    retries = Retry(
        total=3,
        backoff_factor=0.5, # Shorter backoff
        status_forcelist=[429, 500, 502, 503, 504], # Retry on these statuses
        allowed_methods=["GET"] # Only retry GET requests
    )
    session.mount('https://', HTTPAdapter(max_retries=retries))
    session.mount('http://', HTTPAdapter(max_retries=retries)) # Also handle http

    # Use a common browser user-agent
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

    try:
        logging.info(f"Attempting to fetch content from: {url}")
        response = session.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        # Decode content carefully, trying common encodings
        content = None
        try:
            content = response.content.decode(response.encoding or 'utf-8', errors='ignore')
        except (UnicodeDecodeError, LookupError):
            # Fallback if initial decoding fails
             try:
                 content = response.content.decode('iso-8859-1', errors='ignore')
             except Exception:
                  logging.warning(f"Could not decode content from {url}")
                  return None # Give up if decoding fails multiple times

        if content:
             # TODO: Consider using BeautifulSoup to extract main text content instead of raw HTML?
             logging.info(f"Successfully fetched content from {url} (length: {len(content)})")
             return content[:max_content_length] # Truncate
        else:
             logging.warning(f"Fetched empty content from {url}")
             return "" # Return empty string for empty content

    except requests.exceptions.Timeout:
        logging.error(f"Timeout error fetching website {url} after {timeout} seconds.")
        return None
    except requests.exceptions.TooManyRedirects:
        logging.error(f"Too many redirects error fetching website {url}.")
        return None
    except requests.exceptions.SSLError as e:
         logging.error(f"SSL error fetching website {url}: {e}")
         return None
    except requests.exceptions.RequestException as e:
        # General request error (includes connection errors, HTTP errors via raise_for_status)
        logging.error(f"Failed to fetch website {url}: {e}")
        return None
    except Exception as e:
        # Catch any other unexpected errors
        logging.error(f"Unexpected error fetching website {url}: {e}")
        return None