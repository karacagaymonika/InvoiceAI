from pathlib import Path

import streamlit as st

from extractor import extract_invoice_fields, extract_line_items
from ocr import extract_text_from_pdf


st.title("Invoice Processing AI")
st.write(
    "Upload an invoice PDF. The app will extract text, key invoice fields, "
    "and product line data for inventory tracking."
)


BASE_DIR = Path(__file__).parent
INVOICES_DIR = BASE_DIR / "invoices"
INVOICES_DIR.mkdir(exist_ok=True)


uploaded_file = st.file_uploader(
    "Upload Invoice",
    type=["pdf"]
)


if uploaded_file:
    file_path = INVOICES_DIR / uploaded_file.name

    with open(file_path, "wb") as file:
        file.write(uploaded_file.getbuffer())

    st.success(f"Uploaded and saved: {uploaded_file.name}")

    try:
        extracted_text = extract_text_from_pdf(file_path)

        st.subheader("Extracted Invoice Text")

        st.text_area(
            "Extracted text",
            extracted_text,
            height=300
        )

        st.subheader("Structured Invoice Fields")

        extracted_fields = extract_invoice_fields(extracted_text)

        st.table(
            [
                {"Field": key, "Extracted Value": value}
                for key, value in extracted_fields.items()
            ]
        )

        st.subheader("Extracted Product Lines")

        line_items = extract_line_items(extracted_text)

        if line_items:
            st.dataframe(
                line_items,
                use_container_width=True
            )
        else:
            st.warning(
                "No product lines found yet. We will improve this extraction rule."
            )

        st.success("Extraction completed.")

    except Exception as error:
        st.error("Something went wrong while extracting invoice data.")
        st.exception(error)
else:
    st.warning("Please upload a PDF invoice to begin.")