import sqlite3
from pathlib import Path
from datetime import datetime


# --------------------------------------------------
# Database setup
# --------------------------------------------------

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

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory_adjustments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_code TEXT,
            product_name TEXT,
            quantity_change REAL,
            unit TEXT,
            reason TEXT,
            created_at TEXT
        )
        """
    )

    conn.commit()
    conn.close()


# --------------------------------------------------
# Helper functions
# --------------------------------------------------

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


# --------------------------------------------------
# Save invoice and invoice items
# --------------------------------------------------

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
        product_code = str(item.get("product_code", "")).strip()
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
                product_code,
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


# --------------------------------------------------
# Read invoice data
# --------------------------------------------------

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


def get_invoice_items(invoice_id):
    init_db()

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
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
        FROM invoice_items
        WHERE invoice_id = ?
        ORDER BY id
        """,
        (invoice_id,),
    )

    rows = cursor.fetchall()
    conn.close()

    return rows


# --------------------------------------------------
# Update and delete invoices
# --------------------------------------------------

def update_invoice_type(invoice_id, new_invoice_type):
    init_db()

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE invoices
        SET invoice_type = ?
        WHERE id = ?
        """,
        (
            new_invoice_type,
            invoice_id,
        ),
    )

    conn.commit()
    conn.close()


def delete_invoice(invoice_id):
    init_db()

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM invoice_items
        WHERE invoice_id = ?
        """,
        (invoice_id,),
    )

    cursor.execute(
        """
        DELETE FROM invoices
        WHERE id = ?
        """,
        (invoice_id,),
    )

    conn.commit()
    conn.close()


# --------------------------------------------------
# Manual inventory adjustments
# --------------------------------------------------

def save_manual_adjustment(product_code, product_name, quantity_change, unit, reason):
    init_db()

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO inventory_adjustments (
            product_code,
            product_name,
            quantity_change,
            unit,
            reason,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            str(product_code).strip(),
            str(product_name).strip(),
            convert_quantity(quantity_change),
            str(unit).strip(),
            str(reason).strip(),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )

    conn.commit()
    conn.close()


def get_manual_adjustments():
    init_db()

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            product_code,
            product_name,
            quantity_change,
            unit,
            reason,
            created_at
        FROM inventory_adjustments
        ORDER BY id DESC
        """
    )

    rows = cursor.fetchall()
    conn.close()

    return rows


def delete_manual_adjustment(adjustment_id):
    init_db()

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM inventory_adjustments
        WHERE id = ?
        """,
        (adjustment_id,),
    )

    conn.commit()
    conn.close()


# --------------------------------------------------
# Inventory calculation
# --------------------------------------------------

def get_inventory_summary():
    """
    Calculates current stock.

    Purchase invoice = stock increases.
    Sale invoice = stock decreases.
    Manual adjustments can increase or decrease stock.
    """

    init_db()

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            i.invoice_type,
            ii.product_code,
            ii.product_name,
            ii.quantity,
            ii.unit
        FROM invoice_items ii
        JOIN invoices i ON ii.invoice_id = i.id
        """
    )

    invoice_rows = cursor.fetchall()

    cursor.execute(
        """
        SELECT
            product_code,
            product_name,
            quantity_change,
            unit
        FROM inventory_adjustments
        """
    )

    adjustment_rows = cursor.fetchall()

    conn.close()

    inventory = {}

    for invoice_type, product_code, product_name, quantity, unit in invoice_rows:
        product_code = product_code or ""
        product_name = product_name or ""
        unit = unit or ""

        key = (product_code, product_name, unit)

        if key not in inventory:
            inventory[key] = 0

        quantity = convert_quantity(quantity)

        if invoice_type == "Purchase":
            inventory[key] += quantity
        elif invoice_type == "Sale":
            inventory[key] -= quantity
        else:
            inventory[key] += quantity

    for product_code, product_name, quantity_change, unit in adjustment_rows:
        product_code = product_code or ""
        product_name = product_name or ""
        unit = unit or ""

        key = (product_code, product_name, unit)

        if key not in inventory:
            inventory[key] = 0

        inventory[key] += convert_quantity(quantity_change)

    rows = []

    for (product_code, product_name, unit), current_stock in inventory.items():
        rows.append(
            (
                product_code,
                product_name,
                unit,
                current_stock,
            )
        )

    rows.sort(key=lambda row: row[1])

    return rows