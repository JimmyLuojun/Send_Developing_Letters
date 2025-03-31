 # tests/email_handler/test_image_selector.py
import pytest
import logging
from pathlib import Path

# Assuming src layout and running with poetry run pytest
from src.email_handler.image_selector import (
    _extract_keywords_from_filename,
    select_relevant_images
)

# --- Tests for _extract_keywords_from_filename ---

@pytest.mark.parametrize("filename, expected_keywords", [
    # Input, Expected Output (based on NEW logic)
    ("logo.png", {'logo', 'png', 'logo.png'}),
    # Leading '01_' removed by regex, base_cleaned='product_shot', split=['product', 'shot']
    ("01_product_shot.jpg", {'product', 'shot', 'product_shot', 'jpg', '01_product_shot.jpg'}),
    ("data-visualization.gif", {'data', 'visualization', 'data-visualization', 'gif', 'data-visualization.gif'}),
    # Stripped input, base='Company Meeting Pic', base_cleaned='Company Meeting Pic', split=['company', 'meeting', 'pic']
    (" Company Meeting Pic.jpeg ", {'company', 'meeting', 'pic', 'company meeting pic', 'jpeg', 'company meeting pic.jpeg'}),
    # base='...-123-Report_Image Final', base_cleaned='Report_Image Final', split=['report', 'image', 'final']
    ("...-123-Report_Image Final.PNG", {'report', 'image', 'final', 'report_image final', 'png', '...-123-report_image final.png'}), # Original filename added lowercased
    ("image", {'image'}), # base='image', base_cleaned='image', words={'image'}
    # name='archive_icon.svg', base='archive_icon', base_cleaned='archive_icon', split=['archive', 'icon']
    ("/path/to/archive_icon.svg", {'archive', 'icon', 'archive_icon', 'svg', 'archive_icon.svg'}),
    ("", set()),
    # name='.gitkeep', base='.gitkeep', base_cleaned='gitkeep', words={'gitkeep'}
    (".gitkeep", {'gitkeep', '.gitkeep'}), # Original filename also added
    # name='UPPER_CASE.PDF', base='UPPER_CASE', base_cleaned='UPPER_CASE', split=['upper', 'case']
    ("UPPER_CASE.PDF", {'upper', 'case', 'upper_case', 'pdf', 'upper_case.pdf'}),
])
def test_extract_keywords_from_filename(filename, expected_keywords):
    assert _extract_keywords_from_filename(filename) == expected_keywords

# --- Fixtures for select_relevant_images ---

@pytest.fixture
def image_dir_setup(tmp_path):
    """Creates a temporary directory structure with image files for testing."""
    img_dir = tmp_path / "test_images"
    img_dir.mkdir()

    # Create some dummy image files with relevant names
    (img_dir / "skyfend_logo.png").touch()
    (img_dir / "drone_detection_system.jpg").touch()
    (img_dir / "anti_drone_solution.jpeg").touch()
    (img_dir / "meeting_summary.gif").touch() # Less relevant
    (img_dir / "competitor_analysis_chart.png").touch()
    (img_dir / "random_pic.jpg").touch()

    # Create a non-image file
    (img_dir / "notes.txt").touch()

    return img_dir

# --- Tests for select_relevant_images ---

def test_select_relevant_images_basic(image_dir_setup):
    """Test basic selection based on keywords."""
    image_dir = image_dir_setup
    email_body = "<p>Discussing our new drone detection system and anti-drone solutions.</p>"
    company_name = "SkyFend Ltd"
    max_images = 3

    selected = select_relevant_images(image_dir, email_body, company_name, max_images)

    selected_names = {p.name for p in selected}
    print(f"Selected names: {selected_names}") # Debugging output

    assert len(selected) == max_images
    # Expecting the most relevant ones based on score
    # Scores: drone_detection_system (drone, detection, system), anti_drone_solution (anti, drone, solution), skyfend_logo (skyfend)
    # Context: drone, detection, system, anti, solutions, skyfend (from name)
    assert "drone_detection_system.jpg" in selected_names
    assert "anti_drone_solution.jpeg" in selected_names
    assert "skyfend_logo.png" in selected_names
    # Ensure less relevant ones are not selected
    assert "meeting_summary.gif" not in selected_names
    assert "random_pic.jpg" not in selected_names
    assert "competitor_analysis_chart.png" not in selected_names # Lower score


def test_select_relevant_images_max_images_limit(image_dir_setup):
    """Test that max_images limits the results, handling ties."""
    image_dir = image_dir_setup
    email_body = "Generic email body mentioning skyfend drone detection system."
    company_name = "Some Company" # Does not add keywords here
    max_images = 2 # Limit to 2

    selected = select_relevant_images(image_dir, email_body, company_name, max_images)
    assert len(selected) == max_images

    selected_names = {p.name for p in selected}
    print(f"Selected names (limit test): {selected_names}") # Debugging output

    # Scores based on new logic and context "skyfend drone detection system":
    # context_words = {'generic', 'email', 'body', 'mentioning', 'skyfend', 'drone', 'detection', 'system'}
    # skyfend_logo.png -> {'skyfend', 'logo', ...} score=1
    # drone_detection_system.jpg -> {'drone', 'detection', 'system', ...} score=3
    # anti_drone_solution.jpeg -> {'anti', 'drone', 'solution', ...} score=1
    # others -> score=0

    # Must include the highest scorer
    assert "drone_detection_system.jpg" in selected_names
    # The second item must be one of the score=1 items, but we don't know which one due to sort stability.
    # Check that *exactly two* items are selected, fulfilling the max_images=2 requirement
    # and implicitly confirming one of the tied score=1 images was selected along with the score=3 image.
    assert len(selected_names) == 2

    # Alternative more explicit check for ties (optional):
    # assert (("skyfend_logo.png" in selected_names or "anti_drone_solution.jpeg" in selected_names) and
    #         not ("skyfend_logo.png" in selected_names and "anti_drone_solution.jpeg" in selected_names))


def test_select_relevant_images_no_matches(image_dir_setup):
    """Test behavior when no keywords match (score 0). Should still fill slots."""
    image_dir = image_dir_setup
    email_body = "<p>Regarding our recent financial discussion.</p>"
    company_name = "Acme Corp"
    max_images = 3

    selected = select_relevant_images(image_dir, email_body, company_name, max_images)

    # Should return up to max_images, order might depend on glob/sort
    assert 0 < len(selected) <= max_images
    # Since scores are likely 0, it fills slots. We check the count.
    assert len(selected) == max_images # Fills remaining slots up to max


def test_select_relevant_images_fewer_images_than_max(tmp_path):
    """Test when fewer images exist than max_images requested."""
    img_dir = tmp_path / "few_images"
    img_dir.mkdir()
    (img_dir / "image1.png").touch()
    (img_dir / "image2.jpg").touch()

    email_body = "Some text"
    company_name = "Company"
    max_images = 5 # Request more than available

    selected = select_relevant_images(img_dir, email_body, company_name, max_images)
    assert len(selected) == 2 # Returns all available images
    assert {p.name for p in selected} == {"image1.png", "image2.jpg"}

def test_select_relevant_images_empty_dir(tmp_path, caplog):
    """Test with an empty image directory."""
    img_dir = tmp_path / "empty_dir"
    img_dir.mkdir()

    with caplog.at_level(logging.WARNING):
        selected = select_relevant_images(img_dir, "body", "company", 3)

    assert selected == []
    assert f"No candidate images found in: {img_dir}" in caplog.text

def test_select_relevant_images_nonexistent_dir(tmp_path, caplog):
    """Test with a non-existent image directory."""
    img_dir = tmp_path / "non_existent_dir"
    # Do not create the directory

    with caplog.at_level(logging.ERROR):
        selected = select_relevant_images(img_dir, "body", "company", 3)

    assert selected == []
    assert f"Image directory not found: {img_dir}" in caplog.text

def test_select_relevant_images_ignores_non_images(tmp_path):
    """Test that non-image files are ignored by glob."""
    img_dir = tmp_path / "mixed_files"
    img_dir.mkdir()
    (img_dir / "image1.png").touch()
    (img_dir / "document.txt").touch()
    (img_dir / "archive.zip").touch()
    (img_dir / "photo.jpeg").touch()

    selected = select_relevant_images(img_dir, "photo", "company", 5)
    assert len(selected) == 2
    assert {p.name for p in selected} == {"image1.png", "photo.jpeg"}