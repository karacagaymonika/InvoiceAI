from pathlib import Path

import pandas as pd
import streamlit as st

from database import (
    create_database_backup,
    delete_invoice,
    delete_manual_adjustment,
    get_backup_files,
    get_inventory_summary,
    get_invoice_items,
    get_invoices,
    get_manual_adjustments,
    init_db,
    save_invoice,
    save_manual_adjustment,
    update_invoice_type,
)
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


# --------------------------------------------------
# Language setup
# --------------------------------------------------

TEXT = {
    "EN": {
        "app_title": "📄 Invoice Processing AI + Inventory",
        "intro": (
            "Upload invoice PDFs, extract invoice data and product lines, "
            "then save them into a database for stock and financial tracking."
        ),
        "demo_note": (
            "Demo project using fake/test data only. Purchase invoices increase stock. "
            "Shop sale invoices decrease stock."
        ),
        "language_label": "Language / Język",

        "upload_tab": "📤 Upload Invoice",
        "inventory_tab": "📦 Inventory Dashboard",
        "financial_tab": "💷 Financial Dashboard",
        "history_tab": "📜 Invoice History",
        "adjust_tab": "🛠️ Manual Adjustments",
        "backup_tab": "🛡️ Safety / Backups",

        "upload_header": "Upload and Process Invoice",
        "upload_pdf": "Upload Invoice PDF",
        "uploaded_saved": "Uploaded and saved",
        "view_extracted_text": "View extracted invoice text",
        "extracted_text": "Extracted text",
        "invoice_type": "Invoice Type",
        "choose_invoice_type": "Choose invoice type",
        "purchase_option": "Purchase invoice - stock IN / cost",
        "sale_option": "Shop sale invoice - stock OUT / income",
        "invoice_type_help": (
            "Purchase invoice increases stock and counts as cost. "
            "Shop sale invoice decreases stock and counts as income."
        ),
        "structured_fields": "Structured Invoice Fields",
        "document_number": "Document number",
        "document_date": "Document date",
        "total_amount": "Total amount",
        "supplier": "Supplier",
        "buyer": "Buyer",
        "product_lines": "Extracted Product Lines",
        "manual_correct_info": (
            "You can manually correct product names, quantities or prices before saving. "
            "This is normal because invoice layouts vary."
        ),
        "purchase_info": "This invoice will ADD quantities to inventory and count as purchase cost.",
        "sale_info": "This invoice will DEDUCT quantities from inventory and count as sales income.",
        "save_invoice": "Save Invoice to Database",
        "invoice_saved": "Invoice saved successfully. Invoice ID",
        "extract_error": "Something went wrong while extracting invoice data.",
        "upload_prompt": "Please upload a PDF invoice to begin.",

        "inventory_header": "Inventory Dashboard",
        "invoices_saved": "Invoices Saved",
        "products_tracked": "Products Tracked",
        "total_stock_quantity": "Total Stock Quantity",
        "low_stock_items": "Low Stock Items",
        "current_stock": "Current Stock",
        "some_low_stock": "Some products have low stock.",
        "no_low_stock": "No low stock items found.",
        "no_inventory": "No inventory data yet. Save an invoice first.",

        "financial_header": "Financial Dashboard",
        "financial_explain": (
            "This is an MVP-level financial view. Purchases are treated as costs, "
            "sales are treated as income, and net result is sales minus purchases."
        ),
        "no_financial": "No financial data yet. Save invoices first.",
        "sales_income": "Sales Income",
        "purchase_costs": "Purchase Costs",
        "net_result": "Net Result",
        "cash_impact": "Cash Impact",
        "financial_records": "Invoice Financial Records",
        "monthly_summary": "Monthly Summary",
        "yearly_summary": "Yearly Summary",
        "profit_warning": (
            "MVP note: this is not full accounting profit yet. True profit calculation needs "
            "product cost, selling price, VAT handling, expenses and returns."
        ),

        "history_header": "Saved Invoice History",
        "correct_invoice_type": "Correct Invoice Type",
        "correct_invoice_help": (
            "Use this if you accidentally saved a selling invoice as Purchase, "
            "or a purchase invoice as Sale."
        ),
        "select_invoice_correct": "Select invoice ID to correct",
        "new_invoice_type": "New invoice type",
        "purchase_short": "Purchase",
        "sale_short": "Sale",
        "update_invoice_type": "Update Invoice Type",
        "invoice_type_updated": "Invoice type updated.",
        "view_invoice_items": "View Invoice Items",
        "select_invoice_view": "Select invoice ID to view items",
        "no_items": "No items found for this invoice.",
        "delete_invoice": "Delete Invoice",
        "delete_invoice_warning": (
            "Deleting an invoice will also remove its product lines from inventory calculations."
        ),
        "select_invoice_delete": "Select invoice ID to delete",
        "confirm_delete_invoice": (
            "I understand this will delete the selected invoice and update inventory."
        ),
        "delete_selected_invoice": "Delete Selected Invoice",
        "invoice_deleted": "Invoice deleted.",
        "tick_confirm": "Please tick the confirmation box before deleting.",
        "no_invoices": "No invoices saved yet.",

        "manual_header": "Manual Inventory Adjustments",
        "manual_explain": (
            "Use this when stock needs correcting manually, for example damaged items, "
            "missing stock, stock count correction, or items added without an invoice."
        ),
        "current_inventory_reference": "Current Inventory Reference",
        "add_manual_adjustment": "Add Manual Adjustment",
        "product_code": "Product code",
        "product_name": "Product name",
        "unit": "Unit",
        "quantity_change": "Quantity change",
        "quantity_change_help": (
            "Use a positive number to add stock. Use a negative number to deduct stock."
        ),
        "reason": "Reason",
        "reason_default": "Manual stock correction",
        "manual_example": "Example: enter 5 to add 5 items. Enter -2 to deduct 2 items.",
        "save_manual": "Save Manual Adjustment",
        "product_required": "Product name is required.",
        "quantity_zero": "Quantity change cannot be zero.",
        "manual_saved": "Manual inventory adjustment saved.",
        "manual_history": "Manual Adjustment History",
        "delete_manual": "Delete Manual Adjustment",
        "delete_manual_warning": (
            "Use this only if a manual adjustment was added by mistake. "
            "Deleting it will update the inventory calculation."
        ),
        "select_manual_delete": "Select manual adjustment ID to delete",
        "confirm_delete_manual": (
            "I understand this will delete the selected manual adjustment and update inventory."
        ),
        "delete_selected_manual": "Delete Selected Manual Adjustment",
        "manual_deleted": "Manual adjustment deleted.",
        "no_manual": "No manual adjustments saved yet.",

        "backup_header": "Safety and Database Backups",
        "backup_explain": (
            "Use this section to create a safe copy of the database before making important changes. "
            "Backups protect the app data if something is deleted or changed by mistake."
        ),
        "backup_now": "Create Backup Now",
        "backup_created": "Backup created successfully",
        "latest_backups": "Latest Backup Files",
        "no_backups": "No backups created yet.",
        "backup_mum_note": (
            "Recommendation: create a backup before uploading many invoices, deleting invoices, "
            "or making manual stock corrections."
        ),
    },

    "PL": {
        "app_title": "📄 Invoice Processing AI + Magazyn",
        "intro": (
            "Wgraj fakturę PDF, odczytaj dane z faktury i pozycje produktowe, "
            "a następnie zapisz je do bazy danych, aby kontrolować magazyn i finanse."
        ),
        "demo_note": (
            "Projekt demonstracyjny na danych testowych. Faktury zakupowe zwiększają stan magazynowy. "
            "Faktury sprzedażowe sklepu zmniejszają stan magazynowy."
        ),
        "language_label": "Język / Language",

        "upload_tab": "📤 Wgraj fakturę",
        "inventory_tab": "📦 Magazyn",
        "financial_tab": "💷 Finanse",
        "history_tab": "📜 Historia faktur",
        "adjust_tab": "🛠️ Korekty ręczne",
        "backup_tab": "🛡️ Bezpieczeństwo / Kopie",

        "upload_header": "Wgraj i przetwórz fakturę",
        "upload_pdf": "Wgraj fakturę PDF",
        "uploaded_saved": "Wgrano i zapisano",
        "view_extracted_text": "Pokaż tekst odczytany z faktury",
        "extracted_text": "Odczytany tekst",
        "invoice_type": "Typ faktury",
        "choose_invoice_type": "Wybierz typ faktury",
        "purchase_option": "Faktura zakupowa - towar DO magazynu / koszt",
        "sale_option": "Faktura sprzedażowa sklepu - towar Z magazynu / przychód",
        "invoice_type_help": (
            "Faktura zakupowa zwiększa stan magazynowy i liczy się jako koszt. "
            "Faktura sprzedażowa zmniejsza stan magazynowy i liczy się jako przychód."
        ),
        "structured_fields": "Dane z faktury",
        "document_number": "Numer dokumentu",
        "document_date": "Data dokumentu",
        "total_amount": "Kwota całkowita",
        "supplier": "Sprzedawca / dostawca",
        "buyer": "Nabywca / klient",
        "product_lines": "Pozycje produktowe",
        "manual_correct_info": (
            "Możesz ręcznie poprawić nazwy produktów, ilości lub ceny przed zapisaniem. "
            "To normalne, ponieważ faktury mają różne układy."
        ),
        "purchase_info": "Ta faktura DODA ilości do magazynu i zostanie policzona jako koszt zakupu.",
        "sale_info": "Ta faktura ODEJMIE ilości z magazynu i zostanie policzona jako przychód ze sprzedaży.",
        "save_invoice": "Zapisz fakturę do bazy danych",
        "invoice_saved": "Faktura została zapisana. ID faktury",
        "extract_error": "Wystąpił błąd podczas odczytywania danych z faktury.",
        "upload_prompt": "Wgraj fakturę PDF, aby rozpocząć.",

        "inventory_header": "Magazyn",
        "invoices_saved": "Zapisane faktury",
        "products_tracked": "Produkty w magazynie",
        "total_stock_quantity": "Łączna ilość towaru",
        "low_stock_items": "Produkty z niskim stanem",
        "current_stock": "Aktualny stan magazynowy",
        "some_low_stock": "Niektóre produkty mają niski stan magazynowy.",
        "no_low_stock": "Brak produktów z niskim stanem.",
        "no_inventory": "Brak danych magazynowych. Najpierw zapisz fakturę.",

        "financial_header": "Panel finansowy",
        "financial_explain": (
            "To jest uproszczony widok finansowy MVP. Zakupy są traktowane jako koszty, "
            "sprzedaż jako przychód, a wynik netto to sprzedaż minus zakupy."
        ),
        "no_financial": "Brak danych finansowych. Najpierw zapisz faktury.",
        "sales_income": "Przychód ze sprzedaży",
        "purchase_costs": "Koszty zakupów",
        "net_result": "Wynik netto",
        "cash_impact": "Wpływ na środki",
        "financial_records": "Zapisy finansowe faktur",
        "monthly_summary": "Podsumowanie miesięczne",
        "yearly_summary": "Podsumowanie roczne",
        "profit_warning": (
            "Uwaga MVP: to nie jest jeszcze pełny zysk księgowy. Pełne obliczenie zysku wymaga "
            "kosztu produktu, ceny sprzedaży, obsługi VAT, kosztów dodatkowych i zwrotów."
        ),

        "history_header": "Historia zapisanych faktur",
        "correct_invoice_type": "Popraw typ faktury",
        "correct_invoice_help": (
            "Użyj tego, jeśli faktura sprzedażowa została przypadkowo zapisana jako zakupowa "
            "albo faktura zakupowa jako sprzedażowa."
        ),
        "select_invoice_correct": "Wybierz ID faktury do poprawy",
        "new_invoice_type": "Nowy typ faktury",
        "purchase_short": "Zakup",
        "sale_short": "Sprzedaż",
        "update_invoice_type": "Zaktualizuj typ faktury",
        "invoice_type_updated": "Typ faktury został zaktualizowany.",
        "view_invoice_items": "Pokaż pozycje z faktury",
        "select_invoice_view": "Wybierz ID faktury, aby zobaczyć pozycje",
        "no_items": "Brak pozycji dla tej faktury.",
        "delete_invoice": "Usuń fakturę",
        "delete_invoice_warning": (
            "Usunięcie faktury usunie również jej pozycje z obliczeń magazynowych."
        ),
        "select_invoice_delete": "Wybierz ID faktury do usunięcia",
        "confirm_delete_invoice": (
            "Rozumiem, że wybrana faktura zostanie usunięta, a magazyn zostanie przeliczony."
        ),
        "delete_selected_invoice": "Usuń wybraną fakturę",
        "invoice_deleted": "Faktura została usunięta.",
        "tick_confirm": "Zaznacz potwierdzenie przed usunięciem.",
        "no_invoices": "Brak zapisanych faktur.",

        "manual_header": "Ręczne korekty magazynu",
        "manual_explain": (
            "Użyj tego, gdy stan magazynowy wymaga ręcznej poprawy, np. uszkodzony towar, "
            "braki, korekta po liczeniu magazynu albo towar dodany bez faktury."
        ),
        "current_inventory_reference": "Podgląd aktualnego magazynu",
        "add_manual_adjustment": "Dodaj ręczną korektę",
        "product_code": "Kod produktu",
        "product_name": "Nazwa produktu",
        "unit": "Jednostka",
        "quantity_change": "Zmiana ilości",
        "quantity_change_help": (
            "Użyj liczby dodatniej, aby dodać towar. Użyj liczby ujemnej, aby odjąć towar."
        ),
        "reason": "Powód",
        "reason_default": "Ręczna korekta magazynu",
        "manual_example": "Przykład: wpisz 5, aby dodać 5 sztuk. Wpisz -2, aby odjąć 2 sztuki.",
        "save_manual": "Zapisz ręczną korektę",
        "product_required": "Nazwa produktu jest wymagana.",
        "quantity_zero": "Zmiana ilości nie może wynosić zero.",
        "manual_saved": "Ręczna korekta została zapisana.",
        "manual_history": "Historia ręcznych korekt",
        "delete_manual": "Usuń ręczną korektę",
        "delete_manual_warning": (
            "Użyj tego tylko wtedy, gdy korekta została dodana przez pomyłkę. "
            "Usunięcie korekty przeliczy magazyn."
        ),
        "select_manual_delete": "Wybierz ID korekty do usunięcia",
        "confirm_delete_manual": (
            "Rozumiem, że wybrana ręczna korekta zostanie usunięta, a magazyn zostanie przeliczony."
        ),
        "delete_selected_manual": "Usuń wybraną ręczną korektę",
        "manual_deleted": "Ręczna korekta została usunięta.",
        "no_manual": "Brak zapisanych ręcznych korekt.",

        "backup_header": "Bezpieczeństwo i kopie zapasowe bazy danych",
        "backup_explain": (
            "W tej sekcji możesz utworzyć bezpieczną kopię bazy danych przed ważnymi zmianami. "
            "Kopie zapasowe chronią dane aplikacji, jeśli coś zostanie usunięte lub zmienione przez pomyłkę."
        ),
        "backup_now": "Utwórz kopię zapasową teraz",
        "backup_created": "Kopia zapasowa została utworzona",
        "latest_backups": "Ostatnie kopie zapasowe",
        "no_backups": "Brak utworzonych kopii zapasowych.",
        "backup_mum_note": (
            "Rekomendacja: utwórz kopię przed wgraniem wielu faktur, usuwaniem faktur "
            "lub ręcznymi korektami magazynu."
        ),
    },
}


COLUMN_LABELS = {
    "EN": {
        "Product Code": "Product Code",
        "Product Name": "Product Name",
        "Unit": "Unit",
        "Current Stock": "Current Stock",
        "ID": "ID",
        "File Name": "File Name",
        "Type": "Type",
        "Document Number": "Document Number",
        "Date": "Date",
        "Supplier": "Supplier",
        "Buyer": "Buyer",
        "Total Amount": "Total Amount",
        "Saved At": "Saved At",
        "Sales Income": "Sales Income",
        "Purchase Cost": "Purchase Cost",
        "Net Result": "Net Result",
        "Cash Impact": "Cash Impact",
        "Month": "Month",
        "Year": "Year",
        "Item ID": "Item ID",
        "Quantity": "Quantity",
        "Unit Price": "Unit Price",
        "Net Amount": "Net Amount",
        "VAT Rate": "VAT Rate",
        "VAT Amount": "VAT Amount",
        "Gross Amount": "Gross Amount",
        "Line Total": "Line Total",
        "Raw Line": "Raw Line",
        "Quantity Change": "Quantity Change",
        "Reason": "Reason",
    },
    "PL": {
        "Product Code": "Kod produktu",
        "Product Name": "Nazwa produktu",
        "Unit": "Jednostka",
        "Current Stock": "Aktualny stan",
        "ID": "ID",
        "File Name": "Nazwa pliku",
        "Type": "Typ",
        "Document Number": "Numer dokumentu",
        "Date": "Data",
        "Supplier": "Sprzedawca / dostawca",
        "Buyer": "Nabywca / klient",
        "Total Amount": "Kwota całkowita",
        "Saved At": "Zapisano",
        "Sales Income": "Przychód ze sprzedaży",
        "Purchase Cost": "Koszt zakupu",
        "Net Result": "Wynik netto",
        "Cash Impact": "Wpływ na środki",
        "Month": "Miesiąc",
        "Year": "Rok",
        "Item ID": "ID pozycji",
        "Quantity": "Ilość",
        "Unit Price": "Cena jednostkowa",
        "Net Amount": "Kwota netto",
        "VAT Rate": "Stawka VAT",
        "VAT Amount": "Kwota VAT",
        "Gross Amount": "Kwota brutto",
        "Line Total": "Suma pozycji",
        "Raw Line": "Oryginalna linia",
        "Quantity Change": "Zmiana ilości",
        "Reason": "Powód",
    },
}


language_choice = st.sidebar.selectbox(
    "Language / Język",
    ["Polski", "English"]
)

LANG = "PL" if language_choice == "Polski" else "EN"


def t(key):
    return TEXT[LANG].get(key, key)


def translate_columns(dataframe):
    return dataframe.rename(columns=COLUMN_LABELS[LANG])


def translate_invoice_type(value):
    if LANG == "PL":
        if value == "Purchase":
            return "Zakup"
        if value == "Sale":
            return "Sprzedaż"

    return value


# --------------------------------------------------
# Paths and database
# --------------------------------------------------

BASE_DIR = Path(__file__).parent
INVOICES_DIR = BASE_DIR / "invoices"
INVOICES_DIR.mkdir(exist_ok=True)

init_db()


# --------------------------------------------------
# Header
# --------------------------------------------------

st.title(t("app_title"))
st.write(t("intro"))
st.info(t("demo_note"))


# --------------------------------------------------
# Helper functions
# --------------------------------------------------

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


# --------------------------------------------------
# Tabs
# --------------------------------------------------

tab_upload, tab_inventory, tab_financial, tab_history, tab_adjust, tab_backup = st.tabs(
    [
        t("upload_tab"),
        t("inventory_tab"),
        t("financial_tab"),
        t("history_tab"),
        t("adjust_tab"),
        t("backup_tab"),
    ]
)


# --------------------------------------------------
# Upload invoice tab
# --------------------------------------------------

with tab_upload:
    st.header(t("upload_header"))

    uploaded_file = st.file_uploader(
        t("upload_pdf"),
        type=["pdf"]
    )

    if uploaded_file:
        file_path = INVOICES_DIR / uploaded_file.name

        with open(file_path, "wb") as file:
            file.write(uploaded_file.getbuffer())

        st.success(f"{t('uploaded_saved')}: {uploaded_file.name}")

        try:
            extracted_text = extract_text_from_pdf(file_path)
            extracted_fields = extract_invoice_fields(extracted_text)
            line_items = extract_line_items(extracted_text)

            with st.expander(t("view_extracted_text"), expanded=False):
                st.text_area(
                    t("extracted_text"),
                    extracted_text,
                    height=300
                )

            st.subheader(t("invoice_type"))

            invoice_type_display = st.selectbox(
                t("choose_invoice_type"),
                [
                    t("purchase_option"),
                    t("sale_option"),
                ],
                help=t("invoice_type_help")
            )

            if invoice_type_display == t("purchase_option"):
                invoice_type = "Purchase"
            else:
                invoice_type = "Sale"

            st.subheader(t("structured_fields"))

            col1, col2 = st.columns(2)

            with col1:
                document_number = st.text_input(
                    t("document_number"),
                    value=extracted_fields.get("document_number", "")
                )

                document_date = st.text_input(
                    t("document_date"),
                    value=extracted_fields.get("document_date", "")
                )

                total_amount = st.text_input(
                    t("total_amount"),
                    value=extracted_fields.get("total_amount", "")
                )

            with col2:
                supplier = st.text_input(
                    t("supplier"),
                    value=extracted_fields.get("supplier", "")
                )

                buyer = st.text_input(
                    t("buyer"),
                    value=extracted_fields.get("buyer", "")
                )

            st.subheader(t("product_lines"))

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

            st.info(t("manual_correct_info"))

            if invoice_type == "Purchase":
                st.success(t("purchase_info"))
            else:
                st.warning(t("sale_info"))

            if st.button(t("save_invoice"), type="primary"):
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

                st.success(f"{t('invoice_saved')}: {saved_invoice_id}")

        except Exception as error:
            st.error(t("extract_error"))
            st.exception(error)

    else:
        st.warning(t("upload_prompt"))


# --------------------------------------------------
# Inventory dashboard tab
# --------------------------------------------------

with tab_inventory:
    st.header(t("inventory_header"))

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

    card1.metric(t("invoices_saved"), total_invoices)
    card2.metric(t("products_tracked"), total_products)
    card3.metric(t("total_stock_quantity"), total_stock)
    card4.metric(t("low_stock_items"), low_stock_count)

    st.divider()

    st.subheader(t("current_stock"))

    if not inventory_df.empty:
        st.dataframe(
            translate_columns(inventory_df),
            use_container_width=True,
            hide_index=True
        )

        st.subheader(t("low_stock_items"))

        low_stock_df = inventory_df[
            inventory_df["Current Stock"] <= 5
        ]

        if not low_stock_df.empty:
            st.warning(t("some_low_stock"))
            st.dataframe(
                translate_columns(low_stock_df),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.success(t("no_low_stock"))

    else:
        st.info(t("no_inventory"))


# --------------------------------------------------
# Financial dashboard tab
# --------------------------------------------------

with tab_financial:
    st.header(t("financial_header"))

    st.write(t("financial_explain"))

    financial_df = build_financial_dataframe()

    if financial_df.empty:
        st.info(t("no_financial"))
    else:
        total_sales = financial_df["Sales Income"].sum()
        total_purchases = financial_df["Purchase Cost"].sum()
        net_result = total_sales - total_purchases
        total_cash_impact = financial_df["Cash Impact"].sum()

        card1, card2, card3, card4 = st.columns(4)

        card1.metric(t("sales_income"), f"{total_sales:,.2f} PLN")
        card2.metric(t("purchase_costs"), f"{total_purchases:,.2f} PLN")
        card3.metric(t("net_result"), f"{net_result:,.2f} PLN")
        card4.metric(t("cash_impact"), f"{total_cash_impact:,.2f} PLN")

        st.divider()

        st.subheader(t("financial_records"))

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

        financial_display_df = financial_df[display_columns].copy()
        financial_display_df["Type"] = financial_display_df["Type"].apply(translate_invoice_type)

        st.dataframe(
            translate_columns(financial_display_df),
            use_container_width=True,
            hide_index=True
        )

        st.subheader(t("monthly_summary"))

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
            translate_columns(monthly_summary),
            use_container_width=True,
            hide_index=True
        )

        st.subheader(t("yearly_summary"))

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
            translate_columns(yearly_summary),
            use_container_width=True,
            hide_index=True
        )

        st.warning(t("profit_warning"))


# --------------------------------------------------
# Invoice history tab
# --------------------------------------------------

with tab_history:
    st.header(t("history_header"))

    invoices_df = build_invoice_dataframe()

    if not invoices_df.empty:
        display_invoices_df = invoices_df.copy()
        display_invoices_df["Type"] = display_invoices_df["Type"].apply(translate_invoice_type)

        st.dataframe(
            translate_columns(display_invoices_df),
            use_container_width=True,
            hide_index=True
        )

        invoice_ids = invoices_df["ID"].tolist()

        st.subheader(t("correct_invoice_type"))

        st.write(t("correct_invoice_help"))

        correction_invoice_id = st.selectbox(
            t("select_invoice_correct"),
            invoice_ids,
            key="correction_invoice_id"
        )

        corrected_type_display = st.selectbox(
            t("new_invoice_type"),
            [
                t("purchase_short"),
                t("sale_short"),
            ],
            key="corrected_type"
        )

        if corrected_type_display == t("purchase_short"):
            corrected_type = "Purchase"
        else:
            corrected_type = "Sale"

        if st.button(t("update_invoice_type")):
            update_invoice_type(correction_invoice_id, corrected_type)
            st.success(t("invoice_type_updated"))
            st.rerun()

        st.divider()

        st.subheader(t("view_invoice_items"))

        selected_invoice_id = st.selectbox(
            t("select_invoice_view"),
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
                translate_columns(items_df),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info(t("no_items"))

        st.divider()

        st.subheader(t("delete_invoice"))

        st.warning(t("delete_invoice_warning"))

        delete_invoice_id = st.selectbox(
            t("select_invoice_delete"),
            invoice_ids,
            key="delete_invoice_id"
        )

        confirm_delete = st.checkbox(
            t("confirm_delete_invoice"),
            key="confirm_delete_invoice"
        )

        if st.button(t("delete_selected_invoice")):
            if confirm_delete:
                delete_invoice(delete_invoice_id)
                st.success(t("invoice_deleted"))
                st.rerun()
            else:
                st.error(t("tick_confirm"))

    else:
        st.info(t("no_invoices"))


# --------------------------------------------------
# Manual adjustments tab
# --------------------------------------------------

with tab_adjust:
    st.header(t("manual_header"))

    st.write(t("manual_explain"))

    inventory_df = build_inventory_dataframe()

    st.subheader(t("current_inventory_reference"))

    if not inventory_df.empty:
        st.dataframe(
            translate_columns(inventory_df),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info(t("no_inventory"))

    st.subheader(t("add_manual_adjustment"))

    col1, col2 = st.columns(2)

    with col1:
        product_code = st.text_input(t("product_code"))
        product_name = st.text_input(t("product_name"))
        unit = st.text_input(t("unit"), value="szt")

    with col2:
        quantity_change = st.number_input(
            t("quantity_change"),
            value=0.0,
            step=1.0,
            help=t("quantity_change_help")
        )

        reason = st.text_input(
            t("reason"),
            value=t("reason_default")
        )

    st.info(t("manual_example"))

    if st.button(t("save_manual"), type="primary"):
        if not product_name.strip():
            st.error(t("product_required"))
        elif quantity_change == 0:
            st.error(t("quantity_zero"))
        else:
            save_manual_adjustment(
                product_code=product_code,
                product_name=product_name,
                quantity_change=quantity_change,
                unit=unit,
                reason=reason,
            )

            st.success(t("manual_saved"))
            st.rerun()

    st.divider()

    st.subheader(t("manual_history"))

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
            translate_columns(adjustments_df),
            use_container_width=True,
            hide_index=True
        )

        st.subheader(t("delete_manual"))

        st.warning(t("delete_manual_warning"))

        adjustment_ids = adjustments_df["ID"].tolist()

        selected_adjustment_id = st.selectbox(
            t("select_manual_delete"),
            adjustment_ids,
            key="delete_adjustment_id"
        )

        confirm_delete_adjustment = st.checkbox(
            t("confirm_delete_manual"),
            key="confirm_delete_adjustment"
        )

        if st.button(t("delete_selected_manual")):
            if confirm_delete_adjustment:
                delete_manual_adjustment(selected_adjustment_id)
                st.success(t("manual_deleted"))
                st.rerun()
            else:
                st.error(t("tick_confirm"))

    else:
        st.info(t("no_manual"))


# --------------------------------------------------
# Safety / backup tab
# --------------------------------------------------

with tab_backup:
    st.header(t("backup_header"))

    st.write(t("backup_explain"))
    st.info(t("backup_mum_note"))

    if st.button(t("backup_now"), type="primary"):
        backup_file = create_database_backup("manual")
        st.success(f"{t('backup_created')}: {backup_file.name}")

    st.divider()

    st.subheader(t("latest_backups"))

    backup_files = get_backup_files()

    if backup_files:
        backup_df = pd.DataFrame(
            [
                {
                    "Backup File": backup_file.name,
                    "Created At": pd.to_datetime(
                        backup_file.stat().st_mtime,
                        unit="s"
                    ).strftime("%Y-%m-%d %H:%M:%S"),
                    "Size KB": round(backup_file.stat().st_size / 1024, 2),
                }
                for backup_file in backup_files[:10]
            ]
        )

        st.dataframe(
            backup_df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info(t("no_backups"))