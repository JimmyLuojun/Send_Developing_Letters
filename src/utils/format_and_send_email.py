#/Users/junluo/Documents/Send_Developing_Letters/src/utils/format_and_send_email.py
# format_and_send_email.py

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os

def format_email_subject(subject):
    return f"Cooperation Opportunity: {subject}"

def format_email_body(body):
    return f"Dear Sir/Madam,\n\n{body}\n\nBest regards,\nYour Company"

def format_and_send_email(recipient, subject, body, attachments=None):
    if attachments is None:
        attachments = []

    sender_email = "your_email@example.com"  # Replace with real sender email
    sender_password = "your_password"        # Replace with real sender password
    smtp_server = "smtp.example.com"         # Replace with real SMTP server
    smtp_port = 587                          # Common port for TLS

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient
    msg['Subject'] = format_email_subject(subject)

    msg.attach(MIMEText(format_email_body(body), 'plain'))

    for file in attachments:
        with open(file, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename={os.path.basename(file)}")
        msg.attach(part)

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient, msg.as_string())
        print(f"Email sent to {recipient} successfully.")
    except Exception as e:
        print(f"Failed to send email to {recipient}: {e}")


if __name__ == "__main__":
    format_and_send_email(
        "contact@example.com",
        "Skyfend Partnership",
        "We are interested in exploring a partnership with your company.",
        ["path/to/image.jpg"]
    )
