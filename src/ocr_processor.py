from PIL import Image
import pytesseract
import io

def extract_text_from_image(image_file):
    try:
        # If image_file is a file-like object, open it
        if hasattr(image_file, 'read'):
            image_data = image_file.read()
            image = Image.open(io.BytesIO(image_data))
        else:
            image = image_file
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        return f"OCR Error: {str(e)}"