import pdfplumber
import pytesseract
import streamlit as st
from PIL import Image
from transformers import pipeline

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

summarizer = pipeline("summarization", model="facebook/bart-large-cnn")


def extract_text_from_pdf(uploaded_file):  # sourcery skip: use-named-expression
    text = ""
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def extract_text_from_image(uploaded_file):
    image = Image.open(uploaded_file)
    return pytesseract.image_to_string(image)


def summarize_text(text):
    if len(text.strip()) < 50:
        return "Text is too short to summarize."
    return summarizer(text, max_length=300, min_length=100, truncation=True)[0][
        "summary_text"
    ]


# sourcery skip: use-fstring-for-concatenation, use-named-expression
st.title("EduMate Document Summarizer")

uploaded_file = st.file_uploader(
    "Upload PDF or Image", type=["pdf", "png", "jpg", "jpeg"]
)

if uploaded_file:
    if uploaded_file.type == "application/pdf":
        text = extract_text_from_pdf(uploaded_file)
    else:
        text = extract_text_from_image(uploaded_file)

    if st.button("Summarize"):
        with st.spinner("Generating summary..."):
            summary = summarize_text(text)
            st.subheader("Summary")
            st.write(summary)
            st.subheader("Extracted Text")
            st.text(text[:2000] + "...")
