#/Users/junluo/Documents/Send_Developing_Letters/src/utils/generate_developing_letters.py
import os
from openai import OpenAI
from typing import Dict, Any, Optional
import logging

def generate_developing_letter(api_key: str, instructions: str, cooperation_points: str, target_company_name: str, contact_person: str) -> str:
    """
    Generates a developing letter using the DeepSeek API, formatted with HTML.

    Args:
        api_key: Your DeepSeek API key.
        instructions:  General instructions (from main.py).
        cooperation_points: Identified cooperation points.
        target_company_name: The name of the target company.
        contact_person: The name of the contact person (can be an empty string).

    Returns:
        The generated letter (HTML formatted), or a default message if generation fails.
    """
    client = OpenAI(api_key=api_key, base_url=os.getenv("LETTER_GENERATION_API_URL", "https://api.deepseek.com/v1"))

    # --- Construct the FULL prompt ---
    # Salutation
    if contact_person:
        salutation = f"Dear {contact_person},"
    else:
        salutation = "Dear Sir/Madam,"

    prompt = f"""
{instructions}

Generate a formal business letter proposing a partnership. The letter should be concise (160-230 words).

**Specific Instructions and Context:**

*   **Sender:** Jimmy, Overseas Sales Manager at Skyfend (a subsidiary of Autel).
*   **Recipient:** {salutation} (at {target_company_name}).
*   **Company Background:** We've been following {target_company_name}'s development.
*   **Skyfend's Global Presence:** Skyfend has exported devices to partners in Africa, Europe, and America.
*   **Focus:** Emphasize potential cooperation opportunities.
*   **FPV Drone Threats:** Emphasize Skyfend's devices for FPV drone threats and commercial drones (DJI, Autel, Parrot, etc.).
*   **Letter Structure:** Each paragraph should consist of 2-3 sentences.
*   **Call to Action:** Propose a video meeting or call.
*   **Attachment:** Mention that a product brochure is attached.
*   **Subject:** Proposal for Strategic Partnership Between Skyfend and {target_company_name}

**Cooperation Points:**

{cooperation_points}

**Output Format:**

Return ONLY the body of the letter, formatted using basic HTML. Do *not* include any sender address, date, or recipient address *outside* the letter body. The letter *should* start *directly* with the salutation.

Use the following HTML tags for formatting:

*   `<p>` tags for paragraphs.  Use separate `<p>` tags for each paragraph.
*   `<br>` for explicit line breaks where needed (e.g., within the address, after the salutation).
*   `<strong>` or `<b>` tags for bold text (e.g., for key benefits or company names).
*    If listing cooperation points, use a `<ul>` (unordered list) and `<li>` (list item) tags for each point.
"""

    messages = [
        {"role": "system", "content": "You are a helpful assistant that follows instructions extremely well. You generate high-quality, professional business letters, and you are skilled at using basic HTML for formatting."},
        {"role": "user", "content": prompt}
    ]

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",  # Or deepseek-reasoner
            messages=messages,
            stream=False,
            temperature=0.7,
        )

        if response and response.choices and response.choices[0].message:
            letter_content = response.choices[0].message.content.strip()

            # --- Remove `html and ` if present ---
            letter_content = letter_content.replace("`html", "").replace("`", "").strip()
            return letter_content
        else:
            return 'No letter content generated'

    except Exception as e:
        print(f"API request error: {e}")
        return 'No letter content generated'

if __name__ == '__main__':
    # Example Usage (replace with your actual API key and data)
    api_key = "YOUR_DEEPSEEK_API_KEY"  # Replace with your actual API key
    instructions = "Generate a formal business development letter."
    cooperation_points = """
    1.  **Joint Development:** Collaborate on creating a new drone detection system.
    2.  **Marketing Synergy:** Co-market our products to reach a wider audience.
    """
    company_name = "Example Corp" # Test name
    contact_person = "Mr. Smith" # Test name

    logging.basicConfig(level=logging.INFO)

    letter = generate_developing_letter(api_key, instructions, cooperation_points, company_name, contact_person)
    if letter:
        print(letter)