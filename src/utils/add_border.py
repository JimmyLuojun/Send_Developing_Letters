# File: src/utils/add_border.py

from PIL import Image, ImageOps
import os

def add_uniform_border(input_path, output_path, border_size=20, border_color=(255, 255, 255)):
    """
    Adds a fixed border around the image without resizing or cropping.
    border_size: the thickness in pixels of the border.
    border_color: an (R, G, B) tuple for the border color (white by default).
    """
    with Image.open(input_path) as img:
        # Convert image to RGB if needed (JPEG doesn't support transparency)
        if img.mode != "RGB":
            img = img.convert("RGB")
        
        # Use ImageOps.expand to add a uniform border
        bordered_img = ImageOps.expand(img, border=border_size, fill=border_color)
        bordered_img.save(output_path)

if __name__ == "__main__":
    # Update these paths to your actual directories
    input_dir = "/Users/junluo/Documents/Send_Developing_Letters/data/raw/images"
    output_dir = "/Users/junluo/Documents/Send_Developing_Letters/data/raw/image_unified"
    border_size = 20

    # Check if the input directory exists; if not, print an error message and exit.
    if not os.path.exists(input_dir):
        print(f"Input directory '{input_dir}' not found. Please create it and add images.")
        exit(1)

    os.makedirs(output_dir, exist_ok=True)

    for filename in os.listdir(input_dir):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, filename)
            add_uniform_border(input_path, output_path, border_size=border_size, border_color=(255,255,255))

