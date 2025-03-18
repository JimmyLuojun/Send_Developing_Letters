# tests/test_save_email_to_drafts.py
import base64
import pytest
from email.mime.text import MIMEText

from src.utils.save_email_to_drafts import create_message, save_email_to_drafts

# Dummy classes to simulate the Gmail API service.
class DummyDraft:
    def execute(self):
        return {"id": "dummy_id", "message": {"id": "dummy_message_id"}}

class DummyDrafts:
    def create(self, userId, body):
        return DummyDraft()

class DummyService:
    def users(self):
        return self
    def drafts(self):
        return DummyDrafts()

def dummy_build(serviceName, version, credentials):
    return DummyService()

@pytest.fixture(autouse=True)
def patch_build(monkeypatch):
    # Monkeypatch the build function in save_email_to_drafts module.
    monkeypatch.setattr("src.utils.save_email_to_drafts.build", dummy_build)

def test_create_message():
    sender = "sender@example.com"
    recipient = "recipient@example.com"
    subject = "Test Subject"
    body = "This is a test email."
    message_dict = create_message(sender, recipient, subject, body)
    raw_message = message_dict.get("raw")
    assert raw_message is not None
    # Check that the raw message can be decoded.
    decoded = base64.urlsafe_b64decode(raw_message.encode())
    assert b"Content-Type" in decoded

def test_save_email_to_drafts():
    # Create a dummy MIME message.
    dummy_mime = MIMEText("dummy email content", "html")
    dummy_mime["From"] = "sender@example.com"
    dummy_mime["To"] = "recipient@example.com"
    dummy_mime["Subject"] = "Test Subject"
    
    draft_id = save_email_to_drafts(mime_message=dummy_mime)
    assert draft_id is not None
