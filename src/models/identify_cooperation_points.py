#/Users/junluo/Documents/Send_Developing_Letters/src/models/identify_cooperation_points.py
import os  # Import the os module
from openai import OpenAI
from typing import Optional  # Import Optional
from src.models.deepseek_api import DeepSeekAPI, create_message

def identify_cooperation_points(api_key: str, skyfend_business: str, target_business: str) -> str:
    """Identifies cooperation points."""

    deepseek = DeepSeekAPI(api_key)

    prompt = f"""
    Identify potential cooperation points between two companies.

    Company A (Skyfend): {skyfend_business}
    Company B (Target): {target_business}

    List 3-5 specific cooperation points, focusing on synergy and mutual benefit.
    Cooperation Points:
    """
    try:
        messages = [
            create_message("system", "You are a helpful assistant."),
            create_message("user", prompt),
        ]

        result = deepseek.get_completion("deepseek-reasoner", messages)  # Use deepseek-chat for V3
        return result if result else "No cooperation points identified"  # Return result or default message
    except Exception as e:
        print(f"API request error: {e}")
        return 'No cooperation points identified'