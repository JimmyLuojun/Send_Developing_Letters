# src/language_detector/detector.py
import logging
import re
from typing import Optional, Dict
from urllib.parse import urlparse

# Attempt to import langdetect, set flag accordingly
try:
    from langdetect import detect, LangDetectException
    LANGDETECT_AVAILABLE = True
except ImportError:
    # Log only once at warning level if library is missing
    logging.getLogger(__name__).warning(
        "The 'langdetect' library is not installed. Language detection from "
        "content will be skipped. Run 'poetry add langdetect' or 'pip install langdetect'."
    )
    LANGDETECT_AVAILABLE = False
    # Define a dummy exception for type hinting consistency in except blocks
    class LangDetectException(Exception): pass

logger = logging.getLogger(__name__)

# --- TLD Mapping (Keep existing) ---
TLD_LANG_MAP: Dict[str, str] = {
    # German
    '.de': 'de', '.at': 'de', '.ch': 'de',
    # French
    '.fr': 'fr', '.be': 'fr', '.lu': 'fr', '.mc': 'fr', '.ca': 'fr', # Note: .ca is often fr or en
    # Spanish
    '.es': 'es', '.mx': 'es', '.ar': 'es', '.cl': 'es', '.co': 'es', '.pe': 'es',
    # Italian
    '.it': 'it',
    # Japanese
    '.jp': 'ja',
    # Chinese
    '.cn': 'zh-cn', '.hk': 'zh-cn', '.sg': 'zh-cn', # Simplified often default
    # Korean
    '.kr': 'ko',
    # Dutch
    '.nl': 'nl',
    # Portuguese
    '.pt': 'pt', '.br': 'pt',
    # Russian
    '.ru': 'ru',
    # English (Examples - often default, but can be explicit)
    '.uk': 'en', '.us': 'en', '.au': 'en', '.nz': 'en', '.ie': 'en',
    # Add more...
}
# --- End TLD Mapping ---

def detect_language_from_tld(url_or_domain: str) -> Optional[str]:
    """
    Detects language based on top-level domain from a URL or a domain string.
    """
    if not url_or_domain or not isinstance(url_or_domain, str):
        return None
    try:
        # Try parsing as URL first
        try:
            parsed_url = urlparse(url_or_domain)
            hostname = parsed_url.hostname or url_or_domain # Fallback if it's already just a domain
        except ValueError: # Handle cases where input might just be a domain
            hostname = url_or_domain

        if hostname:
            hostname_lower = hostname.lower().strip()
            # Remove www. prefix if present
            if hostname_lower.startswith('www.'):
                hostname_lower = hostname_lower[4:]

            parts = hostname_lower.split('.')
            if len(parts) >= 2:
                # Check full TLD first (e.g., .co.uk, .com.br) - more specific
                if len(parts) >= 3:
                    sld_tld = "." + parts[-2] + "." + parts[-1]
                    lang = TLD_LANG_MAP.get(sld_tld)
                    if lang:
                        logger.debug(f"Detected language '{lang}' from SLD+TLD '{sld_tld}' in '{url_or_domain}'")
                        return lang

                # Check primary TLD (e.g., .de, .fr)
                tld = "." + parts[-1]
                lang = TLD_LANG_MAP.get(tld)
                if lang:
                    logger.debug(f"Detected language '{lang}' from TLD '{tld}' in '{url_or_domain}'")
                    return lang

        logger.debug(f"Could not determine specific language from TLD in '{url_or_domain}'")
        return None
    except Exception as e:
        logger.error(f"Error parsing URL/domain '{url_or_domain}' for TLD detection: {e}")
        return None

# --- NEW FUNCTION ---
def detect_language_from_email_tld(email: str) -> Optional[str]:
    """
    Detects language based on the top-level domain of an email address.
    """
    if not email or '@' not in email:
        logger.debug(f"Invalid or missing email address for TLD detection: {email}")
        return None

    try:
        domain_part = email.split('@')[1]
        # Use the existing TLD detection logic on the domain part
        return detect_language_from_tld(domain_part)
    except IndexError:
        logger.error(f"Could not extract domain part from email: {email}")
        return None
    except Exception as e: # Catch any other unexpected errors
        logger.error(f"Error detecting language from email TLD ({email}): {e}")
        return None
# --- END NEW FUNCTION ---

def detect_language_from_content(content: str) -> Optional[str]:
    """Detects language from text content using langdetect."""
    if not LANGDETECT_AVAILABLE:
        return None # Skip if library not installed

    # Increased minimum length for better reliability
    min_length = 80
    if not content or not isinstance(content, str) or len(content) < min_length:
        logger.debug(f"Content too short (length {len(content) if content else 0}) to reliably detect language.")
        return None
    try:
        # More robust HTML/script/style removal
        text_only = re.sub(r'<script.*?</script>', ' ', content, flags=re.DOTALL | re.IGNORECASE)
        text_only = re.sub(r'<style.*?</style>', ' ', text_only, flags=re.DOTALL | re.IGNORECASE)
        text_only = re.sub(r'<[^>]+>', ' ', text_only) # Remove remaining tags
        text_only = re.sub(r'\s+', ' ', text_only).strip() # Consolidate whitespace

        if len(text_only) < min_length:
             logger.debug(f"Not enough meaningful text (length {len(text_only)}) after cleaning to detect language.")
             return None

        # Limit length passed to langdetect
        detect_sample = text_only[:4000] # Slightly increased sample

        lang_code = detect(detect_sample)
        lang_code = lang_code.lower() # Normalize case
        # Handle specific normalizations if needed (e.g., zh-cn/zh-tw -> zh) - depends on downstream use
        # if lang_code.startswith('zh'):
        #    lang_code = 'zh'
        logger.info(f"Detected language '{lang_code}' from content sample.")
        return lang_code
    except LangDetectException:
        logger.warning("Could not detect language from content (langdetect error). Content might be too short, mixed, or unsupported.")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during language detection from content: {e}", exc_info=True)
        return None

# --- MODIFIED FUNCTION SIGNATURE AND LOGIC ---
def determine_language(
    content: Optional[str],
    url: Optional[str] = None, # Make URL optional if sometimes unavailable
    recipient_email: Optional[str] = None, # Add email parameter
    default_lang: str = 'en'
    ) -> str:
    """
    Determines target language using content, email TLD, URL TLD, then default.

    Args:
        content: Text content scraped from the website (can be None).
        url: The website URL (can be None).
        recipient_email: The recipient's email address (can be None).
        default_lang: The fallback language code (e.g., 'en').

    Returns:
        The determined language code (lowercase).
    """
    final_lang = None

    # 1. Try detecting from content (highest priority if available)
    if content:
        lang_from_content = detect_language_from_content(content)
        if lang_from_content:
            final_lang = lang_from_content
            logger.info(f"Using language '{final_lang}' detected from content.")
            # Optional: Could still check TLDs here as a confirmation/override
            # if certain conditions are met, but let's keep it simple for now.

    # 2. If content detection didn't yield a result, try email TLD
    if final_lang is None and recipient_email:
        lang_from_email = detect_language_from_email_tld(recipient_email)
        if lang_from_email:
            final_lang = lang_from_email
            logger.info(f"Using language '{final_lang}' detected from email TLD ({recipient_email}).")

    # 3. If still no result, try website URL TLD
    if final_lang is None and url:
        lang_from_url = detect_language_from_tld(url)
        if lang_from_url:
            final_lang = lang_from_url
            logger.info(f"Using language '{final_lang}' detected from website URL TLD ({url}).")

    # 4. Fallback to default if no language determined
    if final_lang is None:
        final_lang = default_lang.lower() # Ensure default is lowercase
        logger.info(f"Could not reliably detect language from content or TLDs. Using default '{final_lang}'.")

    return final_lang.lower() # Return final determined language, ensuring lowercase
# --- END MODIFIED FUNCTION ---