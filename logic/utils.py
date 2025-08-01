import pdfplumber
import pytesseract
from PIL import Image


def extract_text_from_pdf(pdf_file):     # sourcery skip: use-named-expression

    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()


def extract_text_from_image(image_file):

    image = Image.open(image_file)
    text = pytesseract.image_to_string(image)
    return text.strip()
