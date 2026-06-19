from pathlib import Path
from io import BytesIO
import re

import pandas as pd
import streamlit as st

from database import (
    create_database_backup,
    delete_invoice,
    delete_manual_adjustment,
    get_all_invoice_items,
    get_backup_files,
    get_inventory_summary,
    get_invoice_items,
    get_invoices,
    get_manual_adjustments,
    init_db,
    save_invoice,
    save_manual_adjustment,
    update_invoice_paid_status,
    update_invoice_type,
)
from extractor import extract_invoice_fields, extract_line_items
from ocr import extract_text_from_pdf


st.set_page_config(
    page_title="Invoice Processing AI",
    page_icon="📄",
    layout="wide",
)


TEXT = {
    "EN": {
        "app_title": "📄 Invoice Processing AI + Inventory",
        "intro": (
            "Upload invoice PDFs or enter invoices manually, then track stock, "
            "extra costs, payments and financial summaries."
        ),
        "demo_note": (
            "Demo/test version. Keep original invoices and Excel exports as backup. "
            "Purchase invoices increase stock. Sale invoices decrease stock."
        ),
        "upload_tab": "📤 Add Invoice",
        "inventory_tab": "📦 Inventory",
        "financial_tab": "💷 Financial Dashboard",
        "history_tab": "📜 Invoice History",
        "adjust_tab": "🛠️ Manual Adjustments",
        "backup_tab": "🛡️ Safety / Exports",
        "upload_header": "Add and Process Invoice",
        "entry_method": "Choose invoice entry method",
        "pdf_entry": "Upload PDF invoice",
        "manual_entry": "Enter invoice manually",
        "upload_pdf": "Upload invoice PDF",
        "uploaded_saved": "Uploaded and saved",
        "view_extracted_text": "View extracted invoice text",
        "extracted_text": "Extracted text",
        "upload_prompt": "Upload a PDF invoice to begin.",
        "extract_error": "Something went wrong while extracting invoice data.",
        "invoice_type": "Invoice type",
        "choose_invoice_type": "Choose invoice type",
        "purchase_option": "Purchase invoice - stock IN / cost",
        "sale_option": "Sale invoice - stock OUT / income",
        "invoice_type_help": (
            "Purchase invoices increase stock and count as costs. "
            "Sale invoices decrease stock and count as income."
        ),
        "paid_status": "Is this invoice paid?",
        "paid_yes": "Yes",
        "paid_no": "No",
        "paid": "Paid",
        "unpaid": "Unpaid",
        "structured_fields": "Invoice details",
        "document_number": "Document number",
        "document_date": "Document date",
        "total_amount": "Total amount",
        "supplier": "Supplier",
        "buyer": "Buyer",
        "manual_file_name": "Manual entry reference",
        "product_lines": "Invoice items",
        "manual_product_table": "Invoice items",
        "manual_invoice_header": "Manual invoice entry",
        "manual_invoice_info": (
            "Add stock products, auxiliary materials, courier charges or other costs. "
            "Only stock products change inventory."
        ),
        "item_type": "Item type",
        "stock_product": "Stock product",
        "auxiliary_material": "Auxiliary material",
        "shipping_cost": "Shipping / courier",
        "other_cost": "Other cost",
        "product_code": "Product code",
        "product_name": "Product / cost name",
        "quantity": "Quantity",
        "unit": "Unit",
        "unit_price": "Unit price",
        "line_total": "Line total",
        "manual_correct_info": (
            "Choose the correct item type. Auxiliary materials, courier and other costs "
            "are included in costs but do not change stock."
        ),
        "purchase_info": "This invoice will add stock products and count as purchase cost.",
        "sale_info": "This invoice will deduct stock products and count as sales income.",
        "save_invoice": "Save invoice",
        "save_manual_invoice": "Save manual invoice",
        "invoice_saved": "Invoice saved successfully. Invoice ID",
        "manual_invoice_saved": "Manual invoice saved successfully. Invoice ID",
        "product_required": "Enter at least one product or cost name.",
        "stock_error_header": "Invoice not saved: not enough stock",
        "stock_error_explain": (
            "This sale would make one or more stock products go below zero. "
            "Auxiliary materials and extra costs are not included in stock validation."
        ),
        "stock_error_update_header": "Invoice type was not updated",
        "stock_product_label": "Product",
        "stock_code": "Code",
        "stock_unit": "Unit",
        "stock_current": "Current stock",
        "stock_requested": "Sale quantity",
        "stock_shortage": "Shortage",
        "inventory_header": "Inventory Dashboard",
        "invoices_saved": "Invoices saved",
        "products_tracked": "Products tracked",
        "total_stock_quantity": "Total stock quantity",
        "low_stock_items": "Low-stock items",
        "current_stock": "Current stock",
        "some_low_stock": "Some products have low stock.",
        "no_low_stock": "No low-stock items found.",
        "no_inventory": "No inventory data yet. Save an invoice first.",
        "financial_header": "Financial Dashboard",
        "financial_explain": (
            "Purchases are costs and sales are income. Additional costs are shown "
            "separately but are already included in invoice totals, so they are not counted twice."
        ),
        "no_financial": "No financial data yet. Save invoices first.",
        "sales_income": "Sales income",
        "purchase_costs": "Purchase costs",
        "net_result": "Net result",
        "cash_impact": "Cash impact",
        "additional_costs": "Additional costs",
        "unpaid_sales": "Unpaid sales",
        "unpaid_purchases": "Unpaid purchases",
        "financial_records": "Invoice financial records",
        "unpaid_invoices": "Unpaid invoices",
        "all_invoices_paid": "All invoices are marked as paid.",
        "monthly_summary": "Monthly summary",
        "yearly_summary": "Yearly summary",
        "profit_warning": (
            "MVP note: this is not full accounting profit. VAT, returns, cost allocation "
            "and other accounting rules may still be needed."
        ),
        "history_header": "Saved Invoice History",
        "correct_invoice_type": "Correct invoice type",
        "correct_invoice_help": "Use this if an invoice was saved as the wrong type.",
        "select_invoice_correct": "Select invoice ID",
        "new_invoice_type": "New invoice type",
        "purchase_short": "Purchase",
        "sale_short": "Sale",
        "update_invoice_type": "Update invoice type",
        "invoice_type_updated": "Invoice type updated.",
        "update_payment_status": "Update payment status",
        "select_invoice_payment": "Select invoice ID",
        "new_payment_status": "New payment status",
        "payment_status_updated": "Payment status updated.",
        "view_invoice_items": "View invoice items",
        "select_invoice_view": "Select invoice ID to view items",
        "no_items": "No items found for this invoice.",
        "delete_invoice": "Delete invoice",
        "delete_invoice_warning": (
            "Deleting an invoice also removes its product lines from inventory calculations."
        ),
        "select_invoice_delete": "Select invoice ID to delete",
        "confirm_delete_invoice": (
            "I understand this will delete the selected invoice and update inventory."
        ),
        "delete_selected_invoice": "Delete selected invoice",
        "invoice_deleted": "Invoice deleted.",
        "tick_confirm": "Tick the confirmation box before deleting.",
        "no_invoices": "No invoices saved yet.",
        "manual_header": "Manual Inventory Adjustments",
        "manual_explain": (
            "Use this for damaged items, missing stock, stock counts or products added without an invoice."
        ),
        "current_inventory_reference": "Current inventory reference",
        "add_manual_adjustment": "Add manual adjustment",
        "quantity_change": "Quantity change",
        "quantity_change_help": "Positive adds stock. Negative deducts stock.",
        "reason": "Reason",
        "reason_default": "Manual stock correction",
        "manual_example": "Example: 5 adds five items. -2 deducts two items.",
        "save_manual": "Save manual adjustment",
        "quantity_zero": "Quantity change cannot be zero.",
        "manual_saved": "Manual inventory adjustment saved.",
        "manual_history": "Manual adjustment history",
        "delete_manual": "Delete manual adjustment",
        "delete_manual_warning": "Use this only when an adjustment was added by mistake.",
        "select_manual_delete": "Select adjustment ID",
        "confirm_delete_manual": (
            "I understand this will delete the adjustment and update inventory."
        ),
        "delete_selected_manual": "Delete selected adjustment",
        "manual_deleted": "Manual adjustment deleted.",
        "no_manual": "No manual adjustments saved yet.",
        "backup_header": "Safety, Backups and Excel Exports",
        "backup_explain": (
            "Create a database backup before important changes and download Excel copies of the data."
        ),
        "backup_now": "Create backup now",
        "backup_created": "Backup created successfully",
        "latest_backups": "Latest backup files",
        "no_backups": "No backups created yet.",
        "backup_mum_note": "Create a backup before deleting invoices or making large stock corrections.",
        "excel_exports_header": "Excel exports",
        "excel_exports_explain": (
            "Download inventory, invoices, invoice items, financial summaries and manual adjustments."
        ),
        "download_full_excel": "Download full Excel report",
        "download_inventory_excel": "Download inventory Excel",
        "download_invoices_excel": "Download invoice history Excel",
        "download_items_excel": "Download invoice items Excel",
        "download_financial_excel": "Download financial summary Excel",
        "download_manual_excel": "Download manual adjustments Excel",
    },
    "PL": {
        "app_title": "📄 Invoice Processing AI + Magazyn",
        "intro": (
            "Wgraj fakturę PDF lub wpisz ją ręcznie, a następnie kontroluj magazyn, "
            "koszty dodatkowe, płatności i podsumowania finansowe."
        ),
        "demo_note": (
            "Wersja testowa. Zachowuj oryginalne faktury i eksporty Excel jako kopię. "
            "Faktury zakupowe zwiększają magazyn, a sprzedażowe go zmniejszają."
        ),
        "upload_tab": "📤 Dodaj fakturę",
        "inventory_tab": "📦 Magazyn",
        "financial_tab": "💷 Finanse",
        "history_tab": "📜 Historia faktur",
        "adjust_tab": "🛠️ Korekty ręczne",
        "backup_tab": "🛡️ Bezpieczeństwo / Eksport",
        "upload_header": "Dodaj i przetwórz fakturę",
        "entry_method": "Wybierz sposób dodania faktury",
        "pdf_entry": "Wgraj fakturę PDF",
        "manual_entry": "Wpisz fakturę ręcznie",
        "upload_pdf": "Wgraj fakturę PDF",
        "uploaded_saved": "Wgrano i zapisano",
        "view_extracted_text": "Pokaż tekst odczytany z faktury",
        "extracted_text": "Odczytany tekst",
        "upload_prompt": "Wgraj fakturę PDF, aby rozpocząć.",
        "extract_error": "Wystąpił błąd podczas odczytu faktury.",
        "invoice_type": "Typ faktury",
        "choose_invoice_type": "Wybierz typ faktury",
        "purchase_option": "Faktura zakupowa - towar DO magazynu / koszt",
        "sale_option": "Faktura sprzedażowa - towar Z magazynu / przychód",
        "invoice_type_help": (
            "Zakup zwiększa magazyn i liczy się jako koszt. "
            "Sprzedaż zmniejsza magazyn i liczy się jako przychód."
        ),
        "paid_status": "Czy faktura jest opłacona?",
        "paid_yes": "Tak",
        "paid_no": "Nie",
        "paid": "Opłacona",
        "unpaid": "Nieopłacona",
        "structured_fields": "Dane faktury",
        "document_number": "Numer dokumentu",
        "document_date": "Data dokumentu",
        "total_amount": "Kwota całkowita",
        "supplier": "Sprzedawca / dostawca",
        "buyer": "Nabywca / klient",
        "manual_file_name": "Nazwa / numer referencyjny wpisu",
        "product_lines": "Pozycje faktury",
        "manual_product_table": "Pozycje faktury",
        "manual_invoice_header": "Ręczne dodanie faktury",
        "manual_invoice_info": (
            "Dodaj towary magazynowe, materiały pomocnicze, koszt kuriera lub inny koszt. "
            "Tylko towary magazynowe zmieniają stan magazynu."
        ),
        "item_type": "Rodzaj pozycji",
        "stock_product": "Towar do magazynu",
        "auxiliary_material": "Materiał pomocniczy",
        "shipping_cost": "Wysyłka / kurier",
        "other_cost": "Inny koszt",
        "product_code": "Kod produktu",
        "product_name": "Nazwa produktu / kosztu",
        "quantity": "Ilość",
        "unit": "Jednostka",
        "unit_price": "Cena jednostkowa",
        "line_total": "Suma pozycji",
        "manual_correct_info": (
            "Wybierz prawidłowy rodzaj pozycji. Materiały pomocnicze, kurier i inne koszty "
            "liczą się jako koszty, ale nie zmieniają magazynu."
        ),
        "purchase_info": "Ta faktura doda towary magazynowe i zostanie policzona jako koszt.",
        "sale_info": "Ta faktura odejmie towary magazynowe i zostanie policzona jako przychód.",
        "save_invoice": "Zapisz fakturę",
        "save_manual_invoice": "Zapisz ręczną fakturę",
        "invoice_saved": "Faktura została zapisana. ID faktury",
        "manual_invoice_saved": "Ręczna faktura została zapisana. ID faktury",
        "product_required": "Wpisz przynajmniej jedną nazwę produktu lub kosztu.",
        "stock_error_header": "Faktura nie została zapisana: za mało towaru",
        "stock_error_explain": (
            "Ta sprzedaż spowodowałaby ujemny stan jednego lub kilku towarów. "
            "Materiały pomocnicze i koszty dodatkowe nie są objęte kontrolą magazynu."
        ),
        "stock_error_update_header": "Typ faktury nie został zaktualizowany",
        "stock_product_label": "Produkt",
        "stock_code": "Kod",
        "stock_unit": "Jednostka",
        "stock_current": "Aktualny stan",
        "stock_requested": "Ilość sprzedaży",
        "stock_shortage": "Brakująca ilość",
        "inventory_header": "Magazyn",
        "invoices_saved": "Zapisane faktury",
        "products_tracked": "Produkty w magazynie",
        "total_stock_quantity": "Łączna ilość towaru",
        "low_stock_items": "Niski stan",
        "current_stock": "Aktualny stan magazynowy",
        "some_low_stock": "Niektóre produkty mają niski stan.",
        "no_low_stock": "Brak produktów z niskim stanem.",
        "no_inventory": "Brak danych magazynowych. Najpierw zapisz fakturę.",
        "financial_header": "Panel finansowy",
        "financial_explain": (
            "Zakupy są kosztami, a sprzedaż przychodem. Koszty dodatkowe są pokazane osobno, "
            "ale są już częścią kwoty faktury, dlatego nie są liczone drugi raz."
        ),
        "no_financial": "Brak danych finansowych. Najpierw zapisz faktury.",
        "sales_income": "Przychód ze sprzedaży",
        "purchase_costs": "Koszty zakupów",
        "net_result": "Wynik netto",
        "cash_impact": "Wpływ na środki",
        "additional_costs": "Koszty dodatkowe",
        "unpaid_sales": "Nieopłacona sprzedaż",
        "unpaid_purchases": "Nieopłacone zakupy",
        "financial_records": "Zapisy finansowe faktur",
        "unpaid_invoices": "Nieopłacone faktury",
        "all_invoices_paid": "Wszystkie faktury są oznaczone jako opłacone.",
        "monthly_summary": "Podsumowanie miesięczne",
        "yearly_summary": "Podsumowanie roczne",
        "profit_warning": (
            "Uwaga MVP: to nie jest pełny zysk księgowy. Nadal mogą być potrzebne zasady VAT, "
            "zwroty, przypisanie kosztów produktu i inne zasady księgowe."
        ),
        "history_header": "Historia zapisanych faktur",
        "correct_invoice_type": "Popraw typ faktury",
        "correct_invoice_help": "Użyj tego, jeśli faktura została zapisana jako niewłaściwy typ.",
        "select_invoice_correct": "Wybierz ID faktury",
        "new_invoice_type": "Nowy typ faktury",
        "purchase_short": "Zakup",
        "sale_short": "Sprzedaż",
        "update_invoice_type": "Zaktualizuj typ faktury",
        "invoice_type_updated": "Typ faktury został zaktualizowany.",
        "update_payment_status": "Zaktualizuj status płatności",
        "select_invoice_payment": "Wybierz ID faktury",
        "new_payment_status": "Nowy status płatności",
        "payment_status_updated": "Status płatności został zaktualizowany.",
        "view_invoice_items": "Pokaż pozycje faktury",
        "select_invoice_view": "Wybierz ID faktury",
        "no_items": "Brak pozycji dla tej faktury.",
        "delete_invoice": "Usuń fakturę",
        "delete_invoice_warning": (
            "Usunięcie faktury usunie również jej pozycje z obliczeń magazynowych."
        ),
        "select_invoice_delete": "Wybierz ID faktury do usunięcia",
        "confirm_delete_invoice": (
            "Rozumiem, że faktura zostanie usunięta, a magazyn przeliczony."
        ),
        "delete_selected_invoice": "Usuń wybraną fakturę",
        "invoice_deleted": "Faktura została usunięta.",
        "tick_confirm": "Zaznacz potwierdzenie przed usunięciem.",
        "no_invoices": "Brak zapisanych faktur.",
        "manual_header": "Ręczne korekty magazynu",
        "manual_explain": (
            "Użyj tego dla uszkodzonych produktów, braków, liczenia magazynu "
            "lub produktów dodanych bez faktury."
        ),
        "current_inventory_reference": "Podgląd aktualnego magazynu",
        "add_manual_adjustment": "Dodaj ręczną korektę",
        "quantity_change": "Zmiana ilości",
        "quantity_change_help": "Liczba dodatnia dodaje towar, ujemna go odejmuje.",
        "reason": "Powód",
        "reason_default": "Ręczna korekta magazynu",
        "manual_example": "Przykład: 5 dodaje pięć sztuk, -2 odejmuje dwie sztuki.",
        "save_manual": "Zapisz ręczną korektę",
        "quantity_zero": "Zmiana ilości nie może wynosić zero.",
        "manual_saved": "Ręczna korekta została zapisana.",
        "manual_history": "Historia ręcznych korekt",
        "delete_manual": "Usuń ręczną korektę",
        "delete_manual_warning": "Użyj tego tylko, jeśli korekta została dodana przez pomyłkę.",
        "select_manual_delete": "Wybierz ID korekty",
        "confirm_delete_manual": (
            "Rozumiem, że korekta zostanie usunięta, a magazyn przeliczony."
        ),
        "delete_selected_manual": "Usuń wybraną korektę",
        "manual_deleted": "Ręczna korekta została usunięta.",
        "no_manual": "Brak zapisanych ręcznych korekt.",
        "backup_header": "Bezpieczeństwo, kopie i eksport Excel",
        "backup_explain": "Utwórz kopię bazy przed ważnymi zmianami i pobieraj dane do Excela.",
        "backup_now": "Utwórz kopię teraz",
        "backup_created": "Kopia została utworzona",
        "latest_backups": "Ostatnie kopie",
        "no_backups": "Brak utworzonych kopii.",
        "backup_mum_note": "Utwórz kopię przed usuwaniem faktur lub dużymi korektami magazynu.",
        "excel_exports_header": "Eksport do Excela",
        "excel_exports_explain": (
            "Pobierz magazyn, faktury, pozycje faktur, podsumowania finansowe i korekty."
        ),
        "download_full_excel": "Pobierz pełny raport Excel",
        "download_inventory_excel": "Pobierz magazyn Excel",
        "download_invoices_excel": "Pobierz historię faktur Excel",
        "download_items_excel": "Pobierz pozycje faktur Excel",
        "download_financial_excel": "Pobierz podsumowanie finansowe Excel",
        "download_manual_excel": "Pobierz korekty ręczne Excel",
    },
}


COLUMN_LABELS = {
    "EN": {
        "ID": "ID",
        "Invoice ID": "Invoice ID",
        "Item ID": "Item ID",
        "File Name": "File Name",
        "Type": "Type",
        "Document Number": "Document Number",
        "Date": "Date",
        "Supplier": "Supplier",
        "Buyer": "Buyer",
        "Total Amount": "Total Amount",
        "Paid Status": "Paid Status",
        "Saved At": "Saved At",
        "Item Type": "Item Type",
        "Product Code": "Product Code",
        "Product Name": "Product / Cost Name",
        "Quantity": "Quantity",
        "Unit": "Unit",
        "Unit Price": "Unit Price",
        "Net Amount": "Net Amount",
        "VAT Rate": "VAT Rate",
        "VAT Amount": "VAT Amount",
        "Gross Amount": "Gross Amount",
        "Line Total": "Line Total",
        "Raw Line": "Raw Line",
        "Current Stock": "Current Stock",
        "Sales Income": "Sales Income",
        "Purchase Cost": "Purchase Cost",
        "Net Result": "Net Result",
        "Cash Impact": "Cash Impact",
        "Additional Costs": "Additional Costs",
        "Unpaid Sales": "Unpaid Sales",
        "Unpaid Purchases": "Unpaid Purchases",
        "Month": "Month",
        "Year": "Year",
        "Quantity Change": "Quantity Change",
        "Reason": "Reason",
        "Backup File": "Backup File",
        "Created At": "Created At",
        "Size KB": "Size KB",
    },
    "PL": {
        "ID": "ID",
        "Invoice ID": "ID faktury",
        "Item ID": "ID pozycji",
        "File Name": "Nazwa pliku",
        "Type": "Typ",
        "Document Number": "Numer dokumentu",
        "Date": "Data",
        "Supplier": "Sprzedawca / dostawca",
        "Buyer": "Nabywca / klient",
        "Total Amount": "Kwota całkowita",
        "Paid Status": "Status płatności",
        "Saved At": "Zapisano",
        "Item Type": "Rodzaj pozycji",
        "Product Code": "Kod produktu",
        "Product Name": "Nazwa produktu / kosztu",
        "Quantity": "Ilość",
        "Unit": "Jednostka",
        "Unit Price": "Cena jednostkowa",
        "Net Amount": "Kwota netto",
        "VAT Rate": "Stawka VAT",
        "VAT Amount": "Kwota VAT",
        "Gross Amount": "Kwota brutto",
        "Line Total": "Suma pozycji",
        "Raw Line": "Oryginalna linia",
        "Current Stock": "Aktualny stan",
        "Sales Income": "Przychód ze sprzedaży",
        "Purchase Cost": "Koszt zakupu",
        "Net Result": "Wynik netto",
        "Cash Impact": "Wpływ na środki",
        "Additional Costs": "Koszty dodatkowe",
        "Unpaid Sales": "Nieopłacona sprzedaż",
        "Unpaid Purchases": "Nieopłacone zakupy",
        "Month": "Miesiąc",
        "Year": "Rok",
        "Quantity Change": "Zmiana ilości",
        "Reason": "Powód",
        "Backup File": "Plik kopii",
        "Created At": "Utworzono",
        "Size KB": "Rozmiar KB",
    },
}


language_choice = st.sidebar.selectbox(
    "Language / Język",
    ["Polski", "English"],
)
LANG = "PL" if language_choice == "Polski" else "EN"


def t(key):
    return TEXT[LANG].get(key, key)


def translate_columns(dataframe):
    return dataframe.rename(columns=COLUMN_LABELS[LANG])


def translate_invoice_type(value):
    if LANG == "PL":
        return {"Purchase": "Zakup", "Sale": "Sprzedaż"}.get(value, value)
    return value


def paid_display(value):
    return t("paid") if bool(value) else t("unpaid")


def item_type_display_options():
    return [
        t("stock_product"),
        t("auxiliary_material"),
        t("shipping_cost"),
        t("other_cost"),
    ]


def item_type_display_to_internal(value):
    return {
        t("stock_product"): "stock_product",
        t("auxiliary_material"): "auxiliary_material",
        t("shipping_cost"): "shipping_cost",
        t("other_cost"): "other_cost",
    }.get(value, "stock_product")


def item_type_internal_to_display(value):
    return {
        "stock_product": t("stock_product"),
        "auxiliary_material": t("auxiliary_material"),
        "shipping_cost": t("shipping_cost"),
        "other_cost": t("other_cost"),
    }.get(value, t("stock_product"))


BASE_DIR = Path(__file__).parent
INVOICES_DIR = BASE_DIR / "invoices"
INVOICES_DIR.mkdir(exist_ok=True)
init_db()


st.title(t("app_title"))
st.write(t("intro"))
st.info(t("demo_note"))


def parse_amount(value):
    if value is None:
        return 0.0

    text = str(value).strip()
    text = re.sub(r"(?i)\bPLN\b|zł|zl", "", text)
    text = text.replace(" ", "")

    if not text:
        return 0.0

    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")

    try:
        return float(text)
    except ValueError:
        return 0.0


def parse_date(value):
    return pd.to_datetime(value, dayfirst=True, errors="coerce") if value else pd.NaT


def calculate_total_from_items(items):
    return sum(parse_amount(item.get("line_total", 0)) for item in items)


def final_total_amount(entered_total, items):
    if str(entered_total).strip():
        return entered_total

    calculated = calculate_total_from_items(items)
    return f"{calculated:.2f}" if calculated else ""


def show_stock_validation_error(error, update_mode=False):
    st.error(
        t("stock_error_update_header")
        if update_mode
        else t("stock_error_header")
    )
    st.warning(t("stock_error_explain"))

    issues = getattr(error, "issues", [])

    if issues:
        issues_df = pd.DataFrame(
            [
                {
                    t("stock_code"): issue.get("product_code", ""),
                    t("stock_product_label"): issue.get("product_name", ""),
                    t("stock_unit"): issue.get("unit", ""),
                    t("stock_current"): issue.get("current_stock", 0),
                    t("stock_requested"): issue.get("requested_quantity", 0),
                    t("stock_shortage"): issue.get("shortage", 0),
                }
                for issue in issues
            ]
        )
        st.dataframe(issues_df, use_container_width=True, hide_index=True)


def handle_stock_exception(error, update_mode=False):
    if hasattr(error, "issues"):
        show_stock_validation_error(error, update_mode=update_mode)
    else:
        st.exception(error)


def build_inventory_dataframe():
    return pd.DataFrame(
        get_inventory_summary(),
        columns=[
            "Product Code",
            "Product Name",
            "Unit",
            "Current Stock",
        ],
    )


def build_invoice_dataframe():
    return pd.DataFrame(
        get_invoices(),
        columns=[
            "ID",
            "File Name",
            "Type",
            "Document Number",
            "Date",
            "Supplier",
            "Buyer",
            "Total Amount",
            "Is Paid",
            "Saved At",
        ],
    )


def build_invoice_items_dataframe():
    return pd.DataFrame(
        get_all_invoice_items(),
        columns=[
            "Item ID",
            "Invoice ID",
            "Document Number",
            "Type",
            "Item Type",
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
        ],
    )


def build_manual_adjustments_dataframe():
    return pd.DataFrame(
        get_manual_adjustments(),
        columns=[
            "ID",
            "Product Code",
            "Product Name",
            "Quantity Change",
            "Unit",
            "Reason",
            "Saved At",
        ],
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
    financial_df["Paid Status"] = financial_df["Is Paid"].apply(paid_display)

    financial_df["Sales Income"] = financial_df.apply(
        lambda row: row["Amount Number"] if row["Type"] == "Sale" else 0.0,
        axis=1,
    )
    financial_df["Purchase Cost"] = financial_df.apply(
        lambda row: row["Amount Number"] if row["Type"] == "Purchase" else 0.0,
        axis=1,
    )
    financial_df["Net Result"] = (
        financial_df["Sales Income"] - financial_df["Purchase Cost"]
    )
    financial_df["Cash Impact"] = financial_df.apply(
        lambda row: row["Amount Number"] if row["Type"] == "Sale" else -row["Amount Number"],
        axis=1,
    )
    financial_df["Unpaid Sales"] = financial_df.apply(
        lambda row: row["Amount Number"]
        if row["Type"] == "Sale" and not bool(row["Is Paid"])
        else 0.0,
        axis=1,
    )
    financial_df["Unpaid Purchases"] = financial_df.apply(
        lambda row: row["Amount Number"]
        if row["Type"] == "Purchase" and not bool(row["Is Paid"])
        else 0.0,
        axis=1,
    )

    items_df = build_invoice_items_dataframe()

    if items_df.empty:
        financial_df["Additional Costs"] = 0.0
    else:
        items_df["Line Amount"] = items_df["Line Total"].apply(parse_amount)
        extra_df = items_df[
            items_df["Item Type"].isin(
                {"auxiliary_material", "shipping_cost", "other_cost"}
            )
        ]

        extra_by_invoice = (
            extra_df.groupby("Invoice ID")["Line Amount"]
            .sum()
            .rename("Additional Costs")
        )

        financial_df = financial_df.merge(
            extra_by_invoice,
            how="left",
            left_on="ID",
            right_index=True,
        )
        financial_df["Additional Costs"] = financial_df["Additional Costs"].fillna(0.0)
        financial_df.loc[
            financial_df["Type"] != "Purchase",
            "Additional Costs",
        ] = 0.0

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
    items_df = build_invoice_items_dataframe()
    financial_df = build_financial_dataframe()
    manual_df = build_manual_adjustments_dataframe()

    if not invoices_df.empty:
        invoices_df = invoices_df.copy()
        invoices_df["Paid Status"] = invoices_df["Is Paid"].apply(paid_display)

    if not items_df.empty:
        items_df = items_df.copy()
        items_df["Item Type"] = items_df["Item Type"].apply(item_type_internal_to_display)

    if not financial_df.empty:
        summary_columns = [
            "Sales Income",
            "Purchase Cost",
            "Net Result",
            "Cash Impact",
            "Additional Costs",
            "Unpaid Sales",
            "Unpaid Purchases",
        ]
        monthly_summary = (
            financial_df.groupby("Month", dropna=False)[summary_columns]
            .sum()
            .reset_index()
        )
        yearly_summary = (
            financial_df.groupby("Year", dropna=False)[summary_columns]
            .sum()
            .reset_index()
        )
        unpaid_df = financial_df[~financial_df["Is Paid"].astype(bool)].copy()
    else:
        monthly_summary = pd.DataFrame()
        yearly_summary = pd.DataFrame()
        unpaid_df = pd.DataFrame()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        inventory_df.to_excel(writer, index=False, sheet_name="Inventory")
        invoices_df.to_excel(writer, index=False, sheet_name="Invoices")
        items_df.to_excel(writer, index=False, sheet_name="Invoice Items")
        financial_df.to_excel(writer, index=False, sheet_name="Financial Records")
        unpaid_df.to_excel(writer, index=False, sheet_name="Unpaid Invoices")
        monthly_summary.to_excel(writer, index=False, sheet_name="Monthly Summary")
        yearly_summary.to_excel(writer, index=False, sheet_name="Yearly Summary")
        manual_df.to_excel(writer, index=False, sheet_name="Manual Adjustments")

    output.seek(0)
    return output


def item_editor_column_config():
    return {
        "item_type": st.column_config.SelectboxColumn(
            t("item_type"),
            options=item_type_display_options(),
            required=True,
        ),
        "product_code": st.column_config.TextColumn(t("product_code")),
        "product_name": st.column_config.TextColumn(t("product_name"), required=True),
        "quantity": st.column_config.NumberColumn(
            t("quantity"),
            min_value=0.0,
            step=1.0,
        ),
        "unit": st.column_config.TextColumn(t("unit")),
        "unit_price": st.column_config.NumberColumn(
            t("unit_price"),
            min_value=0.0,
            format="%.2f",
        ),
        "line_total": st.column_config.NumberColumn(
            t("line_total"),
            min_value=0.0,
            format="%.2f",
        ),
    }


def prepare_editor_dataframe(line_items=None):
    rows = []

    if line_items:
        for item in line_items:
            rows.append(
                {
                    "item_type": t("stock_product"),
                    "product_code": item.get("product_code", ""),
                    "product_name": item.get("product_name", "") or item.get("raw_line", ""),
                    "quantity": parse_amount(item.get("quantity", 1)) or 1,
                    "unit": item.get("unit", "szt") or "szt",
                    "unit_price": parse_amount(item.get("unit_price", 0)),
                    "line_total": (
                        parse_amount(item.get("line_total", 0))
                        or parse_amount(item.get("gross_amount", 0))
                        or parse_amount(item.get("net_amount", 0))
                    ),
                }
            )

    if not rows:
        rows = [
            {
                "item_type": t("stock_product"),
                "product_code": "",
                "product_name": "",
                "quantity": 1.0,
                "unit": "szt",
                "unit_price": 0.0,
                "line_total": 0.0,
            }
        ]

    return pd.DataFrame(rows)


def editor_rows_to_database_items(editor_df):
    items = []

    for row in editor_df.fillna("").to_dict("records"):
        product_name = str(row.get("product_name", "")).strip()

        if not product_name:
            continue

        items.append(
            {
                "item_type": item_type_display_to_internal(row.get("item_type", "")),
                "product_code": row.get("product_code", ""),
                "product_name": product_name,
                "quantity": row.get("quantity", 0),
                "unit": row.get("unit", ""),
                "unit_price": row.get("unit_price", ""),
                "net_amount": "",
                "vat_rate": "",
                "vat_amount": "",
                "gross_amount": "",
                "line_total": row.get("line_total", ""),
                "raw_line": "",
            }
        )

    return items


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


with tab_upload:
    st.header(t("upload_header"))

    entry_method = st.radio(
        t("entry_method"),
        [t("pdf_entry"), t("manual_entry")],
        horizontal=True,
    )

    if entry_method == t("pdf_entry"):
        uploaded_file = st.file_uploader(t("upload_pdf"), type=["pdf"])

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
                    st.text_area(t("extracted_text"), extracted_text, height=300)

                invoice_type_display = st.selectbox(
                    t("choose_invoice_type"),
                    [t("purchase_option"), t("sale_option")],
                    help=t("invoice_type_help"),
                    key="pdf_invoice_type",
                )
                invoice_type = (
                    "Purchase"
                    if invoice_type_display == t("purchase_option")
                    else "Sale"
                )

                paid_choice = st.selectbox(
                    t("paid_status"),
                    [t("paid_no"), t("paid_yes")],
                    key="pdf_paid_status",
                )

                col1, col2 = st.columns(2)

                with col1:
                    document_number = st.text_input(
                        t("document_number"),
                        value=extracted_fields.get("document_number", ""),
                        key="pdf_document_number",
                    )
                    document_date = st.text_input(
                        t("document_date"),
                        value=extracted_fields.get("document_date", ""),
                        key="pdf_document_date",
                    )
                    total_amount = st.text_input(
                        t("total_amount"),
                        value=extracted_fields.get("total_amount", ""),
                        key="pdf_total_amount",
                    )

                with col2:
                    supplier = st.text_input(
                        t("supplier"),
                        value=extracted_fields.get("supplier", ""),
                        key="pdf_supplier",
                    )
                    buyer = st.text_input(
                        t("buyer"),
                        value=extracted_fields.get("buyer", ""),
                        key="pdf_buyer",
                    )

                st.subheader(t("product_lines"))

                edited_items_df = st.data_editor(
                    prepare_editor_dataframe(line_items),
                    use_container_width=True,
                    num_rows="dynamic",
                    hide_index=True,
                    column_config=item_editor_column_config(),
                    key="pdf_items_editor",
                )

                st.info(t("manual_correct_info"))
                if invoice_type == "Purchase":
                    st.success(t("purchase_info"))
                else:
                    st.warning(t("sale_info"))

                if st.button(t("save_invoice"), type="primary", key="save_pdf_invoice"):
                    prepared_items = editor_rows_to_database_items(edited_items_df)

                    if not prepared_items:
                        st.error(t("product_required"))
                    else:
                        invoice_data = {
                            "file_name": uploaded_file.name,
                            "invoice_type": invoice_type,
                            "document_number": document_number,
                            "document_date": document_date,
                            "supplier": supplier,
                            "buyer": buyer,
                            "total_amount": final_total_amount(total_amount, prepared_items),
                            "is_paid": paid_choice == t("paid_yes"),
                        }

                        try:
                            invoice_id = save_invoice(invoice_data, prepared_items)
                            st.success(f"{t('invoice_saved')}: {invoice_id}")
                        except Exception as error:
                            handle_stock_exception(error)

            except Exception as error:
                st.error(t("extract_error"))
                st.exception(error)
        else:
            st.warning(t("upload_prompt"))

    else:
        st.subheader(t("manual_invoice_header"))
        st.info(t("manual_invoice_info"))

        invoice_type_display = st.selectbox(
            t("choose_invoice_type"),
            [t("purchase_option"), t("sale_option")],
            help=t("invoice_type_help"),
            key="manual_invoice_type",
        )
        invoice_type = (
            "Purchase"
            if invoice_type_display == t("purchase_option")
            else "Sale"
        )

        paid_choice = st.selectbox(
            t("paid_status"),
            [t("paid_no"), t("paid_yes")],
            key="manual_paid_status",
        )

        if invoice_type == "Purchase":
            st.success(t("purchase_info"))
        else:
            st.warning(t("sale_info"))

        col1, col2 = st.columns(2)

        with col1:
            manual_file_name = st.text_input(
                t("manual_file_name"),
                value="Manual invoice entry",
                key="manual_file_name",
            )
            manual_document_number = st.text_input(
                t("document_number"),
                key="manual_document_number",
            )
            manual_document_date = st.text_input(
                t("document_date"),
                key="manual_document_date",
            )
            manual_total_amount = st.text_input(
                t("total_amount"),
                key="manual_total_amount",
            )

        with col2:
            manual_supplier = st.text_input(
                t("supplier"),
                key="manual_supplier",
            )
            manual_buyer = st.text_input(
                t("buyer"),
                key="manual_buyer",
            )

        st.subheader(t("manual_product_table"))

        manual_items_df = st.data_editor(
            prepare_editor_dataframe(),
            use_container_width=True,
            num_rows="dynamic",
            hide_index=True,
            column_config=item_editor_column_config(),
            key="manual_items_editor",
        )

        st.info(t("manual_correct_info"))

        if st.button(
            t("save_manual_invoice"),
            type="primary",
            key="save_manual_invoice",
        ):
            prepared_items = editor_rows_to_database_items(manual_items_df)

            if not prepared_items:
                st.error(t("product_required"))
            else:
                invoice_data = {
                    "file_name": manual_file_name,
                    "invoice_type": invoice_type,
                    "document_number": manual_document_number,
                    "document_date": manual_document_date,
                    "supplier": manual_supplier,
                    "buyer": manual_buyer,
                    "total_amount": final_total_amount(
                        manual_total_amount,
                        prepared_items,
                    ),
                    "is_paid": paid_choice == t("paid_yes"),
                }

                try:
                    invoice_id = save_invoice(invoice_data, prepared_items)
                    st.success(f"{t('manual_invoice_saved')}: {invoice_id}")
                except Exception as error:
                    handle_stock_exception(error)


with tab_inventory:
    st.header(t("inventory_header"))

    inventory_df = build_inventory_dataframe()
    invoices_df = build_invoice_dataframe()

    total_stock = inventory_df["Current Stock"].sum() if not inventory_df.empty else 0
    low_stock_df = (
        inventory_df[inventory_df["Current Stock"] <= 5]
        if not inventory_df.empty
        else inventory_df
    )

    card1, card2, card3, card4 = st.columns(4)
    card1.metric(t("invoices_saved"), len(invoices_df))
    card2.metric(t("products_tracked"), len(inventory_df))
    card3.metric(t("total_stock_quantity"), total_stock)
    card4.metric(t("low_stock_items"), len(low_stock_df))

    st.divider()
    st.subheader(t("current_stock"))

    if inventory_df.empty:
        st.info(t("no_inventory"))
    else:
        st.dataframe(
            translate_columns(inventory_df),
            use_container_width=True,
            hide_index=True,
        )

        st.subheader(t("low_stock_items"))

        if low_stock_df.empty:
            st.success(t("no_low_stock"))
        else:
            st.warning(t("some_low_stock"))
            st.dataframe(
                translate_columns(low_stock_df),
                use_container_width=True,
                hide_index=True,
            )


with tab_financial:
    st.header(t("financial_header"))
    st.write(t("financial_explain"))

    financial_df = build_financial_dataframe()

    if financial_df.empty:
        st.info(t("no_financial"))
    else:
        total_sales = financial_df["Sales Income"].sum()
        total_purchases = financial_df["Purchase Cost"].sum()
        net_result = financial_df["Net Result"].sum()
        cash_impact = financial_df["Cash Impact"].sum()
        additional_costs = financial_df["Additional Costs"].sum()
        unpaid_sales = financial_df["Unpaid Sales"].sum()
        unpaid_purchases = financial_df["Unpaid Purchases"].sum()

        row1 = st.columns(4)
        row1[0].metric(t("sales_income"), f"{total_sales:,.2f} PLN")
        row1[1].metric(t("purchase_costs"), f"{total_purchases:,.2f} PLN")
        row1[2].metric(t("net_result"), f"{net_result:,.2f} PLN")
        row1[3].metric(t("cash_impact"), f"{cash_impact:,.2f} PLN")

        row2 = st.columns(3)
        row2[0].metric(t("additional_costs"), f"{additional_costs:,.2f} PLN")
        row2[1].metric(t("unpaid_sales"), f"{unpaid_sales:,.2f} PLN")
        row2[2].metric(t("unpaid_purchases"), f"{unpaid_purchases:,.2f} PLN")

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
            "Paid Status",
            "Sales Income",
            "Purchase Cost",
            "Additional Costs",
            "Net Result",
            "Cash Impact",
        ]

        display_df = financial_df[display_columns].copy()
        display_df["Type"] = display_df["Type"].apply(translate_invoice_type)

        st.dataframe(
            translate_columns(display_df),
            use_container_width=True,
            hide_index=True,
        )

        st.subheader(t("unpaid_invoices"))
        unpaid_df = financial_df[~financial_df["Is Paid"].astype(bool)].copy()

        if unpaid_df.empty:
            st.success(t("all_invoices_paid"))
        else:
            unpaid_display = unpaid_df[
                [
                    "ID",
                    "Type",
                    "Document Number",
                    "Date",
                    "Supplier",
                    "Buyer",
                    "Total Amount",
                    "Paid Status",
                ]
            ].copy()
            unpaid_display["Type"] = unpaid_display["Type"].apply(
                translate_invoice_type
            )
            st.dataframe(
                translate_columns(unpaid_display),
                use_container_width=True,
                hide_index=True,
            )

        summary_columns = [
            "Sales Income",
            "Purchase Cost",
            "Additional Costs",
            "Net Result",
            "Cash Impact",
            "Unpaid Sales",
            "Unpaid Purchases",
        ]

        st.subheader(t("monthly_summary"))
        monthly_summary = (
            financial_df.groupby("Month", dropna=False)[summary_columns]
            .sum()
            .reset_index()
        )
        st.dataframe(
            translate_columns(monthly_summary),
            use_container_width=True,
            hide_index=True,
        )

        st.subheader(t("yearly_summary"))
        yearly_summary = (
            financial_df.groupby("Year", dropna=False)[summary_columns]
            .sum()
            .reset_index()
        )
        st.dataframe(
            translate_columns(yearly_summary),
            use_container_width=True,
            hide_index=True,
        )

        st.warning(t("profit_warning"))


with tab_history:
    st.header(t("history_header"))

    invoices_df = build_invoice_dataframe()

    if invoices_df.empty:
        st.info(t("no_invoices"))
    else:
        display_invoices = invoices_df.copy()
        display_invoices["Type"] = display_invoices["Type"].apply(
            translate_invoice_type
        )
        display_invoices["Paid Status"] = display_invoices["Is Paid"].apply(
            paid_display
        )
        display_invoices = display_invoices.drop(columns=["Is Paid"])

        st.dataframe(
            translate_columns(display_invoices),
            use_container_width=True,
            hide_index=True,
        )

        invoice_ids = invoices_df["ID"].tolist()
        col_type, col_payment = st.columns(2)

        with col_type:
            st.subheader(t("correct_invoice_type"))
            st.write(t("correct_invoice_help"))

            correction_invoice_id = st.selectbox(
                t("select_invoice_correct"),
                invoice_ids,
                key="correction_invoice_id",
            )
            corrected_type_display = st.selectbox(
                t("new_invoice_type"),
                [t("purchase_short"), t("sale_short")],
                key="corrected_type",
            )
            corrected_type = (
                "Purchase"
                if corrected_type_display == t("purchase_short")
                else "Sale"
            )

            if st.button(t("update_invoice_type")):
                try:
                    update_invoice_type(
                        correction_invoice_id,
                        corrected_type,
                    )
                    st.success(t("invoice_type_updated"))
                    st.rerun()
                except Exception as error:
                    handle_stock_exception(error, update_mode=True)

        with col_payment:
            st.subheader(t("update_payment_status"))

            payment_invoice_id = st.selectbox(
                t("select_invoice_payment"),
                invoice_ids,
                key="payment_invoice_id",
            )
            payment_status_display = st.selectbox(
                t("new_payment_status"),
                [t("paid_no"), t("paid_yes")],
                key="new_payment_status",
            )

            if st.button(t("update_payment_status")):
                update_invoice_paid_status(
                    payment_invoice_id,
                    payment_status_display == t("paid_yes"),
                )
                st.success(t("payment_status_updated"))
                st.rerun()

        st.divider()
        st.subheader(t("view_invoice_items"))

        selected_invoice_id = st.selectbox(
            t("select_invoice_view"),
            invoice_ids,
            key="view_invoice_id",
        )

        item_rows = get_invoice_items(selected_invoice_id)

        if item_rows:
            items_df = pd.DataFrame(
                item_rows,
                columns=[
                    "Item ID",
                    "Item Type",
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
                ],
            )
            items_df["Item Type"] = items_df["Item Type"].apply(
                item_type_internal_to_display
            )

            st.dataframe(
                translate_columns(items_df),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info(t("no_items"))

        st.divider()
        st.subheader(t("delete_invoice"))
        st.warning(t("delete_invoice_warning"))

        delete_invoice_id = st.selectbox(
            t("select_invoice_delete"),
            invoice_ids,
            key="delete_invoice_id",
        )
        confirm_delete = st.checkbox(
            t("confirm_delete_invoice"),
            key="confirm_delete_invoice",
        )

        if st.button(t("delete_selected_invoice")):
            if confirm_delete:
                delete_invoice(delete_invoice_id)
                st.success(t("invoice_deleted"))
                st.rerun()
            else:
                st.error(t("tick_confirm"))


with tab_adjust:
    st.header(t("manual_header"))
    st.write(t("manual_explain"))

    inventory_df = build_inventory_dataframe()

    st.subheader(t("current_inventory_reference"))

    if inventory_df.empty:
        st.info(t("no_inventory"))
    else:
        st.dataframe(
            translate_columns(inventory_df),
            use_container_width=True,
            hide_index=True,
        )

    st.subheader(t("add_manual_adjustment"))
    col1, col2 = st.columns(2)

    with col1:
        product_code = st.text_input(
            t("product_code"),
            key="adjust_product_code",
        )
        product_name = st.text_input(
            t("product_name"),
            key="adjust_product_name",
        )
        unit = st.text_input(
            t("unit"),
            value="szt",
            key="adjust_unit",
        )

    with col2:
        quantity_change = st.number_input(
            t("quantity_change"),
            value=0.0,
            step=1.0,
            help=t("quantity_change_help"),
        )
        reason = st.text_input(
            t("reason"),
            value=t("reason_default"),
        )

    st.info(t("manual_example"))

    if st.button(t("save_manual"), type="primary"):
        if not product_name.strip():
            st.error(t("product_required"))
        elif quantity_change == 0:
            st.error(t("quantity_zero"))
        else:
            save_manual_adjustment(
                product_code,
                product_name,
                quantity_change,
                unit,
                reason,
            )
            st.success(t("manual_saved"))
            st.rerun()

    st.divider()
    st.subheader(t("manual_history"))

    adjustments_df = build_manual_adjustments_dataframe()

    if adjustments_df.empty:
        st.info(t("no_manual"))
    else:
        st.dataframe(
            translate_columns(adjustments_df),
            use_container_width=True,
            hide_index=True,
        )

        st.subheader(t("delete_manual"))
        st.warning(t("delete_manual_warning"))

        selected_adjustment_id = st.selectbox(
            t("select_manual_delete"),
            adjustments_df["ID"].tolist(),
            key="delete_adjustment_id",
        )
        confirm_delete_adjustment = st.checkbox(
            t("confirm_delete_manual"),
            key="confirm_delete_adjustment",
        )

        if st.button(t("delete_selected_manual")):
            if confirm_delete_adjustment:
                delete_manual_adjustment(selected_adjustment_id)
                st.success(t("manual_deleted"))
                st.rerun()
            else:
                st.error(t("tick_confirm"))


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
                    "Backup File": file.name,
                    "Created At": pd.to_datetime(
                        file.stat().st_mtime,
                        unit="s",
                    ).strftime("%Y-%m-%d %H:%M:%S"),
                    "Size KB": round(file.stat().st_size / 1024, 2),
                }
                for file in backup_files[:10]
            ]
        )
        st.dataframe(
            translate_columns(backup_df),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info(t("no_backups"))

    st.divider()
    st.subheader(t("excel_exports_header"))
    st.write(t("excel_exports_explain"))

    export_date = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    inventory_export = build_inventory_dataframe()
    invoices_export = build_invoice_dataframe()
    items_export = build_invoice_items_dataframe()
    financial_export = build_financial_dataframe()
    manual_export = build_manual_adjustments_dataframe()

    if not invoices_export.empty:
        invoices_export = invoices_export.copy()
        invoices_export["Paid Status"] = invoices_export["Is Paid"].apply(
            paid_display
        )

    if not items_export.empty:
        items_export = items_export.copy()
        items_export["Item Type"] = items_export["Item Type"].apply(
            item_type_internal_to_display
        )

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
            data=dataframe_to_excel_bytes(inventory_export, "Inventory"),
            file_name=f"invoiceai_inventory_{export_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.download_button(
            label=t("download_invoices_excel"),
            data=dataframe_to_excel_bytes(invoices_export, "Invoices"),
            file_name=f"invoiceai_invoices_{export_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.download_button(
            label=t("download_items_excel"),
            data=dataframe_to_excel_bytes(items_export, "Invoice Items"),
            file_name=f"invoiceai_invoice_items_{export_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    with col2:
        st.download_button(
            label=t("download_financial_excel"),
            data=dataframe_to_excel_bytes(financial_export, "Financial"),
            file_name=f"invoiceai_financial_{export_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.download_button(
            label=t("download_manual_excel"),
            data=dataframe_to_excel_bytes(manual_export, "Manual Adjustments"),
            file_name=f"invoiceai_manual_adjustments_{export_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
