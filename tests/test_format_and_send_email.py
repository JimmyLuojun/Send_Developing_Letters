# tests/test_format_and_send_email.py

import pytest
from src.utils.format_and_send_email import format_email_subject, format_email_body, format_and_send_email
from unittest.mock import patch, MagicMock
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase


def test_format_email_subject():
    subject = "Test Subject"
    formatted_subject = format_email_subject(subject)
    assert formatted_subject == "Cooperation Opportunity: Test Subject"

def test_format_email_body():
    body = "This is a test body."
    formatted_body = format_email_body(body)
    assert "Dear Sir/Madam," in formatted_body
    assert body in formatted_body
    assert "Best regards," in formatted_body
    assert "Your Company" in formatted_body  # Replace with your actual company name

@patch('smtplib.SMTP')
def test_format_and_send_email_success(mock_smtp):
    # Create mock objects for SMTP and its methods
    mock_smtp_instance = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_smtp_instance

    # Call the function
    recipient = "recipient@example.com"
    subject = "Test Subject"
    body = "Test Body"
    format_and_send_email(recipient, subject, body)

    # Assertions
    mock_smtp.assert_called_once()  # Check that SMTP was instantiated
    mock_smtp_instance.starttls.assert_called_once()
    mock_smtp_instance.login.assert_called_once()
    mock_smtp_instance.sendmail.assert_called_once()
    mock_smtp_instance.quit.assert_not_called()  # Make sure quit is NOT called when using context manager

@patch('smtplib.SMTP')
def test_format_and_send_email_failure(mock_smtp):
     # Set up the mock to raise an exception
    mock_smtp_instance = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_smtp_instance
    mock_smtp_instance.sendmail.side_effect = Exception("Simulated SMTP Error")

    recipient = "recipient@example.com"
    subject = "Test Subject"
    body = "Test Body"

    # Call the function - exception should be caught internally
    format_and_send_email(recipient, subject, body)
    mock_smtp_instance.sendmail.assert_called_once()

@patch('smtplib.SMTP')
def test_format_and_send_email_with_attachments(mock_smtp, tmp_path):
    # Create a mock SMTP instance
    mock_smtp_instance = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_smtp_instance

    # Create a temporary file for attachment testing
    attachment_file = tmp_path / "test_attachment.txt"
    attachment_file.write_text("This is a test attachment.")

    # Call the function with attachments
    recipient = "recipient@example.com"
    subject = "Test Subject"
    body = "Test Body"
    attachments = [str(attachment_file)]
    format_and_send_email(recipient, subject, body, attachments)

     # Assertions to check if sendmail was called.
    mock_smtp.assert_called()
    mock_smtp_instance.sendmail.assert_called()
    mock_smtp_instance.starttls.assert_called()