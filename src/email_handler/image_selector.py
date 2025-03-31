# src/email_handler/image_selector.py
"""Module for selecting relevant images based on context."""
import re
import logging
from pathlib import Path
from typing import List, Set

def _extract_keywords_from_filename(filename_str: str) -> Set[str]:
    """Extracts potential keywords from a filename string."""
    cleaned_filename_str = filename_str.strip() # Strip input first
    if not cleaned_filename_str:
        return set()

    # Use the cleaned string for Path operations
    filename_path = Path(cleaned_filename_str)
    filename = filename_path.name # Get potentially stripped filename part
    base = filename_path.stem # Get potentially stripped base name
    # Ensure extension is lowercase and dot removed
    ext = filename_path.suffix.lower().replace('.', '')

    keywords = set()
    if ext:
        keywords.add(ext)

    # Remove leading numbers, dots, spaces, hyphens, UNDERSCORES for cleaner word splitting
    # Also strip remaining whitespace from the result
    base_cleaned = re.sub(r'^[\d._\s\-]+', '', base).strip()

    # Split by sequences of common delimiters and clean parts
    words = set()
    if base_cleaned: # Only split if base_cleaned is not empty
        # Use regex split for better handling of multiple delimiters
        parts = re.split(r'[\s_-]+', base_cleaned)
        for part in parts:
            cleaned_part = part.strip().lower()
            # Optional: Add more filtering like minimum length if needed
            if cleaned_part:
                words.add(cleaned_part)

    # If no words found after splitting, use the whole cleaned base name if it exists
    if not words and base_cleaned:
        words.add(base_cleaned.lower())

    keywords.update(words)
    # Add original filename (lowercase, stripped) and cleaned base (lowercase) as keywords
    keywords.add(filename.lower()) # filename is from cleaned_filename_str
    if base_cleaned:
        keywords.add(base_cleaned.lower())

    # Remove empty strings just in case
    keywords.discard('')

    logging.debug(f"Keywords extracted from '{filename}': {keywords}")
    return keywords


def select_relevant_images(
    image_dir: Path,
    email_body: str,
    company_name: str,
    max_images: int = 3
) -> List[Path]:
    """
    Selects up to max_images relevant images from a directory based on email context.

    Args:
        image_dir: Path object for the directory containing candidate images.
        email_body: The HTML body of the email for context.
        company_name: The target company name for context.
        max_images: The maximum number of images to select.

    Returns:
        A list of Path objects for the selected images.
    """
    if not image_dir.is_dir():
        logging.error(f"Image directory not found: {image_dir}")
        return []

    # Find candidate image files (adjust patterns if needed)
    candidate_images = list(image_dir.glob("*.jpg")) + \
                       list(image_dir.glob("*.jpeg")) + \
                       list(image_dir.glob("*.png")) + \
                       list(image_dir.glob("*.gif")) # Add other types if necessary

    if not candidate_images:
        logging.warning(f"No candidate images found in: {image_dir}")
        return []
    logging.info(f"Found {len(candidate_images)} candidate images in {image_dir}.")

    # Create context words from email body and company name
    context_text = f"{email_body} {company_name}".lower()
    # Extract words (alphanumeric sequences)
    context_words = set(re.findall(r'\b\w+\b', context_text))
    logging.debug(f"Context words for scoring (sample): {list(context_words)[:20]}")

    # Score images based on keyword overlap
    image_scores = []
    for img_path in candidate_images:
        filename_keywords = _extract_keywords_from_filename(img_path.name)
        # Simple intersection score
        score = len(filename_keywords.intersection(context_words))
        image_scores.append((img_path, score))
        logging.debug(f"Image '{img_path.name}' score: {score}")

    # Sort images by score (descending)
    image_scores.sort(key=lambda x: x[1], reverse=True)

    # Select top N images
    selected_paths = [img_path for img_path, score in image_scores[:max_images]]

    # If fewer than max_images were selected based on score, fill remaining slots
    # with other candidates (preserving initial order if scores were 0)
    if len(selected_paths) < max_images:
        logging.debug(f"Only {len(selected_paths)} images selected by score. Filling remaining slots.")
        already_selected_set = set(selected_paths)
        remaining_candidates = [img_path for img_path, score in image_scores if img_path not in already_selected_set]
        needed = max_images - len(selected_paths)
        selected_paths.extend(remaining_candidates[:needed])

    logging.info(f"Selected {len(selected_paths)} images: {[p.name for p in selected_paths]}")
    return selected_paths

# Note: The add_uniform_border function is omitted as per the plan,
# assuming images in `unified_images_dir` are pre-processed.
# If needed, it would be added here, taking image paths and output dir.