from pathlib import Path

import streamlit as st

from ocr import extract_text_from_pdf


# -----------------------------
# Page configuration
# -----------------------------
st.set_page_config(
    page_title="Invoice Processing AI",
    page_icon="📄",
    layout="wide"
)


# -----------------------------
# Folder setup
# -----------------------------
BASE_DIR = Path(__file__).parent
INVOICES_DIR = BASE_DIR / "invoices"

INVOICES_DIR.mkdir(exist_ok=True)


# -----------------------------
# App title
# -----------------------------
st.title("📄 Invoice Processing AI")
st.write("Upload an invoice PDF. The app will save it and extract readable text.")


# -----------------------------
# File uploader
# -----------------------------
uploaded_file = st.file_uploader(
    "Upload Invoice",
    type=["pdf"]
)


# -----------------------------
# Save uploaded invoice and extract text
# -----------------------------
if uploaded_file is not None:
    file_path = INVOICES_DIR / uploaded_file.name

    with open(file_path, "wb") as file:
        file.write(uploaded_file.getbuffer())

    file_size_kb = round(uploaded_file.size / 1024, 2)

    st.success("Invoice uploaded and saved successfully!")

    st.subheader("Uploaded File Details")
    st.write(f"**File name:** {uploaded_file.name}")
    st.write(f"**File size:** {file_size_kb} KB")
    st.write(f"**Saved location:** `{file_path}`")

    st.divider()

    st.subheader("Extracted Invoice Text")

    extracted_text = extract_text_from_pdf(file_path)

    st.text_area(
        "Extracted text",
        extracted_text,
        height=400
    )

    if "No readable text found" in extracted_text:
        st.warning(
            "This looks like a scanned/image invoice. We will add OCR support next."
        )
    else:
        st.success("Text extracted successfully.")
else:
    st.warning("Please upload a PDF invoice to begin.")
    