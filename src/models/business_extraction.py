# src/models/business_extraction.py
import requests # requests is a python library, which is used to send the request to the API;
from typing import Optional
# typing is a python library, which is used to type the variables; Optional is a class in the typing library, which is used to type the variables; Optional[str] is a type hint, which is used to hint the type of the variables;
from src.models.deepseek_api import DeepSeekAPI, create_message

def extract_main_business(api_key: str, website_content: str) -> Optional[str]:
    """Extracts the main business from website content."""

    deepseek = DeepSeekAPI(api_key)

    prompt = f"""
    Extract the main business description from the following website content.
    Provide a concise summary (1-2 sentences) of the company's primary activity.

    Website Content:
    {website_content}

    Main Business Description:
    """

    messages = [
        create_message("system", "You are a helpful assistant."),
        create_message("user", prompt),
    ]

    return deepseek.get_completion("deepseek-chat", messages)  # Use deepseek-chat for V3

def extract_main_business_old(api_url: str, api_key: str) -> Optional[str]:
    """
    Extracts the main business name from a document using an external API.

    Args:
        api_url: The URL of the API endpoint.
        api_key: The API key for authentication.

    Returns:
        The extracted main business name, or None if extraction fails.  Returns 'Unknown' if response is empty.
    """
    headers = {"Authorization": f"Bearer {api_key}"} # Bearer is a type of authentication;

    try:
        response = requests.post(api_url, headers=headers)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        data = response.json() #.json() is a method that is used to convert the response to a json object; here, data is assumed to be a json object;
        if data and "business_name" in data: # if data is not None and "business_name" is in data;
            return data["business_name"]
        else:
            return "Unknown" # return "Unknown" is to return the value "Unknown";

    except requests.exceptions.RequestException as e: # requests.exceptions.RequestException is a built-in exception in python, which is used to catch the error when the request is not successful;
        print(f"Error during API call: {e}")
        return None # return None is to return the value None; None is a built-in constant in python, which is used to represent the absence of a value;