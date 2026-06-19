import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
BACKUP_DIR = BASE_DIR / "backups"
BACKUP_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "invoice_ai.db"


def connect_db():
    return sqlite3.connect(DB_PATH)


def column_exists(cursor, table_name, column_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    return column_name in [row[1] for row in cursor.fetchall()]


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
            is_paid INTEGER DEFAULT 0,
            created_at TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER,
            item_type TEXT DEFAULT 'stock_product',
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

    if not column_exists(cursor, "invoices", "is_paid"):
        cursor.execute(
            "ALTER TABLE invoices ADD COLUMN is_paid INTEGER DEFAULT 0"
        )

    if not column_exists(cursor, "invoice_items", "item_type"):
        cursor.execute(
            "ALTER TABLE invoice_items "
            "ADD COLUMN item_type TEXT DEFAULT 'stock_product'"
        )

    cursor.execute(
        """
        UPDATE invoice_items
        SET item_type = 'stock_product'
        WHERE item_type IS NULL OR TRIM(item_type) = ''
        """
    )
    cursor.execute(
        """
        UPDATE invoices
        SET is_paid = 0
        WHERE is_paid IS NULL
        """
    )

    conn.commit()
    conn.close()


class StockValidationError(ValueError):
    def __init__(self, issues):
        self.issues = issues
        super().__init__("Not enough stock for this sale invoice.")


def create_database_backup(reason="manual"):
    init_db()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_reason = str(reason).strip().replace(" ", "_").lower()
    backup_file = BACKUP_DIR / f"invoice_ai_backup_{safe_reason}_{timestamp}.db"
    shutil.copy2(DB_PATH, backup_file)
    return backup_file


def get_backup_files():
    BACKUP_DIR.mkdir(exist_ok=True)
    return sorted(
        BACKUP_DIR.glob("invoice_ai_backup_*.db"),
        key=lambda file: file.stat().st_mtime,
        reverse=True,
    )


def clean_text(value):
    return "" if value is None else str(value).strip()


def normalize_key_value(value):
    return " ".join(clean_text(value).split()).lower()


def make_inventory_key(product_code, product_name, unit):
    return (
        normalize_key_value(product_code),
        normalize_key_value(product_name),
        normalize_key_value(unit),
    )


def convert_quantity(value):
    if value is None:
        return 0.0

    value = str(value).strip().replace(",", ".")
    if not value:
        return 0.0

    try:
        return float(value)
    except ValueError:
        return 0.0


def normalize_invoice_quantity(value):
    return abs(convert_quantity(value))


def normalize_item_type(value):
    normalized = normalize_key_value(value)

    mapping = {
        "stock_product": "stock_product",
        "stock product": "stock_product",
        "towar do magazynu": "stock_product",
        "towar": "stock_product",
        "auxiliary_material": "auxiliary_material",
        "auxiliary material": "auxiliary_material",
        "materiał pomocniczy": "auxiliary_material",
        "material pomocniczy": "auxiliary_material",
        "shipping_cost": "shipping_cost",
        "shipping / courier": "shipping_cost",
        "shipping/courier": "shipping_cost",
        "wysyłka / kurier": "shipping_cost",
        "wysylka / kurier": "shipping_cost",
        "kurier": "shipping_cost",
        "other_cost": "other_cost",
        "other cost": "other_cost",
        "inny koszt": "other_cost",
    }

    return mapping.get(normalized, "stock_product")


def normalize_paid_value(value):
    if isinstance(value, bool):
        return 1 if value else 0

    normalized = normalize_key_value(value)
    if normalized in {
        "1", "true", "yes", "y", "tak", "paid", "opłacona", "oplacona"
    }:
        return 1

    return 0


def prepare_line_item_for_save(item):
    product_code = clean_text(item.get("product_code", ""))
    product_name = clean_text(item.get("product_name", ""))
    raw_line = clean_text(item.get("raw_line", ""))

    if not product_name and raw_line:
        product_name = raw_line

    return {
        "item_type": normalize_item_type(item.get("item_type", "stock_product")),
        "product_code": product_code,
        "product_name": product_name,
        "quantity": normalize_invoice_quantity(item.get("quantity", 0)),
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
        if cleaned_item["product_name"]:
            cleaned_items.append(cleaned_item)

    return cleaned_items


def build_inventory_dict(exclude_invoice_id=None):
    init_db()

    conn = connect_db()
    cursor = conn.cursor()

    query = """
        SELECT
            i.id,
            i.invoice_type,
            ii.item_type,
            ii.product_code,
            ii.product_name,
            ii.quantity,
            ii.unit
        FROM invoice_items ii
        JOIN invoices i ON ii.invoice_id = i.id
    """
    params = ()

    if exclude_invoice_id is not None:
        query += " WHERE i.id != ?"
        params = (exclude_invoice_id,)

    cursor.execute(query, params)
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

    for (
        invoice_id,
        invoice_type,
        item_type,
        product_code,
        product_name,
        quantity,
        unit,
    ) in invoice_rows:
        if normalize_item_type(item_type) != "stock_product":
            continue

        product_code = clean_text(product_code)
        product_name = clean_text(product_name)
        unit = clean_text(unit)
        quantity = normalize_invoice_quantity(quantity)
        key = make_inventory_key(product_code, product_name, unit)

        if key not in inventory:
            inventory[key] = {
                "product_code": product_code,
                "product_name": product_name,
                "unit": unit,
                "current_stock": 0.0,
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
        key = make_inventory_key(product_code, product_name, unit)

        if key not in inventory:
            inventory[key] = {
                "product_code": product_code,
                "product_name": product_name,
                "unit": unit,
                "current_stock": 0.0,
            }

        inventory[key]["current_stock"] += convert_quantity(quantity_change)

    return inventory


def validate_sale_invoice_stock(line_items, exclude_invoice_id=None):
    inventory = build_inventory_dict(exclude_invoice_id=exclude_invoice_id)
    requested = {}
    display_data = {}

    for item in prepare_line_items_for_save(line_items):
        if item["item_type"] != "stock_product":
            continue

        quantity = normalize_invoice_quantity(item["quantity"])
        if quantity <= 0:
            continue

        key = make_inventory_key(
            item["product_code"],
            item["product_name"],
            item["unit"],
        )

        requested[key] = requested.get(key, 0.0) + quantity
        display_data[key] = {
            "product_code": item["product_code"],
            "product_name": item["product_name"],
            "unit": item["unit"],
        }

    issues = []

    for key, requested_quantity in requested.items():
        current_stock = inventory.get(key, {}).get("current_stock", 0.0)

        if requested_quantity > current_stock:
            issues.append(
                {
                    "product_code": display_data[key]["product_code"],
                    "product_name": display_data[key]["product_name"],
                    "unit": display_data[key]["unit"],
                    "current_stock": current_stock,
                    "requested_quantity": requested_quantity,
                    "shortage": requested_quantity - current_stock,
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
            item_type,
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

    return [
        {
            "item_type": row[0],
            "product_code": row[1],
            "product_name": row[2],
            "quantity": row[3],
            "unit": row[4],
            "unit_price": row[5],
            "net_amount": row[6],
            "vat_rate": row[7],
            "vat_amount": row[8],
            "gross_amount": row[9],
            "line_total": row[10],
            "raw_line": row[11],
        }
        for row in rows
    ]


def save_invoice(invoice_data, line_items):
    init_db()

    invoice_type = clean_text(invoice_data.get("invoice_type", ""))
    is_paid = normalize_paid_value(invoice_data.get("is_paid", False))
    cleaned_line_items = prepare_line_items_for_save(line_items)

    if invoice_type == "Sale":
        issues = validate_sale_invoice_stock(cleaned_line_items)
        if issues:
            raise StockValidationError(issues)

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
            is_paid,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            invoice_data.get("file_name", ""),
            invoice_type,
            invoice_data.get("document_number", ""),
            invoice_data.get("document_date", ""),
            invoice_data.get("supplier", ""),
            invoice_data.get("buyer", ""),
            invoice_data.get("total_amount", ""),
            is_paid,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )

    invoice_id = cursor.lastrowid

    for item in cleaned_line_items:
        cursor.execute(
            """
            INSERT INTO invoice_items (
                invoice_id,
                item_type,
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                invoice_id,
                item["item_type"],
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
            is_paid,
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
            item_type,
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


def get_all_invoice_items():
    init_db()

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            ii.id,
            ii.invoice_id,
            i.document_number,
            i.invoice_type,
            ii.item_type,
            ii.product_code,
            ii.product_name,
            ii.quantity,
            ii.unit,
            ii.unit_price,
            ii.net_amount,
            ii.vat_rate,
            ii.vat_amount,
            ii.gross_amount,
            ii.line_total,
            ii.raw_line
        FROM invoice_items ii
        JOIN invoices i ON ii.invoice_id = i.id
        ORDER BY ii.id DESC
        """
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def update_invoice_type(invoice_id, new_invoice_type):
    init_db()
    new_invoice_type = clean_text(new_invoice_type)

    if new_invoice_type == "Sale":
        issues = validate_sale_invoice_stock(
            get_invoice_line_items_as_dicts(invoice_id),
            exclude_invoice_id=invoice_id,
        )
        if issues:
            raise StockValidationError(issues)

    create_database_backup("before_update_invoice_type")

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE invoices SET invoice_type = ? WHERE id = ?",
        (new_invoice_type, invoice_id),
    )
    conn.commit()
    conn.close()


def update_invoice_paid_status(invoice_id, is_paid):
    init_db()
    create_database_backup("before_update_paid_status")

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE invoices SET is_paid = ? WHERE id = ?",
        (normalize_paid_value(is_paid), invoice_id),
    )
    conn.commit()
    conn.close()


def delete_invoice(invoice_id):
    init_db()
    create_database_backup("before_delete_invoice")

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
    cursor.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
    conn.commit()
    conn.close()


def save_manual_adjustment(product_code, product_name, quantity_change, unit, reason):
    init_db()
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
    create_database_backup("before_delete_adjustment")

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM inventory_adjustments WHERE id = ?",
        (adjustment_id,),
    )
    conn.commit()
    conn.close()


def get_inventory_summary():
    rows = [
        (
            item["product_code"],
            item["product_name"],
            item["unit"],
            item["current_stock"],
        )
        for item in build_inventory_dict().values()
    ]

    rows.sort(key=lambda row: row[1].lower() if row[1] else "")
    return rows
