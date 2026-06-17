import sqlite3
from pathlib import Path
from datetime import datetime


BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "invoice_ai.db"


def connect_db():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT,
            invoice_type TEXT,
            document_number TEXT,
            document_date TEXT,
            supplier TEXT,
            buyer TEXT,
            total_amount TEXT,
            created_at TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER,
            product_code TEXT,
            product_name TEXT,
            quantity REAL,
            unit TEXT,
            unit_price TEXT,
            net_amount TEXT,
            vat_rate TEXT,
            vat_amount TEXT,
            gross_amount TEXT,
            line_total TEXT,
            raw_line TEXT,
            FOREIGN KEY(invoice_id) REFERENCES invoices(id)
        )
        """
    )

    conn.commit()
    conn.close()


def convert_quantity(value):
    if value is None:
        return 0

    value = str(value).strip()

    if value == "":
        return 0

    value = value.replace(",", ".")

    try:
        return float(value)
    except ValueError:
        return 0


def save_invoice(invoice_data, line_items):
    init_db()

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO invoices (
            file_name,
            invoice_type,
            document_number,
            document_date,
            supplier,
            buyer,
            total_amount,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            invoice_data.get("file_name", ""),
            invoice_data.get("invoice_type", ""),
            invoice_data.get("document_number", ""),
            invoice_data.get("document_date", ""),
            invoice_data.get("supplier", ""),
            invoice_data.get("buyer", ""),
            invoice_data.get("total_amount", ""),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )

    invoice_id = cursor.lastrowid

    for item in line_items:
        product_name = str(item.get("product_name", "")).strip()
        raw_line = str(item.get("raw_line", "")).strip()

        if not product_name and raw_line:
            product_name = raw_line

        if not product_name:
            continue

        cursor.execute(
            """
            INSERT INTO invoice_items (
                invoice_id,
                product_code,
                product_name,
                quantity,
                unit,
                unit_price,
                net_amount,
                vat_rate,
                vat_amount,
                gross_amount,
                line_total,
                raw_line
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                invoice_id,
                item.get("product_code", ""),
                product_name,
                convert_quantity(item.get("quantity", 0)),
                item.get("unit", ""),
                item.get("unit_price", ""),
                item.get("net_amount", ""),
                item.get("vat_rate", ""),
                item.get("vat_amount", ""),
                item.get("gross_amount", ""),
                item.get("line_total", ""),
                raw_line,
            ),
        )

    conn.commit()
    conn.close()

    return invoice_id


def get_invoices():
    init_db()

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            file_name,
            invoice_type,
            document_number,
            document_date,
            supplier,
            buyer,
            total_amount,
            created_at
        FROM invoices
        ORDER BY id DESC
        """
    )

    rows = cursor.fetchall()
    conn.close()

    return rows


def get_inventory_summary():
    init_db()

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            ii.product_code,
            ii.product_name,
            ii.unit,
            SUM(
                CASE
                    WHEN i.invoice_type = 'Purchase' THEN ii.quantity
                    WHEN i.invoice_type = 'Sale' THEN -ii.quantity
                    ELSE ii.quantity
                END
            ) AS current_stock
        FROM invoice_items ii
        JOIN invoices i ON ii.invoice_id = i.id
        GROUP BY ii.product_code, ii.product_name, ii.unit
        ORDER BY ii.product_name
        """
    )

    rows = cursor.fetchall()
    conn.close()

    return rows