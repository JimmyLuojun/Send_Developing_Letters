# tests/test_format_and_send_email.py
import os
import pathlib
import pytest
import tempfile
from email.mime.multipart import MIMEMultipart

from src.utils.format_and_send_email import create_email_with_inline_images_and_attachments

@pytest.fixture
def dummy_files(tmp_path):
    # Create dummy inline image files.
    img1 = tmp_path / "img1.jpg"
    img1.write_bytes(b"dummy image data 1")
    img2 = tmp_path / "img2.jpg"
    img2.write_bytes(b"dummy image data 2")
    img3 = tmp_path / "img3.jpg"
    img3.write_bytes(b"dummy image data 3")
    
    # Create a dummy attachment file.
    attachment = tmp_path / "attachment.pdf"
    attachment.write_bytes(b"dummy pdf content")
    
    return [str(img1), str(img2), str(img3)], [str(attachment)]

def test_create_email_with_inline_images_and_attachments(dummy_files):
    image_paths, attachment_paths = dummy_files
    sender = "sender@example.com"
    recipient = "recipient@example.com"
    subject = "Test Subject"
    body = "Line1\nLine2\nLine3\nLine4"  # 4 lines to trigger the 4-segment split

    mime_message = create_email_with_inline_images_and_attachments(
        sender, recipient, subject, body, image_paths, attachment_paths
    )
    
    # Check that the returned message is a MIMEMultipart and contains the expected headers.
    assert isinstance(mime_message, MIMEMultipart)
    assert mime_message['From'] == sender
    assert mime_message['To'] == recipient
    assert mime_message['Subject'] == subject
    
    # The outer payload should include at least one attachment part (the PDF)
    payload = mime_message.get_payload()
    attachment_found = False
    for part in payload:
        # Attachments typically have a 'Content-Disposition' header with "attachment".
        if part.get("Content-Disposition", "").strip().startswith("attachment"):
            attachment_found = True
            break
    assert attachment_found, "Attachment not found in the MIME message."
