# src/letter_generator/generator.py
"""Module responsible for generating the developing letter content."""
import logging
from typing import Dict
from src.core import LetterGenerator, LetterGenerationInput, DevelopingLetter
from src.api_clients import DeepSeekClient # Import the specific client

# Configure logging (ensure it's configured somewhere, e.g., main.py)
logger = logging.getLogger(__name__)

class DeepSeekLetterGenerator(LetterGenerator):
    """Generates developing letters using the DeepSeek API."""

    def __init__(self, deepseek_client: DeepSeekClient):
        """
        Initializes the generator with a DeepSeek client instance.

        Args:
            deepseek_client: An initialized DeepSeekClient.
        """
        self.client = deepseek_client
        logging.info("DeepSeekLetterGenerator initialized.")

    def generate(self, input_data: LetterGenerationInput, model: str = "deepseek-chat") -> DevelopingLetter:
        """
        Generates a developing letter using the DeepSeek API, including image placeholders.

        Args:
            input_data: Object containing necessary data (cooperation points, company names).
            model: The DeepSeek model to use.

        Returns:
            A DevelopingLetter object containing the generated subject and body (with placeholders).
            Returns a default letter on error.
        """
        logging.info(f"Generating letter for {input_data.target_company_name}...")

        # Construct a detailed prompt based on the original main4.py logic
        prompt = f"""
        Subject: Compose a concise and compelling subject line for a business development email from Skyfend to {input_data.target_company_name}. Mention both company names and hint at potential cooperation.

        Body: Write a formal but engaging business development letter from Skyfend (sender: Jimmy, Overseas Sales Manager) to {input_data.contact_person_name} at {input_data.target_company_name}.

        Instructions:
        1.  Sender: Jimmy, Overseas Sales Manager, Skyfend.
        2.  Recipient: {input_data.contact_person_name}, {input_data.target_company_name}.
        3.  Skyfend Background: Briefly introduce Skyfend as a leader in counter-drone technology and low-altitude airspace security solutions. Mention focus on addressing threats from FPV drones and protecting critical infrastructure/events.
        4.  Cooperation Points: Seamlessly integrate these identified potential cooperation points:
            ---
            {input_data.cooperation_points}
            ---
        5.  Structure: Aim for 3-4 concise paragraphs.
            - Paragraph 1: Introduction of Skyfend and reason for outreach (based on potential synergy).
            - Paragraph 2/3: Elaborate on the cooperation points, highlighting mutual benefits.
            - Paragraph 4: Call to action - suggest a brief meeting to discuss possibilities further. Provide sender's contact info implicitly (they can reply).
        6.  Tone: Professional, collaborative, forward-looking. Avoid overly technical jargon unless essential.
        7.  Attachment Mention: Include a sentence mentioning that Skyfend's product brochure is attached for reference.
        8.  ***IMPORTANT - Image Placeholders:*** Within the generated HTML email body, insert the literal text placeholders `[IMAGE1]`, `[IMAGE2]`, and `[IMAGE3]`. Aim to place `[IMAGE1]` after the introductory paragraph, `[IMAGE2]` after describing the main cooperation points, and `[IMAGE3]` before the final call to action/closing paragraph. Ensure the text flows well around these placeholders.
        9.  Output Format: Generate ONLY the subject line text first, followed by "---BODY_SEPARATOR---", then the email body formatted in basic, clean HTML suitable for email clients (use <p>, <strong>, <a> tags sparingly if needed, no complex CSS or layouts). Ensure proper spacing between paragraphs using <p> tags AND include the image placeholders as instructed in point 8.

        Example Output Structure:
        Subject: [Your generated subject line]
        ---BODY_SEPARATOR---
        <p>Dear {input_data.contact_person_name},</p>
        <p>Introduction paragraph...</p>
        [IMAGE1]
        <p>Cooperation points paragraph...</p>
        [IMAGE2]
        <p>Further points or benefits...</p>
        [IMAGE3]
        <p>We have attached our product brochure for your reference...</p>
        <p>Call to action paragraph...</p>
        <p>Sincerely,<br>Jimmy<br>Overseas Sales Manager<br>Skyfend</p>
        """

        # Use the _create_message helper from deepseek_client module if needed, or define locally
        # Assuming _create_message is accessible or defined within this scope/module
        # If defined in deepseek_client.py, ensure it's imported or accessible.
        # For simplicity, let's assume _create_message is available here:
        def _create_message(role: str, content: str) -> Dict[str, str]:
             """Creates a message dictionary.""" # Basic local definition
             return {"role": role, "content": content}

        messages = [
            _create_message("system", "You are an expert B2B communication assistant writing professional outreach emails formatted in HTML."),
            _create_message("user", prompt)
        ]

        try:
            # Assuming self.client is DeepSeekClient and has _get_completion
            completion = self.client._get_completion(model, messages)

            if completion and "---BODY_SEPARATOR---" in completion:
                subject_part, body_part = completion.split("---BODY_SEPARATOR---", 1)
                # Clean up subject prefix if present
                subject = subject_part.replace("Subject:", "").strip()
                body_html = body_part.strip() # This body_html should now contain [IMAGE1] etc.
                logging.info(f"Successfully generated letter for {input_data.target_company_name}. Subject: {subject}")
                # Return the letter with placeholders in the body
                return DevelopingLetter(subject=subject, body_html=body_html)
            else:
                logging.error(f"Failed to parse generated letter structure for {input_data.target_company_name}. Completion: {completion}")
                return DevelopingLetter(subject=f"Potential Cooperation with {input_data.target_company_name}", body_html="<p>Error generating letter content.</p>")

        except Exception as e:
            logging.error(f"Error during letter generation API call for {input_data.target_company_name}: {e}", exc_info=True)
            return DevelopingLetter(subject=f"Potential Cooperation with {input_data.target_company_name}", body_html="<p>Error generating letter content.</p>")