# tests/email_handler/test_formatter.py
import pytest
import logging
from pathlib import Path
from email.message import Message
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication

# Assuming src layout and running with poetry run pytest
from src.email_handler.formatter import create_mime_email

# --- Test Data ---
SENDER = "sender@example.com"
TO = "recipient@example.com"
SUBJECT = "Test Email Subject"
BODY_HTML = """
<html>
  <head></head>
  <body>
    <p>Hello there!</p>
    <p>Check out this image:</p>
    <img src="cid:image0">
    <p>And another one:</p>
    <img src="cid:image1">
  </body>
</html>
"""

# --- Fixtures ---

@pytest.fixture
def image_files(tmp_path):
    """Create dummy image files for testing."""
    img_dir = tmp_path / "images"
    img_dir.mkdir()
    img1 = img_dir / "logo.png"
    img1.write_text("dummy png data", encoding="utf-8")
    img2 = img_dir / "photo.jpg"
    img2.write_text("dummy jpg data", encoding="utf-8")
    return [img1, img2]

@pytest.fixture
def attachment_files(tmp_path):
    """Create dummy attachment files for testing."""
    att_dir = tmp_path / "attachments"
    att_dir.mkdir()
    att1 = att_dir / "report.pdf"
    att1.write_text("dummy pdf data", encoding="utf-8")
    att2 = att_dir / "data.xlsx"
    att2.write_text("dummy xlsx data", encoding="utf-8")
    return [att1, att2]

# --- Test Cases ---

def test_create_mime_email_basic():
    """Test creating a simple HTML email with no attachments or inline images."""
    message = create_mime_email(SENDER, TO, SUBJECT, BODY_HTML)

    assert isinstance(message, MIMEMultipart)
    assert message['From'] == SENDER
    assert message['To'] == TO
    assert message['Subject'] == SUBJECT
    assert message.is_multipart()
    assert message.get_content_type() == 'multipart/related' # Always 'related' in current impl

    payload = message.get_payload()
    assert len(payload) == 1 # Only the HTML part
    assert isinstance(payload[0], MIMEText)
    assert payload[0].get_content_type() == 'text/html'
    # Decode payload carefully if needed, check content
    # For simplicity, we trust MIMEText handles it here.

def test_create_mime_email_with_inline_images(image_files):
    """Test creating an email with inline images."""
    message = create_mime_email(SENDER, TO, SUBJECT, BODY_HTML, inline_image_paths=image_files)

    assert message.is_multipart()
    payload = message.get_payload()
    assert len(payload) == 3 # HTML part + 2 image parts

    html_part = payload[0]
    img_parts = payload[1:]

    assert isinstance(html_part, MIMEText)

    assert len(img_parts) == 2
    for i, part in enumerate(img_parts):
        assert isinstance(part, MIMEImage)
        assert part['Content-Disposition'].startswith('inline')
        assert f'filename="{image_files[i].name}"' in part['Content-Disposition']
        assert part['Content-ID'] == f'<image{i}>' # Check Content-ID format
        # Ensure filename matches
        retrieved_filename = part.get_filename()
        assert retrieved_filename == image_files[i].name


def test_create_mime_email_with_attachments(attachment_files):
    """Test creating an email with attachments."""
    message = create_mime_email(SENDER, TO, SUBJECT, BODY_HTML, attachment_paths=attachment_files)

    assert message.is_multipart()
    payload = message.get_payload()
    assert len(payload) == 3 # HTML part + 2 attachment parts

    html_part = payload[0]
    att_parts = payload[1:]

    assert isinstance(html_part, MIMEText)

    assert len(att_parts) == 2
    for i, part in enumerate(att_parts):
        assert isinstance(part, MIMEApplication)
        assert part['Content-Disposition'].startswith('attachment')
        assert f'filename="{attachment_files[i].name}"' in part['Content-Disposition']
        # Ensure filename matches
        retrieved_filename = part.get_filename()
        assert retrieved_filename == attachment_files[i].name


def test_create_mime_email_with_both(image_files, attachment_files):
    """Test creating an email with both inline images and attachments."""
    message = create_mime_email(
        SENDER, TO, SUBJECT, BODY_HTML,
        inline_image_paths=image_files,
        attachment_paths=attachment_files
    )

    assert message.is_multipart()
    payload = message.get_payload()
    # Order matters: HTML, then inline images, then attachments based on code
    assert len(payload) == 1 + len(image_files) + len(attachment_files)

    assert isinstance(payload[0], MIMEText)
    # Check inline images (indices 1, 2)
    assert isinstance(payload[1], MIMEImage)
    assert payload[1]['Content-ID'] == '<image0>'
    assert isinstance(payload[2], MIMEImage)
    assert payload[2]['Content-ID'] == '<image1>'
    # Check attachments (indices 3, 4)
    assert isinstance(payload[3], MIMEApplication)
    assert f'filename="{attachment_files[0].name}"' in payload[3]['Content-Disposition']
    assert isinstance(payload[4], MIMEApplication)
    assert f'filename="{attachment_files[1].name}"' in payload[4]['Content-Disposition']

def test_create_mime_email_missing_inline_image(caplog, image_files):
    """Test handling of a non-existent inline image file."""
    missing_path = Path("non_existent_image.jpg")
    paths = [image_files[0], missing_path]

    with caplog.at_level(logging.WARNING):
        message = create_mime_email(SENDER, TO, SUBJECT, BODY_HTML, inline_image_paths=paths)

    assert "Inline image file not found, skipping: non_existent_image.jpg" in caplog.text
    payload = message.get_payload()
    assert len(payload) == 2 # HTML + 1 valid image
    assert isinstance(payload[1], MIMEImage)
    assert payload[1]['Content-ID'] == '<image0>' # Only the first image was added

def test_create_mime_email_missing_attachment(caplog, attachment_files):
    """Test handling of a non-existent attachment file."""
    missing_path = Path("non_existent_attachment.doc")
    paths = [attachment_files[0], missing_path]

    with caplog.at_level(logging.WARNING):
        message = create_mime_email(SENDER, TO, SUBJECT, BODY_HTML, attachment_paths=paths)

    assert "Attachment file not found, skipping: non_existent_attachment.doc" in caplog.text
    payload = message.get_payload()
    assert len(payload) == 2 # HTML + 1 valid attachment
    assert isinstance(payload[1], MIMEApplication)
    assert f'filename="{attachment_files[0].name}"' in payload[1]['Content-Disposition']

# Optional: Test error during file read (more complex mocking)
# from unittest.mock import patch, mock_open
# def test_create_mime_email_inline_image_read_error(caplog, image_files):
#     """Test handling errors during inline image file reading."""
#     faulty_path = image_files[0]
#     mock_file = mock_open(read_data=b"")
#     mock_file.side_effect = IOError("Disk read error") # Simulate read error
#
#     with caplog.at_level(logging.ERROR):
#         # Patch 'open' within the formatter module's scope
#         with patch('src.email_handler.formatter.open', mock_file):
#             message = create_mime_email(SENDER, TO, SUBJECT, BODY_HTML, inline_image_paths=[faulty_path])
#
#     assert f"Error attaching inline image {faulty_path}: Disk read error" in caplog.text
#     payload = message.get_payload()
#     assert len(payload) == 1 # Only HTML part, image failed 