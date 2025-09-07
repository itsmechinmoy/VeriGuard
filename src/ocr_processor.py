from PIL import Image
import pytesseract

def extract_text_from_image(image):
    try:
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        return f"OCR Error: {str(e)}"