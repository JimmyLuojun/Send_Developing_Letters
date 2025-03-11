#/Users/junluo/Documents/Send_Developing_Letters/src/models/deepseek_api.py
import os
from openai import OpenAI
from typing import Optional, List, Dict, Any
import time

class DeepSeekAPI:
    """
    A class to encapsulate interactions with the DeepSeek API.
    """

    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com/v1"):
        """
        Initializes the DeepSeekAPI client.

        Args:
            api_key: Your DeepSeek API key.
            base_url: The base URL for the DeepSeek API.
        """
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def get_completion(self, model: str, messages: List[Dict[str, str]]) -> Optional[str]:
        """
        Gets a chat completion from the DeepSeek API.

        Args:
            model: The name of the DeepSeek model to use (e.g., "deepseek-reasoner").
            messages: A list of message dictionaries.

        Returns:
            The generated text content, or None if an error occurs.
        """
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                stream=False  # Non-streaming mode
            )

            if response and response.choices and response.choices[0].message:
                return response.choices[0].message.content.strip()
            else:
                return None

        except Exception as e:
            print(f"Error during DeepSeek API call: {e}")
            return None
        finally:
            time.sleep(1)


# --- Helper function to create messages ---
def create_message(role: str, content: str) -> Dict[str, str]:
    """Creates a message dictionary for the DeepSeek API."""
    return {"role": role, "content": content}

# --- Example Usage (for testing only) ---
if __name__ == "__main__":
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise ValueError("API_KEY not found in .env file")

    base_url = os.getenv("BUSINESS_EXTRACTION_API_URL", "https://api.deepseek.com/v1/chat/completions")
    deepseek = DeepSeekAPI(api_key, base_url)

    messages = [
        create_message("system", "You are a helpful assistant."),
        create_message("user", "What is the capital of France?"),
    ]

    completion = deepseek.get_completion("deepseek-chat", messages)
    if completion:
        print(f"Completion: {completion}")
    else:
        print("Failed to get completion.")