# src/api_clients/deepseek_client.py
"""
Client for interacting with the DeepSeek API.
Encapsulates API calls for business extraction and cooperation points.
"""
import logging
import time
import json
from typing import Optional, List, Dict, Any

# Import specific OpenAI/HTTPX errors.
from openai import OpenAI, APIError, RateLimitError, Timeout, APIConnectionError, BadRequestError
import httpx  # add at top if missing

# (Ensure the incorrect import below is REMOVED)
# from src.core.target_company_data import _create_message # <--- DELETE THIS LINE

# Configure logging
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Helper function - MUST BE DEFINED HERE
def _create_message(role: str, content: str) -> Dict[str, str]:
    """Creates a message dictionary for the DeepSeek API."""
    if role not in ["system", "user", "assistant"]:
        logger.warning(f"Invalid role '{role}' provided for message. Using 'user'.")
        role = "user"
    return {"role": role, "content": content}


class DeepSeekClient:
    """
    Encapsulates interactions with the DeepSeek API using the OpenAI library format.
    Handles API calls for chat completions, including error handling and retries.
    """
    DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
    DEFAULT_REQUEST_TIMEOUT = 30 # seconds
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_INITIAL_DELAY = 1.0 # seconds

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        request_timeout: int = DEFAULT_REQUEST_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        initial_delay: float = DEFAULT_INITIAL_DELAY
    ):
        """Initialize the DeepSeek client.
        
        Args:
            api_key: The API key for authentication
            base_url: The base URL for the API
            request_timeout: Timeout in seconds for API requests
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay between retries in seconds
        """
        if not api_key:
            raise ValueError("API key is required")
            
        self.api_key = api_key
        self.base_url = base_url
        self.request_timeout = request_timeout
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        
        # Initialize the OpenAI client with our custom settings
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=request_timeout,
            max_retries=0  # We handle retries ourselves
        )
        
        logger.info(
            "Initialized DeepSeekClient with base_url=%s, timeout=%ds, max_retries=%d, initial_delay=%.1fs",
            base_url, request_timeout, max_retries, initial_delay
        )

    def _get_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_retries: int = DEFAULT_MAX_RETRIES,
        initial_delay: float = DEFAULT_INITIAL_DELAY
    ) -> Optional[str]:
        retries = 0
        delay = initial_delay
        last_exception = None
        while retries <= max_retries:
            attempt = retries + 1
            try:
                logger.debug(f"Attempt {attempt}/{max_retries + 1}: Calling chat.completions.create(model='{model}')...")
                response = self.client.chat.completions.create(model=model, messages=messages, stream=False)
                logger.debug(f"Attempt {attempt}: API call successful.")
                if not response or not response.choices or len(response.choices) == 0:
                    logger.warning(f"Received empty or invalid response structure. Response: {response}")
                    return None
                choice = response.choices[0]
                if not choice.message or choice.message.content is None:
                    logger.warning(f"Received choice with no message or empty content. Choice: {choice}")
                    return None
                completion = choice.message.content.strip()
                usage = getattr(response, 'usage', None)
                usage_str = f" Usage: {usage}" if usage else ""
                logger.debug(f"Completion received. Length: {len(completion)}.{usage_str}")
                return completion
            except Exception as e:
                last_exception = e
                error_type_name = type(e).__name__
                # Retriable errors:
                if isinstance(e, RateLimitError):
                    logger.warning(f"Attempt {attempt}: Rate limit error ({error_type_name}). Retrying in {delay:.1f}s... Error: {e}")
                    should_retry = True
                elif isinstance(e, Timeout) or isinstance(e, httpx.ReadTimeout):
                    logger.warning(f"Attempt {attempt}: Timeout error ({error_type_name}). Retrying in {delay:.1f}s... Error: {e}")
                    should_retry = True
                elif isinstance(e, APIConnectionError):
                    logger.warning(f"Attempt {attempt}: Connection error ({error_type_name}). Retrying in {delay:.1f}s... Error: {e}")
                    should_retry = True
                # Non-retriable errors:
                elif isinstance(e, BadRequestError):
                    logger.error(f"Attempt {attempt}: Bad Request error ({error_type_name}). Not retrying. Error: {e}", exc_info=False)
                    return None
                elif isinstance(e, APIError):
                    status_code = getattr(e, 'status_code', None)
                    if status_code and 500 <= status_code < 600:
                        logger.warning(f"Attempt {attempt}: Server error ({error_type_name}, Status: {status_code}). Retrying in {delay:.1f}s... Error: {e}")
                        should_retry = True
                    else:
                        logger.error(f"Attempt {attempt}: Non-retriable API error ({error_type_name}, Status: {status_code}). Not retrying. Error: {e}", exc_info=True)
                        return None
                else:
                    logger.exception(f"Attempt {attempt}: Unexpected error during API call: {error_type_name}. Not retrying.", exc_info=True)
                    return None

                # If retriable and we have attempts left, wait and retry.
                if should_retry and retries < max_retries:
                    retries += 1
                    logger.info(f"Waiting {delay:.1f}s before retry {retries + 1}...")
                    try:
                        time.sleep(delay)
                    except Exception as sleep_err:
                        logger.error(f"Error during retry delay sleep: {sleep_err}")
                        return None
                    delay *= 2
                    continue
                else:
                    break

        logger.error(f"Failed to get completion for model '{model}' after {attempt} attempts. Last error: {last_exception!r}")
        return None

    # --- Public Methods ---
    # (Keep extract_main_business and identify_cooperation_points as previously refined)
    def extract_main_business(self, website_content: str, model: str = "deepseek-chat") -> Optional[str]:
        # ... (implementation as before) ...
        if not isinstance(website_content, str) or not website_content.strip(): return None
        max_content_length = 3000; truncated_content = website_content[:max_content_length]
        if len(website_content) > max_content_length: truncated_content += "..."
        prompt = f"""
        Analyze the following website content and extract the main business description.
        Provide a concise summary (1-2 sentences maximum) focusing ONLY on the company's primary activity, products, or services offered.
        Ignore boilerplate text like contact forms, privacy policies, cookie notices, navigation menus, or footers unless they explicitly state the core business focus.

        Website Content:
        ---
        {truncated_content}
        ---

        Main Business Description (1-2 sentences):
        """
        logger.info(f"Requesting main business extraction from DeepSeek API using model '{model}'...")
        messages = [_create_message("system", "..."), _create_message("user", prompt)]
        main_business = self._get_completion(model, messages)
        if main_business: logger.info("Successfully extracted main business description.")
        else: logger.error("Failed to extract main business description...")
        return main_business

    def identify_cooperation_points(self, skyfend_business_desc: str, target_company_desc: str, model: str = "deepseek-chat") -> Optional[str]:
        # ... (implementation as before) ...
        if not isinstance(skyfend_business_desc, str) or not skyfend_business_desc.strip() or \
           not isinstance(target_company_desc, str) or not target_company_desc.strip(): return None
        prompt = f"""
        Task: Analyze the business descriptions ...

        Company A ({skyfend_business_desc}):
        ---
        {skyfend_business_desc}
        ---

        Company B (Target Company):
        ---
        {target_company_desc}
        ---

        Instructions: ...

        Potential Cooperation Points:
        """
        logger.info(f"Requesting cooperation points identification from DeepSeek API using model '{model}'...")
        messages = [_create_message("system", "..."), _create_message("user", prompt)]
        cooperation_points = self._get_completion(model, messages)
        if cooperation_points and "no specific cooperation points" not in cooperation_points.lower():
             logger.info("Successfully identified potential cooperation points.")
             return cooperation_points
        elif cooperation_points:
             logger.info("API indicated no specific cooperation points were identified...")
             return "No cooperation points identified"
        else:
             logger.error("Failed to identify cooperation points...")
             return "No cooperation points identified"