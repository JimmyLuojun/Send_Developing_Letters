# src/email_handler/__init__.py
"""Package for handling email formatting, image selection, and sending/saving."""

from .formatter import create_mime_email
from .image_selector import select_relevant_images
from .sender import save_email_to_drafts

__all__ = [
    "create_mime_email",
    "select_relevant_images",
    "save_email_to_drafts",
]