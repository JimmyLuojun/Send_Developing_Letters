# tests/test_add_border.py
import os
import pytest
from PIL import Image
from src.utils.add_border import add_uniform_border

@pytest.fixture
def setup_temp_dirs(tmp_path):
    """
    Creates temporary input and output directories for testing.
    """
    input_dir = tmp_path / "input_images"
    output_dir = tmp_path / "output_images"
    input_dir.mkdir()
    output_dir.mkdir()
    return input_dir, output_dir

def create_test_image(path, size=(100, 50), color=(100, 150, 200), mode="RGB"):
    """
    Helper function to create a simple test image.
    """
    img = Image.new(mode, size, color)
    img.save(path)

def test_add_uniform_border(setup_temp_dirs):
    """
    Test that add_uniform_border adds the correct border without cropping or resizing content.
    Using PNG output to ensure lossless saving of the border color.
    """
    input_dir, output_dir = setup_temp_dirs
    
    # Create a test image in the input directory
    input_image_path = input_dir / "test.jpg"
    create_test_image(str(input_image_path), size=(100, 50), color=(100, 150, 200))
    
    # Define output path with PNG extension for lossless saving
    output_image_path = output_dir / "test_bordered.png"
    
    # Define border settings
    border_size = 10
    border_color = (255, 0, 0)  # red
    
    # Run the function
    add_uniform_border(str(input_image_path), str(output_image_path),
                       border_size=border_size, border_color=border_color)
    
    # Check the output file was created
    assert output_image_path.exists(), "Output image does not exist."
    
    # Open the output image and verify its properties
    with Image.open(output_image_path) as img:
        # Original image was 100×50, so final should be 100+2*10 by 50+2*10 → 120×70
        expected_width = 100 + 2 * border_size
        expected_height = 50 + 2 * border_size
        assert img.size == (expected_width, expected_height), (
            f"Expected {(expected_width, expected_height)}, got {img.size}"
        )
        
        # Check a corner pixel to ensure it's the border color
        top_left_pixel = img.getpixel((0, 0))
        assert top_left_pixel == border_color, (
            f"Expected border color {border_color} at top-left, got {top_left_pixel}"
        )
        
        # Optionally, check bottom-right pixel
        bottom_right_pixel = img.getpixel((img.width - 1, img.height - 1))
        assert bottom_right_pixel == border_color, (
            f"Expected border color {border_color} at bottom-right, got {bottom_right_pixel}"
        )
