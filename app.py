from pathlib import Path

import pandas as pd
import streamlit as st

from database import get_inventory_summary, get_invoices, init_db, save_invoice
from extractor import extract_invoice_fields, extract_line_items
from ocr import extract_text_from_pdf


# --------------------------------------------------
# Page setup
# --------------------------------------------------

st.set_page_config(
    page_title="Invoice Processing AI",
    page_icon="📄",
    layout="wide"
)


BASE_DIR = Path(__file__).parent
INVOICES_DIR = BASE_DIR / "invoices"
INVOICES_DIR.mkdir(exist_ok=True)

init_db()


# --------------------------------------------------
# App header
# --------------------------------------------------

st.title("📄 Invoice Processing AI + Inventory")
st.write(
    "Upload invoice PDFs, extract invoice data and product lines, "
    "then save them into a database for inventory tracking."
)

st.info(
    "Demo project using fake/test data only. Private invoices and database files are ignored by Git."
)


# --------------------------------------------------
# Helper functions for dashboard
# --------------------------------------------------

def build_inventory_dataframe():
    inventory_rows = get_inventory_summary()

    if not inventory_rows:
        return pd.DataFrame(
            columns=[
                "Product Code",
                "Product Name",
                "Unit",
                "Current Stock",
            ]
        )

    return pd.DataFrame(
        inventory_rows,
        columns=[
            "Product Code",
            "Product Name",
            "Unit",
            "Current Stock",
        ]
    )


def build_invoice_dataframe():
    invoice_rows = get_invoices()

    if not invoice_rows:
        return pd.DataFrame(
            columns=[
                "ID",
                "File Name",
                "Type",
                "Document Number",
                "Date",
                "Supplier",
                "Buyer",
                "Total Amount",
                "Saved At",
            ]
        )

    return pd.DataFrame(
        invoice_rows,
        columns=[
            "ID",
            "File Name",
            "Type",
            "Document Number",
            "Date",
            "Supplier",
            "Buyer",
            "Total Amount",
            "Saved At",
        ]
    )


# --------------------------------------------------
# Tabs
# --------------------------------------------------

tab_upload, tab_inventory, tab_history = st.tabs(
    [
        "📤 Upload Invoice",
        "📦 Inventory Dashboard",
        "📜 Invoice History",
    ]
)


# --------------------------------------------------
# Upload tab
# --------------------------------------------------

with tab_upload:
    st.header("Upload and Process Invoice")

    uploaded_file = st.file_uploader(
        "Upload Invoice PDF",
        type=["pdf"]
    )

    if uploaded_file:
        file_path = INVOICES_DIR / uploaded_file.name

        with open(file_path, "wb") as file:
            file.write(uploaded_file.getbuffer())

        st.success(f"Uploaded and saved: {uploaded_file.name}")

        try:
            extracted_text = extract_text_from_pdf(file_path)
            extracted_fields = extract_invoice_fields(extracted_text)
            line_items = extract_line_items(extracted_text)

            with st.expander("View extracted invoice text", expanded=False):
                st.text_area(
                    "Extracted text",
                    extracted_text,
                    height=300
                )

            st.subheader("Invoice Type")

            invoice_type = st.selectbox(
                "Choose invoice type",
                ["Purchase", "Sale"],
                help="Purchase increases stock. Sale decreases stock."
            )

            st.subheader("Structured Invoice Fields")

            col1, col2 = st.columns(2)

            with col1:
                document_number = st.text_input(
                    "Document number",
                    value=extracted_fields.get("document_number", "")
                )

                document_date = st.text_input(
                    "Document date",
                    value=extracted_fields.get("document_date", "")
                )

                total_amount = st.text_input(
                    "Total amount",
                    value=extracted_fields.get("total_amount", "")
                )

            with col2:
                supplier = st.text_input(
                    "Supplier",
                    value=extracted_fields.get("supplier", "")
                )

                buyer = st.text_input(
                    "Buyer",
                    value=extracted_fields.get("buyer", "")
                )

            st.subheader("Extracted Product Lines")

            product_columns = [
                "product_code",
                "product_name",
                "quantity",
                "unit",
                "unit_price",
                "net_amount",
                "vat_rate",
                "vat_amount",
                "gross_amount",
                "line_total",
                "raw_line",
            ]

            if line_items:
                items_df = pd.DataFrame(line_items)

                for column in product_columns:
                    if column not in items_df.columns:
                        items_df[column] = ""

                items_df = items_df[product_columns]

            else:
                items_df = pd.DataFrame(columns=product_columns)

            edited_items_df = st.data_editor(
                items_df,
                use_container_width=True,
                num_rows="dynamic",
                hide_index=True
            )

            st.info(
                "You can manually correct product names, quantities or prices before saving. "
                "This is normal because invoice layouts vary."
            )

            if st.button("Save Invoice to Database", type="primary"):
                invoice_data = {
                    "file_name": uploaded_file.name,
                    "invoice_type": invoice_type,
                    "document_number": document_number,
                    "document_date": document_date,
                    "supplier": supplier,
                    "buyer": buyer,
                    "total_amount": total_amount,
                }

                edited_line_items = edited_items_df.fillna("").to_dict("records")

                saved_invoice_id = save_invoice(
                    invoice_data=invoice_data,
                    line_items=edited_line_items
                )

                st.success(
                    f"Invoice saved successfully. Invoice ID: {saved_invoice_id}"
                )

        except Exception as error:
            st.error("Something went wrong while extracting invoice data.")
            st.exception(error)

    else:
        st.warning("Please upload a PDF invoice to begin.")


# --------------------------------------------------
# Inventory dashboard tab
# --------------------------------------------------

with tab_inventory:
    st.header("Inventory Dashboard")

    inventory_df = build_inventory_dataframe()
    invoices_df = build_invoice_dataframe()

    total_invoices = len(invoices_df)
    total_products = len(inventory_df)

    if not inventory_df.empty:
        total_stock = inventory_df["Current Stock"].sum()
        low_stock_count = len(inventory_df[inventory_df["Current Stock"] <= 5])
    else:
        total_stock = 0
        low_stock_count = 0

    card1, card2, card3, card4 = st.columns(4)

    card1.metric("Invoices Saved", total_invoices)
    card2.metric("Products Tracked", total_products)
    card3.metric("Total Stock Quantity", total_stock)
    card4.metric("Low Stock Items", low_stock_count)

    st.divider()

    st.subheader("Current Stock")

    if not inventory_df.empty:
        st.dataframe(
            inventory_df,
            use_container_width=True
        )

        st.subheader("Low Stock Items")

        low_stock_df = inventory_df[
            inventory_df["Current Stock"] <= 5
        ]

        if not low_stock_df.empty:
            st.warning("Some products have low stock.")
            st.dataframe(
                low_stock_df,
                use_container_width=True
            )
        else:
            st.success("No low stock items found.")

    else:
        st.info("No inventory data yet. Save an invoice first.")


# --------------------------------------------------
# Invoice history tab
# --------------------------------------------------

with tab_history:
    st.header("Saved Invoice History")

    invoices_df = build_invoice_dataframe()

    if not invoices_df.empty:
        st.dataframe(
            invoices_df,
            use_container_width=True
        )
    else:
        st.info("No invoices saved yet.")