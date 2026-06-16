import streamlit as st

st.set_page_config(
    page_title="Invoice Processing AI",
    layout="wide"
)

st.title("📄 Invoice Processing AI")

st.write("Upload an invoice PDF to begin.")

uploaded_file = st.file_uploader(
    "Upload Invoice",
    type=["pdf"]
)

if uploaded_file:
    st.success(
        f"Uploaded: {uploaded_file.name}"
    )