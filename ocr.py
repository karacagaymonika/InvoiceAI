from pathlib import Path

from pypdf import PdfReader


def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF file.

    This works best for digital PDFs where text is selectable.
    Scanned invoices may need OCR, which we will add later.
    """

    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        return "Error: PDF file does not exist."

    extracted_text = ""

    try:
        reader = PdfReader(str(pdf_path))

        for page_number, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text()

            if page_text:
                extracted_text += f"\n\n--- Page {page_number} ---\n"
                extracted_text += page_text

        if not extracted_text.strip():
            return "No readable text found. This may be a scanned invoice and will need OCR."

        return extracted_text.strip()

    except Exception as error:
        return f"Error extracting text: {error}"