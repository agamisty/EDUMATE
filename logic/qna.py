import os
import streamlit as st

os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "1000"
from transformers import pipeline


@st.cache_resource
def get_doc_qa():
    return pipeline("question-answering", model="deepset/tinyroberta-squad2")

doc_qa = get_doc_qa()

@st.cache_resource
def get_general_qa():
    return pipeline("text2text-generation", model="google/flan-t5-small")

general_qa = get_general_qa()


def ask_about_document(question, context):
    if not question or not context:
        return "Provide both question and document text."

    try:
        result = doc_qa(question=question, context=context)
        return result["answer"]
    except Exception as e:
        return f"Document QA failed: {str(e)}"


def ask_general_question(question):
    if not question.strip():
        return "Question cannot be empty."

    try:
        result = general_qa(question, max_length=256)
        return result[0]["generated_text"]
    except Exception as e:
        return f"General QA failed: {str(e)}"
