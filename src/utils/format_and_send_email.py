# src/utils/format_and_send_email.py
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email import encoders
import os
import pathlib
import re

# Get the project root directory
PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent

def format_email_subject(subject):
    return f"Cooperation Opportunity: {subject}"

def format_email_body(body):
    return f"Dear Sir/Madam,\n\n{body}\n\nBest regards,\nYour Company"  # Replace Your Company as needed

def extract_keywords_from_filename(filename):
    """Extract keywords from image filenames for relevance scoring."""
    base = pathlib.Path(filename).stem  # Get filename without extension
    base = re.sub(r'^[\d\.\s]+', '', base)  # Remove leading numbers, dots, spaces
    base = base.replace('_', ' ')  # Replace underscores with spaces
    keywords = set(base.lower().split())  # Split into words, lowercase, and create a set
    return keywords

def select_relevant_images(email_body, company_name):
    """Selects up to 3 relevant images based on filename keywords and email content."""
    images_folder = PROJECT_ROOT / "data" / "raw" / "images"  # Use PROJECT_ROOT
    candidate_images = list(images_folder.glob("*.jpg")) + list(images_folder.glob("*.png"))
    
    if not candidate_images:
        logging.warning("No candidate images found in the images folder.")
        return []

    context_text = f"{email_body} {company_name}".lower()
    context_words = set(re.findall(r'\w+', context_text))

    image_scores = []
    for img in candidate_images:
        keywords = extract_keywords_from_filename(str(img))
        score = len(keywords.intersection(context_words))
        image_scores.append((img, score))

    image_scores.sort(key=lambda x: x[1], reverse=True)  # Sort by score (descending)
    selected = [str(img) for img, _ in image_scores[:3]]  # Select top 3

    if len(selected) < 3:
        for img in candidate_images:
            if str(img) not in selected:
                selected.append(str(img))
            if len(selected) == 3:
                break
    return selected

def create_email_with_inline_images_and_attachments(
    sender, recipient, subject, body, image_paths, attachment_paths
):
    """
    Create a MIME email message by splitting the body into segments
    and inserting inline images between the segments.
    Additionally, attach any files specified in 'attachment_paths'.
    """
    # Top-level container: 'mixed' for attachments + inline images.
    outer_message = MIMEMultipart('mixed')
    outer_message['From'] = sender
    outer_message['To'] = recipient
    outer_message['Subject'] = subject

    # A 'related' container for inline images + HTML content.
    related_part = MIMEMultipart('related')
    outer_message.attach(related_part)

    # Inside 'related', an 'alternative' part for HTML content.
    msg_alternative = MIMEMultipart('alternative')
    related_part.attach(msg_alternative)

    # Build the HTML body by splitting into sections.
    sections = body.split('\n')
    if len(sections) < 4:
        segments = []
        for i, sec in enumerate(sections):
            segments.append(f'<p style="text-align:justify;">{sec}</p>')
            if i < 3:
                segments.append(f'''
                <div style="text-align:center; margin: 20px 0;">
                  <img src="cid:image{i+1}" style="max-width:600px;"/>
                </div>
                ''')
        html_body = "".join(segments)
    else:
        total_sections = len(sections)
        part_length = total_sections // 4
        seg1 = "\n".join(sections[:part_length])
        seg2 = "\n".join(sections[part_length:2*part_length])
        seg3 = "\n".join(sections[2*part_length:3*part_length])
        seg4 = "\n".join(sections[3*part_length:])
        html_body = f"""
        <p style="text-align:justify;">{seg1}</p>
        <div style="text-align:center; margin: 20px 0;">
          <img src="cid:image1" style="max-width:600px;"/>
        </div>

        <p style="text-align:justify;">{seg2}</p>
        <div style="text-align:center; margin: 20px 0;">
          <img src="cid:image2" style="max-width:600px;"/>
        </div>

        <p style="text-align:justify;">{seg3}</p>
        <div style="text-align:center; margin: 20px 0;">
          <img src="cid:image3" style="max-width:600px;"/>
        </div>

        <p style="text-align:justify;">{seg4}</p>
        """
    msg_alternative.attach(MIMEText(html_body, 'html'))

    # Attach inline images.
    for idx, image_path in enumerate(image_paths, start=1):
        try:
            with open(image_path, 'rb') as f:
                img_data = f.read()
            image = MIMEImage(img_data)
            image.add_header('Content-ID', f'<image{idx}>')
            related_part.attach(image)
        except Exception as e:
            logging.error(f"Error attaching inline image {image_path}: {e}")

    # Attach additional files.
    for file_path in attachment_paths:
        if not os.path.isfile(file_path):
            logging.warning(f"Attachment file not found: {file_path}")
            continue
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
            mime_base = MIMEBase('application', 'octet-stream')
            mime_base.set_payload(file_data)
            encoders.encode_base64(mime_base)
            filename = pathlib.Path(file_path).name
            mime_base.add_header('Content-Disposition', f'attachment; filename="{filename}"')
            outer_message.attach(mime_base)
        except Exception as e:
            logging.error(f"Error attaching file {file_path}: {e}")

    return outer_message

def format_and_send_email(recipient, subject, body, attachments=None):
    """Formats and sends an email. Includes error handling."""
    if attachments is None:
        attachments = []

    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 587))

    if not all([sender_email, sender_password, smtp_server, recipient]):
        print("Error: Missing email configuration. Check .env file.")
        return

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient
    msg['Subject'] = format_email_subject(subject)

    msg.attach(MIMEText(format_email_body(body), 'plain'))

    for file in attachments:
        try:
            with open(file, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename={os.path.basename(file)}")
            msg.attach(part)
        except FileNotFoundError:
            print(f"Error: Attachment file not found: {file}")
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
