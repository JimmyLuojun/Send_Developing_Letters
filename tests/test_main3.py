import pathlib
import pandas as pd
import pytest
import src.main3 as main3

@pytest.fixture
def temp_environment_main3(tmp_path, monkeypatch):
    """
    Sets up a temporary project structure for main3.py:
      - A dummy raw Excel file with one valid record.
      - A dummy Skyfend business document.
      - A folder for images with dummy image files.
      - A processed folder for the output Excel file.
      - A logs folder.
    Also patches global variables and external function calls so main3.py uses the temporary data.
    """
    # Create a temporary project root directory.
    base_dir = tmp_path / "Send_Developing_Letters"
    base_dir.mkdir()

    # Create data/raw folder and a dummy Excel file.
    raw_dir = base_dir / "data" / "raw"
    raw_dir.mkdir(parents=True)
    test_excel_path = raw_dir / "test_to_read_website.xlsx"
    df = pd.DataFrame({
        "company": ["Test Company"],
        "recipient_email": ["recipient@example.com"],
        "website": ["http://example.com"],
        "contact person": ["Test Contact"]
    })
    df.to_excel(test_excel_path, index=False)

    # Create a dummy Skyfend business document.
    business_doc_path = raw_dir / "test_main Business of Skyfend.docx"
    business_doc_path.write_text("Dummy skyfend business content")

    # Create data/raw/images folder with dummy image files.
    images_dir = raw_dir / "images"
    images_dir.mkdir()
    image_filenames = [
        "1.2solution for airport security_C.png",
        "1.3 solution for event security.png",
        "1.4 solution for energe security.png",
        "1.5soluiton for VIPs security.png",
        "1.products of skyfend.jpg"
    ]
    for fname in image_filenames:
        (images_dir / fname).write_bytes(b"dummy image data")

    # Create data/processed folder for the output Excel file.
    processed_dir = base_dir / "data" / "processed"
    processed_dir.mkdir(parents=True)
    processed_excel_path = processed_dir / "saving_company_data_after_creating_letters.xlsx"

    # Create a logs folder.
    logs_dir = base_dir / "logs"
    logs_dir.mkdir(parents=True)

    # Patch global paths in main3.py using monkeypatch.setitem.
    monkeypatch.setitem(main3.__dict__, "PROJECT_ROOT", base_dir)
    monkeypatch.setitem(main3.__dict__, "RAW_EXCEL_PATH", test_excel_path)
    monkeypatch.setitem(main3.__dict__, "SKYFEND_BUSINESS_DOC_PATH", business_doc_path)
    monkeypatch.setitem(main3.__dict__, "PROCESSED_EXCEL_PATH", processed_excel_path)

    # Patch external function calls to avoid real network/API calls.
    # If get_website_content is not present, add it.
    if not hasattr(main3, "get_website_content"):
        monkeypatch.setitem(main3.__dict__, "get_website_content",
                              lambda url, max_content_length=2000: "Dummy website content")
    else:
        monkeypatch.setattr(main3, "get_website_content",
                            lambda url, max_content_length=2000: "Dummy website content")

    monkeypatch.setattr(main3, "extract_main_business", lambda api, content: "Dummy main business")
    monkeypatch.setattr(main3, "identify_cooperation_points", lambda api, sb, mb: "Dummy cooperation points")
    monkeypatch.setattr(main3, "generate_developing_letter",
                        lambda api, prompt, cp, comp, contact: "Dummy email body")
    monkeypatch.setattr(main3, "read_skyfend_business", lambda path: "Dummy skyfend business")
    monkeypatch.setattr(main3, "save_email_to_drafts", lambda *args, **kwargs: "dummy_draft_id")

    return base_dir, processed_excel_path, images_dir

def read_processed_excel(processed_excel_path):
    """Helper: returns a DataFrame if the processed Excel exists; otherwise, an empty DataFrame."""
    if processed_excel_path.exists():
        return pd.read_excel(processed_excel_path)
    return pd.DataFrame()

def test_main3_valid_record(temp_environment_main3):
    """
    Test that main3.main() processes a valid record, creates an email draft,
    and writes the expected record to the processed Excel file.
    """
    base_dir, processed_excel_path, images_dir = temp_environment_main3
    try:
        main3.main()
    except Exception as e:
        pytest.fail(f"main3.main() raised an exception: {e}")

    df = read_processed_excel(processed_excel_path)
    assert not df.empty, "Processed Excel file should not be empty."
    assert df.iloc[0]['company'] == "Test Company"

def test_main3_inline_images_selection(temp_environment_main3):
    """
    Test the select_relevant_images() function returns exactly 3 images
    and that each selected image file exists.
    """
    base_dir, processed_excel_path, images_dir = temp_environment_main3
    dummy_email_body = "This email discusses airport security and event security measures."
    dummy_company = "Test Company"
    selected_images = main3.select_relevant_images(dummy_email_body, dummy_company)
    assert len(selected_images) == 3, f"Expected 3 images, got {len(selected_images)}"
    for img in selected_images:
        assert pathlib.Path(img).exists(), f"Selected image {img} does not exist."

def test_main3_email_mime_creation(temp_environment_main3):
    """
    Test that create_email_with_inline_images() creates a MIME message whose HTML
    body contains the expected inline image Content-ID tags.
    """
    base_dir, processed_excel_path, images_dir = temp_environment_main3
    sender = "sender@example.com"
    recipient = "recipient@example.com"
    subject = "Test Subject"
    # Sample body with several lines.
    body = "Line1\nLine2\nLine3\nLine4\nLine5\nLine6"
    # Select three dummy images from images_dir.
    image_files = list(images_dir.glob("*.png")) + list(images_dir.glob("*.jpg"))
    assert len(image_files) >= 3, "Not enough images in the test environment."
    selected_images = [str(image_files[i]) for i in range(3)]
    mime_message = main3.create_email_with_inline_images(sender, recipient, subject, body, selected_images)
    message_str = mime_message.as_string()
    # Verify that Content-ID tags for each image are present.
    for i in range(1, 4):
        cid = f"cid:image{i}"
        assert cid in message_str, f"Content-ID {cid} not found in MIME message."
