# src/email_handler/formatter.py
"""Module for formatting email content and creating MIME messages."""
import logging
import base64
import os # Import os for basename
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication # Correct for generic attachments like PDF
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__) # Add logger

def create_mime_email(
    sender: str,
    to: str,
    subject: str,
    body_html: str, # This SHOULD contain placeholders like [IMAGE1], [IMAGE2]...
    inline_image_paths: Optional[List[Path]] = None,
    attachment_paths: Optional[List[Path]] = None
) -> MIMEMultipart:
    """
    Creates a MIMEMultipart email message with optional inline images and attachments.
    Assumes body_html contains placeholders like [IMAGE1], [IMAGE2] etc.
    which will be replaced by inline images.

    Args:
        sender: Sender's email address.
        to: Recipient's email address.
        subject: Email subject line.
        body_html: Email body content in HTML format with placeholders.
        inline_image_paths: List of Path objects for images to embed inline.
        attachment_paths: List of Path objects for files to attach.

    Returns:
        A MIMEMultipart email message object.
    """
    msg_root = MIMEMultipart('related') # Use 'related' for inline images
    msg_root['From'] = sender
    msg_root['To'] = to
    msg_root['Subject'] = subject

    # --- Prepare for image replacement ---
    image_replacements = {}
    if inline_image_paths:
        # Ensure we don't try to use more images than placeholders expected (e.g., 3)
        num_images_to_use = min(len(inline_image_paths), 3) # Assuming max 3 placeholders
        for i in range(num_images_to_use):
            img_path = inline_image_paths[i]
            placeholder = f'[IMAGE{i+1}]' # Placeholders [IMAGE1], [IMAGE2], [IMAGE3]
            image_cid = f'image{i+1}'     # Generate CID 'image1', 'image2', 'image3'
            # Basic img tag, consider adding style/alt attributes if needed
            img_tag = f'<img src="cid:{image_cid}" alt="{os.path.basename(img_path)}" border="0" style="max-width: 100%; height: auto; border: 0; outline: none; box-shadow: none; text-decoration: none; display: block;"><br>'
            image_replacements[placeholder] = (image_cid, img_tag, img_path)
            logger.debug(f"Prepared replacement: {placeholder} -> CID:{image_cid}")

    # --- Replace placeholders in HTML body ---
    modified_body_html = body_html
    if image_replacements: # Only replace if there are images/placeholders defined
        for placeholder, (_, img_tag, _) in image_replacements.items():
            if placeholder in modified_body_html:
                modified_body_html = modified_body_html.replace(placeholder, img_tag)
                logger.debug(f"Replaced '{placeholder}' in HTML body.")
            else:
                logger.warning(f"Placeholder '{placeholder}' not found in generated HTML body.")

    # --- Attach MODIFIED HTML body ---
    msg_html = MIMEText(modified_body_html, 'html')
    msg_root.attach(msg_html)

    # --- Embed inline images (using the generated CIDs) ---
    if image_replacements:
        for placeholder, (content_id, _, img_path) in image_replacements.items():
            if not img_path or not Path(img_path).is_file(): # Check if path is valid Path object and exists
                logging.warning(f"Inline image file not found or invalid path, skipping: {img_path} (for placeholder {placeholder})")
                continue
            try:
                img_path_obj = Path(img_path) # Ensure it's a Path object
                with open(img_path_obj, 'rb') as img_file:
                    img_subtype = img_path_obj.suffix[1:].lower()
                    mime_image = MIMEImage(img_file.read(), _subtype=img_subtype, name=img_path_obj.name)

                # Add the Content-ID header, matching the cid used in the HTML tag
                mime_image.add_header('Content-ID', f'<{content_id}>')
                mime_image.add_header('Content-Disposition', 'inline', filename=img_path_obj.name)

                msg_root.attach(mime_image)
                logging.info(f"Attached inline image {img_path_obj.name} with CID: {content_id}") # Use INFO for successful attachment
            except FileNotFoundError:
                 logging.error(f"FileNotFoundError attaching inline image {img_path} for placeholder {placeholder}")
            except Exception as e:
                logging.error(f"Error attaching inline image {img_path} for placeholder {placeholder}: {e}")

    # --- Add regular attachments ---
    if attachment_paths:
        from email.mime.base import MIMEBase # Local import ok here
        from email import encoders       # Local import ok here
        for att_path in attachment_paths:
            if not att_path or not Path(att_path).is_file(): # Check if path is valid Path object and exists
                logging.warning(f"Attachment file not found or invalid path, skipping: {att_path}")
                continue
            try:
                att_path_obj = Path(att_path) # Ensure it's a Path object
                with open(att_path_obj, 'rb') as att_file:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(att_file.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename=\"{att_path_obj.name}\"", # Use actual name
                )
                msg_root.attach(part)
                logging.info(f"Attached file: {att_path_obj.name}") # Use INFO
            except FileNotFoundError:
                logging.error(f"FileNotFoundError attaching file {att_path}")
            except Exception as e:
                logging.error(f"Error attaching file {att_path}: {e}")

    return msg_root