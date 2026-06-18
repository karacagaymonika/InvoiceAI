import sqlite3
import shutil
from pathlib import Path
from datetime import datetime


# --------------------------------------------------
# Database setup
# --------------------------------------------------

BASE_DIR = Path(__file__).parent

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

BACKUP_DIR = BASE_DIR / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

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
# Custom safety error
# --------------------------------------------------

class StockValidationError(ValueError):
    """
    Raised when a sale invoice would make stock go below zero.
    """

    def __init__(self, issues):
        self.issues = issues
        message = format_stock_validation_error(issues)
        super().__init__(message)


def format_stock_validation_error(issues):
    if not issues:
        return ""

    lines = [
        "Not enough stock for this sale invoice.",
        "Please check these product quantities before saving:",
    ]

    for issue in issues:
        product_name = issue.get("product_name", "")
        product_code = issue.get("product_code", "")
        unit = issue.get("unit", "")
        current_stock = issue.get("current_stock", 0)
        requested_quantity = issue.get("requested_quantity", 0)
        shortage = issue.get("shortage", 0)

        label_parts = []

        if product_code:
            label_parts.append(f"Code: {product_code}")

        if product_name:
            label_parts.append(f"Product: {product_name}")

        if unit:
            label_parts.append(f"Unit: {unit}")

        product_label = " | ".join(label_parts)

        lines.append(
            f"- {product_label}: current stock {current_stock}, "
            f"sale quantity {requested_quantity}, shortage {shortage}"
        )

    return "\n".join(lines)


# --------------------------------------------------
# Backup functions
# --------------------------------------------------

def create_database_backup(reason="manual"):
    """
    Creates a timestamped backup copy of the SQLite database.

    reason examples:
    - manual
    - before_save_invoice
    - before_delete_invoice
    - before_manual_adjustment
    - before_delete_adjustment
    """

    init_db()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_reason = str(reason).strip().replace(" ", "_").lower()

    backup_file = BACKUP_DIR / f"invoice_ai_backup_{safe_reason}_{timestamp}.db"

    shutil.copy2(DB_PATH, backup_file)

    return backup_file


def get_backup_files():
    """
    Returns a list of backup database files.
    Newest backups are shown first.
    """

    BACKUP_DIR.mkdir(exist_ok=True)

    backup_files = sorted(
        BACKUP_DIR.glob("invoice_ai_backup_*.db"),
        key=lambda file: file.stat().st_mtime,
        reverse=True,
    )

    return backup_files


# --------------------------------------------------
# Helper functions
# --------------------------------------------------

def clean_text(value):
    if value is None:
        return ""

    return str(value).strip()


def normalize_key_value(value):
    value = clean_text(value)
    value = " ".join(value.split())
    return value.lower()


def make_inventory_key(product_code, product_name, unit):
    """
    Creates a consistent key for matching products.

    This helps match products even if there are small differences in spacing
    or capital letters.
    """

    return (
        normalize_key_value(product_code),
        normalize_key_value(product_name),
        normalize_key_value(unit),
    )


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


def normalise_invoice_quantity(value):
    """
    Purchase and sale invoice quantities should be stored as positive numbers.
    Sale logic deducts the quantity later during inventory calculation.
    """

    quantity = convert_quantity(value)

    if quantity < 0:
        quantity = abs(quantity)

    return quantity


def prepare_line_item_for_save(item):
    product_code = clean_text(item.get("product_code", ""))
    product_name = clean_text(item.get("product_name", ""))
    raw_line = clean_text(item.get("raw_line", ""))

    if not product_name and raw_line:
        product_name = raw_line

    return {
        "product_code": product_code,
        "product_name": product_name,
        "quantity": normalise_invoice_quantity(item.get("quantity", 0)),
        "unit": clean_text(item.get("unit", "")),
        "unit_price": item.get("unit_price", ""),
        "net_amount": item.get("net_amount", ""),
        "vat_rate": item.get("vat_rate", ""),
        "vat_amount": item.get("vat_amount", ""),
        "gross_amount": item.get("gross_amount", ""),
        "line_total": item.get("line_total", ""),
        "raw_line": raw_line,
    }


def prepare_line_items_for_save(line_items):
    cleaned_items = []

    for item in line_items:
        cleaned_item = prepare_line_item_for_save(item)

        if not cleaned_item["product_name"]:
            continue

        cleaned_items.append(cleaned_item)

    return cleaned_items


# --------------------------------------------------
# Inventory calculation helpers
# --------------------------------------------------

def build_inventory_dict(exclude_invoice_id=None):
    """
    Builds inventory dictionary.

    exclude_invoice_id is used when checking whether changing an existing
    invoice type would make stock negative.
    """

    init_db()

    conn = connect_db()
    cursor = conn.cursor()

    if exclude_invoice_id is None:
        cursor.execute(
            """
            SELECT
                i.id,
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
    else:
        cursor.execute(
            """
            SELECT
                i.id,
                i.invoice_type,
                ii.product_code,
                ii.product_name,
                ii.quantity,
                ii.unit
            FROM invoice_items ii
            JOIN invoices i ON ii.invoice_id = i.id
            WHERE i.id != ?
            """,
            (exclude_invoice_id,),
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

    for invoice_id, invoice_type, product_code, product_name, quantity, unit in invoice_rows:
        product_code = clean_text(product_code)
        product_name = clean_text(product_name)
        unit = clean_text(unit)
        quantity = normalise_invoice_quantity(quantity)

        key = make_inventory_key(product_code, product_name, unit)

        if key not in inventory:
            inventory[key] = {
                "product_code": product_code,
                "product_name": product_name,
                "unit": unit,
                "current_stock": 0,
            }

        if invoice_type == "Purchase":
            inventory[key]["current_stock"] += quantity
        elif invoice_type == "Sale":
            inventory[key]["current_stock"] -= quantity
        else:
            inventory[key]["current_stock"] += quantity

    for product_code, product_name, quantity_change, unit in adjustment_rows:
        product_code = clean_text(product_code)
        product_name = clean_text(product_name)
        unit = clean_text(unit)
        quantity_change = convert_quantity(quantity_change)

        key = make_inventory_key(product_code, product_name, unit)

        if key not in inventory:
            inventory[key] = {
                "product_code": product_code,
                "product_name": product_name,
                "unit": unit,
                "current_stock": 0,
            }

        inventory[key]["current_stock"] += quantity_change

    return inventory


def get_current_stock_for_product(product_code, product_name, unit, exclude_invoice_id=None):
    inventory = build_inventory_dict(exclude_invoice_id=exclude_invoice_id)
    key = make_inventory_key(product_code, product_name, unit)

    if key not in inventory:
        return 0

    return inventory[key]["current_stock"]


def validate_sale_invoice_stock(line_items, exclude_invoice_id=None):
    """
    Checks if a sale invoice would make stock go below zero.

    Returns:
    - [] if everything is okay
    - list of issue dictionaries if stock is not enough
    """

    inventory = build_inventory_dict(exclude_invoice_id=exclude_invoice_id)

    requested = {}
    display_data = {}

    cleaned_items = prepare_line_items_for_save(line_items)

    for item in cleaned_items:
        product_code = item["product_code"]
        product_name = item["product_name"]
        unit = item["unit"]
        quantity = normalise_invoice_quantity(item["quantity"])

        if quantity <= 0:
            continue

        key = make_inventory_key(product_code, product_name, unit)

        if key not in requested:
            requested[key] = 0
            display_data[key] = {
                "product_code": product_code,
                "product_name": product_name,
                "unit": unit,
            }

        requested[key] += quantity

    issues = []

    for key, requested_quantity in requested.items():
        current_stock = 0

        if key in inventory:
            current_stock = inventory[key]["current_stock"]

        if requested_quantity > current_stock:
            shortage = requested_quantity - current_stock

            issues.append(
                {
                    "product_code": display_data[key]["product_code"],
                    "product_name": display_data[key]["product_name"],
                    "unit": display_data[key]["unit"],
                    "current_stock": current_stock,
                    "requested_quantity": requested_quantity,
                    "shortage": shortage,
                }
            )

    return issues


def get_invoice_line_items_as_dicts(invoice_id):
    init_db()

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
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

    line_items = []

    for row in rows:
        line_items.append(
            {
                "product_code": row[0],
                "product_name": row[1],
                "quantity": row[2],
                "unit": row[3],
                "unit_price": row[4],
                "net_amount": row[5],
                "vat_rate": row[6],
                "vat_amount": row[7],
                "gross_amount": row[8],
                "line_total": row[9],
                "raw_line": row[10],
            }
        )

    return line_items


# --------------------------------------------------
# Save invoice and invoice items
# --------------------------------------------------

def save_invoice(invoice_data, line_items):
    init_db()

    invoice_type = clean_text(invoice_data.get("invoice_type", ""))
    cleaned_line_items = prepare_line_items_for_save(line_items)

    if invoice_type == "Sale":
        stock_issues = validate_sale_invoice_stock(cleaned_line_items)

        if stock_issues:
            raise StockValidationError(stock_issues)

    # Safety backup before saving a new invoice
    create_database_backup("before_save_invoice")

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
            invoice_type,
            invoice_data.get("document_number", ""),
            invoice_data.get("document_date", ""),
            invoice_data.get("supplier", ""),
            invoice_data.get("buyer", ""),
            invoice_data.get("total_amount", ""),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )

    invoice_id = cursor.lastrowid

    for item in cleaned_line_items:
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
                item["product_code"],
                item["product_name"],
                item["quantity"],
                item["unit"],
                item["unit_price"],
                item["net_amount"],
                item["vat_rate"],
                item["vat_amount"],
                item["gross_amount"],
                item["line_total"],
                item["raw_line"],
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

    new_invoice_type = clean_text(new_invoice_type)

    if new_invoice_type == "Sale":
        existing_line_items = get_invoice_line_items_as_dicts(invoice_id)

        stock_issues = validate_sale_invoice_stock(
            existing_line_items,
            exclude_invoice_id=invoice_id,
        )

        if stock_issues:
            raise StockValidationError(stock_issues)

    # Safety backup before changing invoice type
    create_database_backup("before_update_invoice_type")

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

    # Safety backup before deleting invoice
    create_database_backup("before_delete_invoice")

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

    # Safety backup before manual stock adjustment
    create_database_backup("before_manual_adjustment")

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
            clean_text(product_code),
            clean_text(product_name),
            convert_quantity(quantity_change),
            clean_text(unit),
            clean_text(reason),
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

    # Safety backup before deleting adjustment
    create_database_backup("before_delete_adjustment")

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

    inventory = build_inventory_dict()

    rows = []

    for item in inventory.values():
        rows.append(
            (
                item["product_code"],
                item["product_name"],
                item["unit"],
                item["current_stock"],
            )
        )

    rows.sort(key=lambda row: row[1].lower() if row[1] else "")

    return rows