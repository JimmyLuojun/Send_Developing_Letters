# src/utils/format_and_send_email.py
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os

def format_email_subject(subject):
    return f"Cooperation Opportunity: {subject}"

def format_email_body(body):
    return f"Dear Sir/Madam,\n\n{body}\n\nBest regards,\nYour Company"  # Replace Your Company

def format_and_send_email(recipient, subject, body, attachments=None):
    """Formats and sends an email.  Includes error handling.

    Args:
        recipient: The recipient's email address.
        subject: The email subject.
        body: The email body.
        attachments: A list of file paths to attach (optional).
    """
    if attachments is None:
        attachments = []

    sender_email = os.getenv("SENDER_EMAIL")  # Use environment variables
    sender_password = os.getenv("SENDER_PASSWORD")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 587))  # Default to 587 if not set

    # --- Input Validation ---
    if not all([sender_email, sender_password, smtp_server, recipient]):
        print("Error: Missing email configuration. Check .env file.")
        return

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient
    msg['Subject'] = format_email_subject(subject)

    msg.attach(MIMEText(format_email_body(body), 'plain'))

    for file in attachments:
        try:  # Add error handling for attachments
            with open(file, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename={os.path.basename(file)}")
            msg.attach(part)
        except FileNotFoundError:
            print(f"Error: Attachment file not found: {file}")
            #  Don't exit; continue sending the email without the attachment
        except Exception as e:
            print(f"Error attaching file {file}: {e}")
            return

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient, msg.as_string())
        print(f"Email sent to {recipient} successfully.")
    except Exception as e:
        print(f"Failed to send email to {recipient}: {e}")