# src/letter_generator/generator.py
"""Module responsible for generating the developing letter content."""
import logging
from typing import Dict, Optional # Import Optional
from src.core import LetterGenerator, LetterGenerationInput, DevelopingLetter
from src.api_clients import DeepSeekClient

logger = logging.getLogger(__name__)

# Define or import _create_message helper function
def _create_message(role: str, content: str) -> Dict[str, str]:
    """Creates a message dictionary for the DeepSeek API."""
    if role not in ["system", "user", "assistant"]:
        logger.warning(f"Invalid role '{role}' provided for message. Using 'user'.")
        role = "user"
    return {"role": role, "content": content}

class DeepSeekLetterGenerator(LetterGenerator):
    """Generates developing letters using the DeepSeek API."""

    def __init__(self, deepseek_client: DeepSeekClient):
        """Initializes the generator with a DeepSeek client instance."""
        self.client = deepseek_client
        logging.info("DeepSeekLetterGenerator initialized.")

    # --- MODIFIED SIGNATURE: target_language is now Optional[str] = None ---
    def generate(self, input_data: LetterGenerationInput, target_language: Optional[str] = None, model: str = "deepseek-chat") -> DevelopingLetter:
        """
        Generates a developing letter using the DeepSeek API, including image placeholders
        and optionally targeting a specific language.

        Args:
            input_data: Object containing necessary data (cooperation points, company names).
            target_language: Optional desired language code (e.g., 'en', 'de'). Defaults to 'en' if None.
            model: The DeepSeek model to use.

        Returns:
            A DevelopingLetter object containing the generated subject and body.
            Returns a default letter on error.
        """
        # --- ADDED LOGIC: Determine actual language to use ---
        # Default to English ('en') if no target_language is provided or if it's empty
        actual_language = target_language.strip().lower() if target_language and isinstance(target_language, str) else 'en'
        logging.info(f"Generating letter for {input_data.target_company_name} in language '{actual_language}'...")
        # --- END ADDED LOGIC ---


        # --- MODIFIED PROMPT: Uses 'actual_language' variable ---
        prompt = f"""
        Target Language for Output: {actual_language}

        Subject: Compose IN {actual_language.upper()} a concise and compelling subject line for a business development email from Skyfend to {input_data.target_company_name}. Mention both company names and hint at potential cooperation.

        Body: Write IN {actual_language.upper()} a formal but engaging business development letter from Skyfend (sender: Jimmy, Overseas Sales Manager) to {input_data.contact_person_name} at {input_data.target_company_name}.

        Instructions:
        1. Ensure ALL output (Subject and Body HTML) is in {actual_language.upper()}.
        2. Sender: Jimmy, Overseas Sales Manager, Skyfend. # CONSISTENT SENDER
        3. Recipient: {input_data.contact_person_name}, {input_data.target_company_name}.
        4. Skyfend Background: Briefly introduce Skyfend... (AI should translate if possible)
        5. Cooperation Points: Seamlessly integrate these identified potential cooperation points (AI should translate if possible):
            ---
            {input_data.cooperation_points}
            ---
        6. Structure: Aim for 3-4 concise paragraphs... (keep structure)
        7. Tone: Professional, collaborative... (keep tone)
        8. Attachment Mention: Include a sentence IN {actual_language.upper()} mentioning that Skyfend's product brochure is attached for reference.
        9. ***IMPORTANT - Image Placeholders:*** Within the generated HTML email body IN {actual_language.upper()}, insert the literal text placeholders `[IMAGE1]`, `[IMAGE2]`, and `[IMAGE3]`. Aim to place `[IMAGE1]` after the introductory paragraph, `[IMAGE2]` after describing the main cooperation points, and `[IMAGE3]` before the final call to action/closing paragraph. Ensure the text flows well around these placeholders.
        10. Output Format: Generate ONLY the subject line text first, followed by "---BODY_SEPARATOR---", then the email body formatted in basic, clean HTML... Ensure output is in {actual_language.upper()} and includes placeholders...

        Example Output Structure (Illustrative - AI should use target language):
        Subject: [Subject in {actual_language.upper()}]
        ---BODY_SEPARATOR---
        <p>[Greeting in {actual_language.upper()} {input_data.contact_person_name}],</p>
        <p>[Intro in {actual_language.upper()}]</p>
        [IMAGE1]
        <p>[Cooperation points in {actual_language.upper()}]</p>
        [IMAGE2]
        <p>[Further points in {actual_language.upper()}]</p>
        [IMAGE3]
        <p>[Attachment mention in {actual_language.upper()}]</p>
        <p>[Call to action in {actual_language.upper()}]</p>
        <p>[Closing in {actual_language.upper()}],<br>Jimmy<br>Overseas Sales Manager<br>Skyfend</p> # CONSISTENT SIGNATURE
        """
        # --- END MODIFIED PROMPT ---

        messages = [
            _create_message("system", f"You are an expert B2B communication assistant writing professional outreach emails formatted in HTML. Your response MUST be entirely in the language corresponding to the code: {actual_language}."),
            _create_message("user", prompt)
        ]

        try:
            completion = self.client._get_completion(model, messages)

            if completion and "---BODY_SEPARATOR---" in completion:
                subject_part, body_part = completion.split("---BODY_SEPARATOR---", 1)
                subject = subject_part.replace("Subject:", "").strip()
                body_html = body_part.strip()
                if "[IMAGE1]" not in body_html: # Basic check
                     logger.warning(f"AI response for {input_data.target_company_name} might be missing image placeholders.")

                logging.info(f"Successfully generated letter for {input_data.target_company_name} in {actual_language}. Subject: {subject}")
                return DevelopingLetter(subject=subject, body_html=body_html)
            else:
                logging.error(f"Failed to parse generated letter structure for {input_data.target_company_name} in {actual_language}. Completion: {completion}")
                return DevelopingLetter(subject=f"Potential Cooperation with {input_data.target_company_name}", body_html=f"<p>Error generating letter content in {actual_language}.</p>")

        except Exception as e:
            logging.error(f"Error during letter generation API call for {input_data.target_company_name} in {actual_language}: {e}", exc_info=True)
            return DevelopingLetter(subject=f"Potential Cooperation with {input_data.target_company_name}", body_html=f"<p>Error generating letter content in {actual_language}.</p>")