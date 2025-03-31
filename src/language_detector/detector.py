# src/language_detector/detector.py
import logging
import re
from typing import Optional, Dict
from urllib.parse import urlparse
try:
    from langdetect import detect, LangDetectException
    LANGDETECT_AVAILABLE = True
except ImportError:
    logging.warning("The 'langdetect' library is not installed. Language detection from content will be skipped. Run 'poetry add langdetect'.")
    LANGDETECT_AVAILABLE = False
    LangDetectException = Exception # Dummy exception

logger = logging.getLogger(__name__)

# Basic TLD to language mapping (expand as needed)
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
    # Add more... check wikipedia for TLDs by country
}

def detect_language_from_tld(url: str) -> Optional[str]:
    """Detects language based on top-level domain."""
    try:
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname
        if hostname:
            hostname_lower = hostname.lower()
            parts = hostname_lower.split('.')
            if len(parts) >= 2:
                # Check TLD first (e.g., .de)
                tld = "." + parts[-1]
                lang = TLD_LANG_MAP.get(tld)
                if lang:
                    logger.info(f"Detected language '{lang}' from TLD '{tld}' in URL '{url}'")
                    return lang
                # Check common SLD+TLD (e.g., .co.uk, .com.br)
                if len(parts) >= 3 and tld in ['.uk', '.au', '.nz']: # Add others if needed
                     sld_tld = "." + parts[-2] + tld
                     # Currently no SLD specific rules in map, but could add e.g. '.co.uk': 'en'
                     lang = TLD_LANG_MAP.get(sld_tld)
                     if lang:
                         logger.info(f"Detected language '{lang}' from SLD+TLD '{sld_tld}' in URL '{url}'")
                         return lang
        logger.debug(f"Could not determine specific language from TLD in URL '{url}'")
        return None
    except Exception as e:
        logger.error(f"Error parsing URL '{url}' for TLD detection: {e}")
        return None

def detect_language_from_content(content: str) -> Optional[str]:
    """Detects language from text content using langdetect."""
    if not LANGDETECT_AVAILABLE:
        return None # Skip if library not installed

    min_length = 50 # Minimum characters needed for somewhat reliable detection
    if not content or not isinstance(content, str) or len(content) < min_length:
        logger.debug("Not enough content to detect language.")
        return None
    try:
        # Simple HTML tag removal
        text_only = re.sub('<[^<]+?>', ' ', content)
        text_only = re.sub(r'\s+', ' ', text_only).strip() # Consolidate whitespace

        if len(text_only) < min_length:
             logger.debug(f"Not enough meaningful text (length {len(text_only)}) after cleaning to detect language.")
             return None

        # Limit length passed to langdetect
        detect_sample = text_only[:3000]

        lang_code = detect(detect_sample)
        # Normalize common cases if needed (e.g., langdetect might return 'zh-cn')
        lang_code = lang_code.lower()
        logger.info(f"Detected language '{lang_code}' from content sample.")
        return lang_code
    except LangDetectException:
        logger.warning("Could not detect language from content (langdetect error). Content might be too short, mixed, or unsupported.")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during language detection from content: {e}")
        return None

def determine_language(url: str, content: Optional[str], default_lang: str = 'en') -> str:
    """
    Determines target language using content first, then TLD, then default.
    """
    # 1. Try detecting from content
    if content:
        lang = detect_language_from_content(content)
        if lang:
            return lang

    # 2. Try detecting from TLD
    lang = detect_language_from_tld(url)
    if lang:
        return lang

    # 3. Fallback to default
    logger.info(f"Could not reliably detect language from content or TLD for '{url}'. Using default '{default_lang}'.")
    return default_lang.lower() # Ensure default is lowercase