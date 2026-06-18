from pathlib import Path
from io import BytesIO

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
            "Demo/test version. Please keep original invoices and Excel exports as backup. "
            "Purchase invoices increase stock. Shop sale invoices decrease stock."
        ),
        "language_label": "Language / Język",

        "upload_tab": "📤 Add Invoice",
        "inventory_tab": "📦 Inventory Dashboard",
        "financial_tab": "💷 Financial Dashboard",
        "history_tab": "📜 Invoice History",
        "adjust_tab": "🛠️ Manual Adjustments",
        "backup_tab": "🛡️ Safety / Backups",

        "upload_header": "Add and Process Invoice",
        "entry_method": "Choose invoice entry method",
        "pdf_entry": "Upload PDF invoice",
        "manual_entry": "Enter invoice manually",

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
        "structured_fields": "Invoice Details",
        "document_number": "Document number",
        "document_date": "Document date",
        "total_amount": "Total amount",
        "supplier": "Supplier",
        "buyer": "Buyer",
        "product_lines": "Product Lines",
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

        "manual_invoice_header": "Manual Invoice Entry",
        "manual_invoice_info": (
            "Use this option if PDF upload or extraction does not work. "
            "You can type invoice details and product lines manually."
        ),
        "manual_file_name": "Manual entry file name / reference",
        "manual_product_table": "Manual Product Lines",
        "save_manual_invoice": "Save Manual Invoice",
        "manual_invoice_saved": "Manual invoice saved successfully. Invoice ID",

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

        "excel_exports_header": "Excel Exports",
        "excel_exports_explain": (
            "Download Excel copies of inventory, invoices, financial summaries and manual adjustments. "
            "This gives you an extra safety copy outside the app."
        ),
        "download_full_excel": "Download Full Excel Report",
        "download_inventory_excel": "Download Inventory Excel",
        "download_invoices_excel": "Download Invoice History Excel",
        "download_financial_excel": "Download Financial Summary Excel",
        "download_manual_excel": "Download Manual Adjustments Excel",
    },

    "PL": {
        "app_title": "📄 Invoice Processing AI + Magazyn",
        "intro": (
            "Wgraj fakturę PDF, odczytaj dane z faktury i pozycje produktowe, "
            "a następnie zapisz je do bazy danych, aby kontrolować magazyn i finanse."
        ),
        "demo_note": (
            "Wersja testowa. Zachowuj oryginalne faktury i eksporty Excel jako kopię bezpieczeństwa. "
            "Faktury zakupowe zwiększają stan magazynowy. Faktury sprzedażowe sklepu zmniejszają stan magazynowy."
        ),
        "language_label": "Język / Language",

        "upload_tab": "📤 Dodaj fakturę",
        "inventory_tab": "📦 Magazyn",
        "financial_tab": "💷 Finanse",
        "history_tab": "📜 Historia faktur",
        "adjust_tab": "🛠️ Korekty ręczne",
        "backup_tab": "🛡️ Bezpieczeństwo / Kopie",

        "upload_header": "Dodaj i przetwórz fakturę",
        "entry_method": "Wybierz sposób dodania faktury",
        "pdf_entry": "Wgraj fakturę PDF",
        "manual_entry": "Wpisz fakturę ręcznie",

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
        "structured_fields": "Dane faktury",
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

        "manual_invoice_header": "Ręczne dodanie faktury",
        "manual_invoice_info": (
            "Użyj tej opcji, jeśli wgrywanie PDF lub odczyt faktury nie działa. "
            "Możesz ręcznie wpisać dane faktury i pozycje produktowe."
        ),
        "manual_file_name": "Nazwa / numer referencyjny wpisu ręcznego",
        "manual_product_table": "Ręczne pozycje produktowe",
        "save_manual_invoice": "Zapisz ręczną fakturę",
        "manual_invoice_saved": "Ręczna faktura została zapisana. ID faktury",

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

        "excel_exports_header": "Eksport do Excela",
        "excel_exports_explain": (
            "Pobierz kopie danych do Excela: magazyn, faktury, podsumowania finansowe i ręczne korekty. "
            "To dodatkowa bezpieczna kopia poza aplikacją."
        ),
        "download_full_excel": "Pobierz pełny raport Excel",
        "download_inventory_excel": "Pobierz magazyn Excel",
        "download_invoices_excel": "Pobierz historię faktur Excel",
        "download_financial_excel": "Pobierz podsumowanie finansowe Excel",
        "download_manual_excel": "Pobierz korekty ręczne Excel",
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
        "Backup File": "Backup File",
        "Created At": "Created At",
        "Size KB": "Size KB",
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
        "Backup File": "Plik kopii",
        "Created At": "Utworzono",
        "Size KB": "Rozmiar KB",
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


def build_manual_adjustments_dataframe():
    adjustment_rows = get_manual_adjustments()

    if not adjustment_rows:
        return pd.DataFrame(
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

    return pd.DataFrame(
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


def dataframe_to_excel_bytes(dataframe, sheet_name="Data"):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False, sheet_name=sheet_name)

    output.seek(0)
    return output


def build_full_excel_report():
    output = BytesIO()

    inventory_df = build_inventory_dataframe()
    invoices_df = build_invoice_dataframe()
    financial_df = build_financial_dataframe()
    manual_df = build_manual_adjustments_dataframe()

    if not financial_df.empty:
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
    else:
        monthly_summary = pd.DataFrame(
            columns=[
                "Month",
                "Sales Income",
                "Purchase Cost",
                "Net Result",
                "Cash Impact",
            ]
        )

        yearly_summary = pd.DataFrame(
            columns=[
                "Year",
                "Sales Income",
                "Purchase Cost",
                "Net Result",
                "Cash Impact",
            ]
        )

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        inventory_df.to_excel(writer, index=False, sheet_name="Inventory")
        invoices_df.to_excel(writer, index=False, sheet_name="Invoices")
        financial_df.to_excel(writer, index=False, sheet_name="Financial Records")
        monthly_summary.to_excel(writer, index=False, sheet_name="Monthly Summary")
        yearly_summary.to_excel(writer, index=False, sheet_name="Yearly Summary")
        manual_df.to_excel(writer, index=False, sheet_name="Manual Adjustments")

    output.seek(0)
    return output


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
# Add invoice tab
# --------------------------------------------------

with tab_upload:
    st.header(t("upload_header"))

    entry_method = st.radio(
        t("entry_method"),
        [
            t("pdf_entry"),
            t("manual_entry"),
        ],
        horizontal=True
    )

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

    if entry_method == t("pdf_entry"):
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
                    help=t("invoice_type_help"),
                    key="pdf_invoice_type"
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
                        value=extracted_fields.get("document_number", ""),
                        key="pdf_document_number"
                    )

                    document_date = st.text_input(
                        t("document_date"),
                        value=extracted_fields.get("document_date", ""),
                        key="pdf_document_date"
                    )

                    total_amount = st.text_input(
                        t("total_amount"),
                        value=extracted_fields.get("total_amount", ""),
                        key="pdf_total_amount"
                    )

                with col2:
                    supplier = st.text_input(
                        t("supplier"),
                        value=extracted_fields.get("supplier", ""),
                        key="pdf_supplier"
                    )

                    buyer = st.text_input(
                        t("buyer"),
                        value=extracted_fields.get("buyer", ""),
                        key="pdf_buyer"
                    )

                st.subheader(t("product_lines"))

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
                    hide_index=True,
                    key="pdf_items_editor"
                )

                st.info(t("manual_correct_info"))

                if invoice_type == "Purchase":
                    st.success(t("purchase_info"))
                else:
                    st.warning(t("sale_info"))

                if st.button(t("save_invoice"), type="primary", key="save_pdf_invoice"):
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
                    st.rerun()

            except Exception as error:
                st.error(t("extract_error"))
                st.exception(error)

        else:
            st.warning(t("upload_prompt"))

    else:
        st.subheader(t("manual_invoice_header"))
        st.info(t("manual_invoice_info"))

        st.subheader(t("invoice_type"))

        manual_invoice_type_display = st.selectbox(
            t("choose_invoice_type"),
            [
                t("purchase_option"),
                t("sale_option"),
            ],
            help=t("invoice_type_help"),
            key="manual_invoice_type"
        )

        if manual_invoice_type_display == t("purchase_option"):
            manual_invoice_type = "Purchase"
        else:
            manual_invoice_type = "Sale"

        if manual_invoice_type == "Purchase":
            st.success(t("purchase_info"))
        else:
            st.warning(t("sale_info"))

        st.subheader(t("structured_fields"))

        col1, col2 = st.columns(2)

        with col1:
            manual_file_name = st.text_input(
                t("manual_file_name"),
                value="Manual invoice entry",
                key="manual_file_name"
            )

            manual_document_number = st.text_input(
                t("document_number"),
                key="manual_document_number"
            )

            manual_document_date = st.text_input(
                t("document_date"),
                key="manual_document_date"
            )

            manual_total_amount = st.text_input(
                t("total_amount"),
                key="manual_total_amount"
            )

        with col2:
            manual_supplier = st.text_input(
                t("supplier"),
                key="manual_supplier"
            )

            manual_buyer = st.text_input(
                t("buyer"),
                key="manual_buyer"
            )

        st.subheader(t("manual_product_table"))

        default_manual_items = pd.DataFrame(
            [
                {
                    "product_code": "",
                    "product_name": "",
                    "quantity": 1,
                    "unit": "szt",
                    "unit_price": "",
                    "net_amount": "",
                    "vat_rate": "",
                    "vat_amount": "",
                    "gross_amount": "",
                    "line_total": "",
                    "raw_line": "",
                }
            ],
            columns=product_columns
        )

        manual_items_df = st.data_editor(
            default_manual_items,
            use_container_width=True,
            num_rows="dynamic",
            hide_index=True,
            key="manual_items_editor"
        )

        st.info(t("manual_correct_info"))

        if st.button(t("save_manual_invoice"), type="primary", key="save_manual_invoice"):
            manual_invoice_data = {
                "file_name": manual_file_name,
                "invoice_type": manual_invoice_type,
                "document_number": manual_document_number,
                "document_date": manual_document_date,
                "supplier": manual_supplier,
                "buyer": manual_buyer,
                "total_amount": manual_total_amount,
            }

            manual_line_items = manual_items_df.fillna("").to_dict("records")

            cleaned_manual_line_items = []

            for item in manual_line_items:
                product_name = str(item.get("product_name", "")).strip()
                raw_line = str(item.get("raw_line", "")).strip()

                if product_name or raw_line:
                    cleaned_manual_line_items.append(item)

            if not cleaned_manual_line_items:
                st.error(t("product_required"))
            else:
                saved_invoice_id = save_invoice(
                    invoice_data=manual_invoice_data,
                    line_items=cleaned_manual_line_items
                )

                st.success(f"{t('manual_invoice_saved')}: {saved_invoice_id}")
                st.rerun()


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
# Safety / backup and Excel export tab
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
            translate_columns(backup_df),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info(t("no_backups"))

    st.divider()

    st.subheader(t("excel_exports_header"))
    st.write(t("excel_exports_explain"))

    export_date = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")

    inventory_export_df = build_inventory_dataframe()
    invoices_export_df = build_invoice_dataframe()
    financial_export_df = build_financial_dataframe()
    manual_export_df = build_manual_adjustments_dataframe()

    st.download_button(
        label=t("download_full_excel"),
        data=build_full_excel_report(),
        file_name=f"invoiceai_full_report_{export_date}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )

    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            label=t("download_inventory_excel"),
            data=dataframe_to_excel_bytes(inventory_export_df, "Inventory"),
            file_name=f"invoiceai_inventory_{export_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        st.download_button(
            label=t("download_invoices_excel"),
            data=dataframe_to_excel_bytes(invoices_export_df, "Invoices"),
            file_name=f"invoiceai_invoices_{export_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    with col2:
        st.download_button(
            label=t("download_financial_excel"),
            data=dataframe_to_excel_bytes(financial_export_df, "Financial"),
            file_name=f"invoiceai_financial_{export_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        st.download_button(
            label=t("download_manual_excel"),
            data=dataframe_to_excel_bytes(manual_export_df, "Manual Adjustments"),
            file_name=f"invoiceai_manual_adjustments_{export_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )