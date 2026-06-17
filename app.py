from pathlib import Path

import pandas as pd
import streamlit as st

from database import (
    delete_invoice,
    get_inventory_summary,
    get_invoice_items,
    get_invoices,
    get_manual_adjustments,
    init_db,
    save_invoice,
    save_manual_adjustment,
    update_invoice_type,
    delete_manual_adjustment,
)
from extractor import extract_invoice_fields, extract_line_items
from ocr import extract_text_from_pdf


st.set_page_config(
    page_title="Invoice Processing AI",
    page_icon="📄",
    layout="wide"
)


BASE_DIR = Path(__file__).parent
INVOICES_DIR = BASE_DIR / "invoices"
INVOICES_DIR.mkdir(exist_ok=True)

init_db()


st.title("📄 Invoice Processing AI + Inventory")
st.write(
    "Upload invoice PDFs, extract invoice data and product lines, "
    "then save them into a database for stock and financial tracking."
)

st.info(
    "Demo project using fake/test data only. Purchase invoices increase stock. "
    "Shop sale invoices decrease stock."
)


def parse_amount(amount_text):
    if amount_text is None:
        return 0.0

    amount_text = str(amount_text)
    amount_text = amount_text.replace("PLN", "")
    amount_text = amount_text.replace("zł", "")
    amount_text = amount_text.replace("zl", "")
    amount_text = amount_text.replace(" ", "")
    amount_text = amount_text.replace(".", "")
    amount_text = amount_text.replace(",", ".")

    try:
        return float(amount_text)
    except ValueError:
        return 0.0


def parse_date(date_text):
    if not date_text:
        return pd.NaT

    return pd.to_datetime(
        date_text,
        dayfirst=True,
        errors="coerce"
    )


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


def build_financial_dataframe():
    invoices_df = build_invoice_dataframe()

    if invoices_df.empty:
        return invoices_df

    financial_df = invoices_df.copy()

    financial_df["Amount Number"] = financial_df["Total Amount"].apply(parse_amount)
    financial_df["Parsed Date"] = financial_df["Date"].apply(parse_date)

    financial_df["Month"] = financial_df["Parsed Date"].dt.to_period("M").astype(str)
    financial_df["Year"] = financial_df["Parsed Date"].dt.year.astype("Int64")

    financial_df["Sales Income"] = financial_df.apply(
        lambda row: row["Amount Number"] if row["Type"] == "Sale" else 0,
        axis=1
    )

    financial_df["Purchase Cost"] = financial_df.apply(
        lambda row: row["Amount Number"] if row["Type"] == "Purchase" else 0,
        axis=1
    )

    financial_df["Net Result"] = financial_df["Sales Income"] - financial_df["Purchase Cost"]

    financial_df["Cash Impact"] = financial_df.apply(
        lambda row: row["Amount Number"] if row["Type"] == "Sale" else -row["Amount Number"],
        axis=1
    )

    return financial_df


tab_upload, tab_inventory, tab_financial, tab_history, tab_adjust = st.tabs(
    [
        "📤 Upload Invoice",
        "📦 Inventory Dashboard",
        "💷 Financial Dashboard",
        "📜 Invoice History",
        "🛠️ Manual Adjustments",
    ]
)


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

            invoice_type_display = st.selectbox(
                "Choose invoice type",
                [
                    "Purchase invoice - stock IN / cost",
                    "Shop sale invoice - stock OUT / income",
                ],
                help=(
                    "Purchase invoice increases stock and counts as cost. "
                    "Shop sale invoice decreases stock and counts as income."
                )
            )

            if invoice_type_display == "Purchase invoice - stock IN / cost":
                invoice_type = "Purchase"
            else:
                invoice_type = "Sale"

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

            if invoice_type == "Purchase":
                st.success("This invoice will ADD quantities to inventory and count as purchase cost.")
            else:
                st.warning("This invoice will DEDUCT quantities from inventory and count as sales income.")

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
            use_container_width=True,
            hide_index=True
        )

        st.subheader("Low Stock Items")

        low_stock_df = inventory_df[
            inventory_df["Current Stock"] <= 5
        ]

        if not low_stock_df.empty:
            st.warning("Some products have low stock.")
            st.dataframe(
                low_stock_df,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.success("No low stock items found.")

    else:
        st.info("No inventory data yet. Save an invoice first.")


with tab_financial:
    st.header("Financial Dashboard")

    st.write(
        "This is an MVP-level financial view. Purchases are treated as costs, "
        "sales are treated as income, and net result is sales minus purchases."
    )

    financial_df = build_financial_dataframe()

    if financial_df.empty:
        st.info("No financial data yet. Save invoices first.")
    else:
        total_sales = financial_df["Sales Income"].sum()
        total_purchases = financial_df["Purchase Cost"].sum()
        net_result = total_sales - total_purchases
        total_cash_impact = financial_df["Cash Impact"].sum()

        card1, card2, card3, card4 = st.columns(4)

        card1.metric("Sales Income", f"{total_sales:,.2f} PLN")
        card2.metric("Purchase Costs", f"{total_purchases:,.2f} PLN")
        card3.metric("Net Result", f"{net_result:,.2f} PLN")
        card4.metric("Cash Impact", f"{total_cash_impact:,.2f} PLN")

        st.divider()

        st.subheader("Invoice Financial Records")

        display_columns = [
            "ID",
            "Type",
            "Document Number",
            "Date",
            "Supplier",
            "Buyer",
            "Total Amount",
            "Sales Income",
            "Purchase Cost",
            "Net Result",
            "Cash Impact",
        ]

        st.dataframe(
            financial_df[display_columns],
            use_container_width=True,
            hide_index=True
        )

        st.subheader("Monthly Summary")

        monthly_summary = (
            financial_df
            .groupby("Month", dropna=False)[
                [
                    "Sales Income",
                    "Purchase Cost",
                    "Net Result",
                    "Cash Impact",
                ]
            ]
            .sum()
            .reset_index()
        )

        st.dataframe(
            monthly_summary,
            use_container_width=True,
            hide_index=True
        )

        st.subheader("Yearly Summary")

        yearly_summary = (
            financial_df
            .groupby("Year", dropna=False)[
                [
                    "Sales Income",
                    "Purchase Cost",
                    "Net Result",
                    "Cash Impact",
                ]
            ]
            .sum()
            .reset_index()
        )

        st.dataframe(
            yearly_summary,
            use_container_width=True,
            hide_index=True
        )

        st.warning(
            "Important: this is not full accounting profit yet. "
            "True profit needs product cost, selling price, VAT handling and expenses."
        )


with tab_history:
    st.header("Saved Invoice History")

    invoices_df = build_invoice_dataframe()

    if not invoices_df.empty:
        st.dataframe(
            invoices_df,
            use_container_width=True,
            hide_index=True
        )

        invoice_ids = invoices_df["ID"].tolist()

        st.subheader("Correct Invoice Type")

        st.write(
            "Use this if you accidentally saved a selling invoice as Purchase, "
            "or a purchase invoice as Sale."
        )

        correction_invoice_id = st.selectbox(
            "Select invoice ID to correct",
            invoice_ids,
            key="correction_invoice_id"
        )

        corrected_type = st.selectbox(
            "New invoice type",
            ["Purchase", "Sale"],
            key="corrected_type"
        )

        if st.button("Update Invoice Type"):
            update_invoice_type(correction_invoice_id, corrected_type)
            st.success(
                f"Invoice ID {correction_invoice_id} updated to {corrected_type}."
            )
            st.rerun()

        st.divider()

        st.subheader("View Invoice Items")

        selected_invoice_id = st.selectbox(
            "Select invoice ID to view items",
            invoice_ids,
            key="view_invoice_id"
        )

        item_rows = get_invoice_items(selected_invoice_id)

        if item_rows:
            items_df = pd.DataFrame(
                item_rows,
                columns=[
                    "Item ID",
                    "Product Code",
                    "Product Name",
                    "Quantity",
                    "Unit",
                    "Unit Price",
                    "Net Amount",
                    "VAT Rate",
                    "VAT Amount",
                    "Gross Amount",
                    "Line Total",
                    "Raw Line",
                ]
            )

            st.dataframe(
                items_df,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No items found for this invoice.")

        st.divider()

        st.subheader("Delete Invoice")

        st.warning(
            "Deleting an invoice will also remove its product lines from inventory calculations."
        )

        delete_invoice_id = st.selectbox(
            "Select invoice ID to delete",
            invoice_ids,
            key="delete_invoice_id"
        )

        confirm_delete = st.checkbox(
            "I understand this will delete the selected invoice and update inventory."
        )

        if st.button("Delete Selected Invoice"):
            if confirm_delete:
                delete_invoice(delete_invoice_id)
                st.success(f"Invoice ID {delete_invoice_id} deleted.")
                st.rerun()
            else:
                st.error("Please tick the confirmation box before deleting.")

    else:
        st.info("No invoices saved yet.")


with tab_adjust:
    st.header("Manual Inventory Adjustments")

    st.write(
        "Use this when stock needs correcting manually, for example damaged items, "
        "missing stock, stock count correction, or items added without an invoice."
    )

    inventory_df = build_inventory_dataframe()

    st.subheader("Current Inventory Reference")

    if not inventory_df.empty:
        st.dataframe(
            inventory_df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No inventory data yet.")

    st.subheader("Add Manual Adjustment")

    col1, col2 = st.columns(2)

    with col1:
        product_code = st.text_input("Product code")
        product_name = st.text_input("Product name")
        unit = st.text_input("Unit", value="szt")

    with col2:
        quantity_change = st.number_input(
            "Quantity change",
            value=0.0,
            step=1.0,
            help="Use a positive number to add stock. Use a negative number to deduct stock."
        )

        reason = st.text_input(
            "Reason",
            value="Manual stock correction"
        )

    st.info(
        "Example: enter 5 to add 5 items. Enter -2 to deduct 2 items."
    )

    if st.button("Save Manual Adjustment", type="primary"):
        if not product_name.strip():
            st.error("Product name is required.")
        elif quantity_change == 0:
            st.error("Quantity change cannot be zero.")
        else:
            save_manual_adjustment(
                product_code=product_code,
                product_name=product_name,
                quantity_change=quantity_change,
                unit=unit,
                reason=reason,
            )

            st.success("Manual inventory adjustment saved.")
            st.rerun()

    st.divider()

    st.subheader("Manual Adjustment History")

    adjustment_rows = get_manual_adjustments()

    if adjustment_rows:
        adjustments_df = pd.DataFrame(
            adjustment_rows,
            columns=[
                "ID",
                "Product Code",
                "Product Name",
                "Quantity Change",
                "Unit",
                "Reason",
                "Saved At",
            ]
        )

        st.dataframe(
            adjustments_df,
            use_container_width=True,
            hide_index=True
        )

        st.subheader("Delete Manual Adjustment")

        st.warning(
            "Use this only if a manual adjustment was added by mistake. "
            "Deleting it will update the inventory calculation."
        )

        adjustment_ids = adjustments_df["ID"].tolist()

        selected_adjustment_id = st.selectbox(
            "Select manual adjustment ID to delete",
            adjustment_ids,
            key="delete_adjustment_id"
        )

        confirm_delete_adjustment = st.checkbox(
            "I understand this will delete the selected manual adjustment and update inventory.",
            key="confirm_delete_adjustment"
        )

        if st.button("Delete Selected Manual Adjustment"):
            if confirm_delete_adjustment:
                delete_manual_adjustment(selected_adjustment_id)
                st.success(f"Manual adjustment ID {selected_adjustment_id} deleted.")
                st.rerun()
            else:
                st.error("Please tick the confirmation box before deleting.")

    else:
        st.info("No manual adjustments saved yet.")