import os
import sys
from PIL import Image, ImageDraw, ImageFont
import exifread
from fractions import Fraction

# Dynamically locate the base directory (script or executable)
def get_base_dir():
    if getattr(sys, 'frozen', False):  # Running as an executable
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))  # Running as a script

# Set base paths dynamically
BASE_DIR = get_base_dir()
input_folder = os.path.join(BASE_DIR, "insta", "01_pre")
output_folder = os.path.join(BASE_DIR, "insta", "02_post")
font_folder = os.path.join(BASE_DIR, "insta", "font")

# Ensure the output folder exists
os.makedirs(output_folder, exist_ok=True)

# Get the first font in the font folder
def get_first_font(font_folder):
    try:
        fonts = [f for f in os.listdir(font_folder) if f.lower().endswith('.ttf')]
        if not fonts:
            raise FileNotFoundError(f"No .ttf font files found in '{font_folder}'.")
        return os.path.join(font_folder, fonts[0])
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

font_file = get_first_font(font_folder)

def make_square_and_add_metadata(folder_path, output_folder, font_path):
    os.makedirs(output_folder, exist_ok=True)
    total_files = len([f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
    processed_files = 0
    print(f"Total files to process: {total_files}")
    for filename in os.listdir(folder_path):
        if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            continue
        #progress bar
        processed_files += 1
        print(f"Processing file {processed_files}/{total_files}", end="\r")
        


        file_path = os.path.join(folder_path, filename)
        with Image.open(file_path) as img:
            # Create square image
            width, height = img.size
            max_side = max(width, height)
            square_img = Image.new("RGB", (max_side, max_side), (255, 255, 255))
            paste_position = ((max_side - width) // 2, (max_side - height) // 2)
            square_img.paste(img, paste_position)

            # Calculate border
            border = max_side - min(width, height)
            margin = int(border * 0.05)  # 5% of the border as margin

            # Metadata Text
            metadata = extract_metadata(file_path)
            text = format_metadata(metadata)
            draw = ImageDraw.Draw(square_img)

            # Text-Box Position (bottom left)
            max_text_width = max_side - 2 * margin
            text_x = margin -40
            text_y = max_side - margin * 4# -1 to avoid cropping the text

            # Adjust font size to fit text within the given width
            font_size = border // 34  # Start with an initial proportional font size

            while font_size > 8:  # Ensure font size doesn't go below 8
                font = ImageFont.truetype(font_path, font_size)
                lines = wrap_text(text, font, max_text_width)
                total_height = sum((font.getbbox(line)[3] - font.getbbox(line)[1] + 2) for line in lines)
                
                if len(lines) > 4:  # Adjust condition based on the number of lines
                    font_size -= 1
                elif total_height <= (max_side - 2 * margin):  # Check if it fits in the border
                    break
                else:
                    font_size -= 1

            

            # Draw text
            current_y = text_y - total_height
            for line in lines:
                draw.text((text_x, current_y), line, fill="black", font=font)
                current_y += font.getbbox(line)[3] - font.getbbox(line)[1] + 2

            # Save
            output_path = os.path.join(output_folder, f"{os.path.splitext(filename)[0]}_insta.jpg")
            square_img.save(output_path, quality=100)
            print(f"Processed and saved: {output_path}")


def extract_metadata(image_path):
    metadata = {}
    with open(image_path, 'rb') as f:
        tags = exifread.process_file(f, stop_tag="UNDEF", details=False)

        # Camera Make and Model
        make = tags.get("Image Make", "Unknown")  # Camera manufacturer
        model = tags.get("Image Model", "Unknown")  # Camera model
        metadata["Camera"] = f"{make} {model}"
                
        # Lens Make and Model
        lens_model = tags.get("EXIF LensModel", "Unknown")  # Lens model
        metadata["Lens"] = f"{lens_model}"
        print("#######")
        print(lens_model)
        # ISO
        metadata["ISO"] = tags.get("EXIF ISOSpeedRatings", "Unknown")
        
        # Aperture
        aperture_tag = tags.get("EXIF FNumber", None)
        if aperture_tag:
            try:
                aperture_value = float(Fraction(str(aperture_tag)))
                metadata["Aperture"] = f"ƒ/{str(round(aperture_value, 1))}"
            except (ValueError, TypeError):
                metadata["Aperture"] = "Unknown"
        else:
            metadata["Aperture"] = "Unknown"
        
        # Shutter Speed
        shutter_tag = tags.get("EXIF ExposureTime", None)
        metadata["ShutterSpeed"] = f"{str(shutter_tag)}s" if shutter_tag else "Unknown"
        
        # Focal Length
        focal_length_tag = tags.get("EXIF FocalLength", None)
        if focal_length_tag:
            try:
                focal_length_value = float(Fraction(str(focal_length_tag)))
                metadata["FocalLength"] = f"{str(int(focal_length_value))}mm"
            except (ValueError, TypeError):
                metadata["FocalLength"] = "Unknown"
        else:
            metadata["FocalLength"] = "Unknown"
    
    return metadata
def format_metadata(metadata):
    return (
        f"Camera: {metadata['Camera']}\n"
        f"Lens: {metadata['Lens']}\n"
        f"ISO: {metadata['ISO']}\n"
        f"Aperture: {metadata['Aperture']}\n"
        f"Shutter Speed: {metadata['ShutterSpeed']}\n"
        f"Focal Length: {metadata['FocalLength']}"
    )


def wrap_text(text, font, max_width):
    # This function wraps the text to fit within the given width
    lines = []
    words = text.split(" ")
    current_line = ""

    for word in words:
        test_line = current_line + (word if current_line == "" else " " + word)
        bbox = font.getbbox(test_line)  # Get the bounding box for the text
        width = bbox[2] - bbox[0]  # Width is the difference between right and left
        if width <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)
    
    return lines

def main():
    # Clear output folder
    for filename in os.listdir(output_folder):
        file_path = os.path.join(output_folder, filename)
        os.remove(file_path)
    make_square_and_add_metadata(input_folder, output_folder, font_file)

if __name__ == "__main__":
    main()