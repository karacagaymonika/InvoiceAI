import re


# --------------------------------------------------
# General helper functions
# --------------------------------------------------

def find_first_match(text, patterns):
    """
    Try regex patterns one by one and return the first match.
    """
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
    return ""


def clean_amount(amount):
    """
    Clean amount text.
    Example:
    '779,08 PLN' -> '779,08'
    """
    if not amount:
        return ""

    amount = str(amount).strip()
    amount = amount.replace("PLN", "")
    amount = amount.replace("zł", "")
    amount = amount.replace("zl", "")
    amount = amount.strip()

    return amount


def amount_to_number(amount):
    """
    Convert Polish/European amount text into number.
    Example:
    '1 491,56' -> 1491.56
    '779,08' -> 779.08
    """
    if not amount:
        return 0

    cleaned = str(amount).strip()
    cleaned = cleaned.replace(" ", "")
    cleaned = cleaned.replace(".", "")
    cleaned = cleaned.replace(",", ".")

    try:
        return float(cleaned)
    except ValueError:
        return 0


def is_money(value):
    """
    Check if value looks like Polish money format.
    Examples:
    85,20
    1 491,56
    """
    value = str(value).strip()
    return re.fullmatch(r"[0-9]{1,3}(?:[\s.][0-9]{3})*,[0-9]{2}", value) is not None


def extract_money_values(text):
    """
    Extract money values from a text line.
    Only comma format is used to avoid reading dates like 19.06 as money.
    """
    amount_pattern = r"([0-9]{1,3}(?:[\s.][0-9]{3})*,[0-9]{2})"
    amounts = re.findall(amount_pattern, text)

    return [clean_amount(amount) for amount in amounts]


# --------------------------------------------------
# Company extraction
# --------------------------------------------------

def clean_company_line(line):
    """
    Remove labels like 'Nazwa:' from company names.
    """
    line = str(line).strip()

    prefixes = [
        "Nazwa:",
        "Nazwa",
        "Company:",
        "Company",
        "Name:",
        "Name",
    ]

    for prefix in prefixes:
        if line.lower().startswith(prefix.lower()):
            return line[len(prefix):].strip()

    return line


def extract_company_after_label(text, label):
    """
    Extract company name after labels like:
    Sprzedawca
    Nabywca
    Supplier
    Buyer
    """

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for index, line in enumerate(lines):
        if label.lower() in line.lower():
            for next_line in lines[index + 1 : index + 12]:
                lower_next = next_line.lower()

                if "nazwa" in lower_next:
                    return clean_company_line(next_line)

                skip_words = [
                    "nip",
                    "regon",
                    "bdo",
                    "telefon",
                    "email",
                    "adres",
                    "ul.",
                    "strona",
                    "data",
                ]

                if any(word in lower_next for word in skip_words):
                    continue

                if len(next_line) > 2:
                    return clean_company_line(next_line)

    return ""


def extract_supplier(text):
    supplier = extract_company_after_label(text, "Sprzedawca")
    if supplier:
        return supplier

    supplier = extract_company_after_label(text, "Supplier")
    if supplier:
        return supplier

    supplier = extract_company_after_label(text, "Seller")
    if supplier:
        return supplier

    return ""


def extract_buyer(text):
    buyer = extract_company_after_label(text, "Nabywca")
    if buyer:
        return buyer

    buyer = extract_company_after_label(text, "Kupujący")
    if buyer:
        return buyer

    buyer = extract_company_after_label(text, "Buyer")
    if buyer:
        return buyer

    buyer = extract_company_after_label(text, "Customer")
    if buyer:
        return buyer

    return ""


# --------------------------------------------------
# Invoice field extraction
# --------------------------------------------------

def extract_document_number(text):
    """
    Extract invoice number.

    Handles:
    Numer Faktury:
    FS 1534/06/2026
    """

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for index, line in enumerate(lines):
        lower_line = line.lower()

        if "numer faktury" in lower_line or "nr faktury" in lower_line:
            if ":" in line:
                after_colon = line.split(":", 1)[1].strip()
                if after_colon:
                    return after_colon

            if index + 1 < len(lines):
                return lines[index + 1].strip()

        if "invoice number" in lower_line or "invoice no" in lower_line:
            if ":" in line:
                after_colon = line.split(":", 1)[1].strip()
                if after_colon:
                    return after_colon

            if index + 1 < len(lines):
                return lines[index + 1].strip()

    patterns = [
        r"\b(FS\s*[0-9]+\/[0-9]+\/[0-9]+)\b",
        r"\b(FV\s*[0-9]+\/[0-9]+\/[0-9]+)\b",
        r"Faktura\s+VAT\s+nr\s*([A-Z0-9\/\-_\.]+)",
        r"Faktura\s+nr\s*([A-Z0-9\/\-_\.]+)",
        r"Numer\s+KSEF\s*[:\-]?\s*([A-Z0-9\/\-_\.]+)",
    ]

    return find_first_match(text, patterns)


def extract_document_date(text):
    """
    Extract invoice date.
    """

    patterns = [
        r"data\s+wystawienia.*?(\d{2}[./-]\d{2}[./-]\d{4})",
        r"data\s+sprzedaży.*?(\d{2}[./-]\d{2}[./-]\d{4})",
        r"data\s+sprzedazy.*?(\d{2}[./-]\d{2}[./-]\d{4})",
        r"data\s+wystawienia.*?(\d{4}[./-]\d{2}[./-]\d{2})",
        r"data\s+sprzedaży.*?(\d{4}[./-]\d{2}[./-]\d{2})",
        r"data\s+sprzedazy.*?(\d{4}[./-]\d{2}[./-]\d{2})",
        r"\b(\d{2}[./-]\d{2}[./-]\d{4})\b",
        r"\b(\d{4}[./-]\d{2}[./-]\d{2})\b",
    ]

    return find_first_match(text, patterns)


def extract_total_amount(text):
    """
    Extract invoice total amount.
    Uses comma money format to avoid dates like 19.06.
    """

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    total_keywords = [
        "kwota należności ogółem",
        "kwota naleznosci ogolem",
        "razem do zapłaty",
        "razem do zaplaty",
        "do zapłaty",
        "do zaplaty",
        "kwota do zapłaty",
        "kwota do zaplaty",
        "wartość brutto",
        "wartosc brutto",
        "suma brutto",
        "wartość sprzedaży brutto",
        "wartosc sprzedazy brutto",
        "total amount",
        "grand total",
        "amount due",
        "total due",
    ]

    for line in lines:
        lower_line = line.lower()

        if any(keyword in lower_line for keyword in total_keywords):
            amounts = extract_money_values(line)

            if amounts:
                return clean_amount(amounts[-1])

    safe_amounts = []

    for line in lines:
        lower_line = line.lower()

        skip_words = [
            "wersja",
            "http",
            "ksef",
            "telefon",
            "nip",
            "regon",
            "data",
            "email",
        ]

        if any(word in lower_line for word in skip_words):
            continue

        amounts = extract_money_values(line)

        for amount in amounts:
            safe_amounts.append(amount)

    if safe_amounts:
        largest_amount = max(safe_amounts, key=amount_to_number)
        return clean_amount(largest_amount)

    return ""


def extract_invoice_fields(text):
    """
    Return main invoice fields as dictionary.
    """

    return {
        "document_number": extract_document_number(text),
        "document_date": extract_document_date(text),
        "supplier": extract_supplier(text),
        "buyer": extract_buyer(text),
        "total_amount": extract_total_amount(text),
    }


# --------------------------------------------------
# Product line extraction
# --------------------------------------------------

def is_lp_number(value):
    """
    Check if value is a line number like 1, 2, 3.
    """
    value = str(value).strip()
    return value.isdigit()


def is_quantity(value):
    """
    Check if value looks like quantity.
    """
    value = str(value).strip()
    return re.fullmatch(r"\d+[,.]?\d*", value) is not None


def is_vat_rate(value):
    """
    Check if value looks like VAT rate.
    """
    value = str(value).strip()
    return re.fullmatch(r"\d{1,2}%", value) is not None


def is_unit(value):
    """
    Check if value looks like unit.
    """

    value = str(value).strip().lower()

    units = [
        "szt",
        "szt.",
        "pcs",
        "piece",
        "unit",
        "kg",
        "g",
        "l",
        "ml",
        "opak",
        "op.",
    ]

    return value in units


def extract_product_code_from_line(line):
    """
    Extract product code from a line if possible.
    """

    patterns = [
        r"(?:sku|kod|code|indeks|symbol)\s*[:\-]?\s*([A-Z0-9\/\-_\.]+)",
        r"^([A-Z0-9]{6,})\s+",
    ]

    return find_first_match(line, patterns)


def extract_line_items_from_single_lines(lines):
    """
    Fallback extraction for lines where all product data is on one row.
    """

    line_items = []

    skip_keywords = [
        "razem",
        "total",
        "suma",
        "do zapłaty",
        "do zaplaty",
        "kwota",
        "nip",
        "regon",
        "telefon",
        "email",
        "faktura",
        "data wystawienia",
        "data sprzedaży",
        "data sprzedazy",
        "sprzedawca",
        "nabywca",
        "adres",
        "bank",
        "konto",
        "termin",
        "płatności",
        "platnosci",
        "wartość brutto",
        "wartosc brutto",
        "wartość netto",
        "wartosc netto",
        "pozycje",
        "lp.",
    ]

    for line in lines:
        lower_line = line.lower()

        if any(keyword in lower_line for keyword in skip_keywords):
            continue

        amounts = extract_money_values(line)

        if not amounts:
            continue

        product_code = extract_product_code_from_line(line)

        quantity = ""
        unit = ""

        quantity_match = re.search(
            r"\b(\d+[,.]?\d*)\s*(szt|szt\.|pcs|piece|unit|kg|g|l|ml|opak|op\.?)\b",
            line,
            re.IGNORECASE,
        )

        if quantity_match:
            quantity = quantity_match.group(1).replace(",", ".")
            unit = quantity_match.group(2)

        vat_rate = ""
        vat_match = re.search(r"\b(\d{1,2})\s*%", line)

        if vat_match:
            vat_rate = vat_match.group(1) + "%"

        product_name = line

        if product_code:
            product_name = product_name.replace(product_code, "")

        if quantity:
            product_name = product_name.replace(quantity, "")

        if unit:
            product_name = product_name.replace(unit, "")

        if vat_rate:
            product_name = product_name.replace(vat_rate, "")

        for amount in amounts:
            product_name = product_name.replace(amount, "")

        product_name = product_name.strip(" -|:;")

        line_items.append(
            {
                "product_code": product_code,
                "product_name": product_name,
                "quantity": quantity,
                "unit": unit,
                "unit_price": amounts[0] if len(amounts) >= 2 else "",
                "net_amount": "",
                "vat_rate": vat_rate,
                "vat_amount": "",
                "gross_amount": amounts[-1],
                "line_total": amounts[-1],
                "raw_line": line,
            }
        )

    return line_items


def extract_line_items_from_ksef_multiline(lines):
    """
    Extract KSeF-style product lines where each row is split into many lines.

    Expected pattern:
    Lp number
    product code
    product name
    unit price
    quantity
    unit
    VAT rate
    line total
    """

    line_items = []

    index = 0

    while index < len(lines):
        current_line = lines[index]

        if not is_lp_number(current_line):
            index += 1
            continue

        try:
            product_code = lines[index + 1]
            product_name = lines[index + 2]
            unit_price = lines[index + 3]
            quantity = lines[index + 4]
            unit = lines[index + 5]
            vat_rate = lines[index + 6]
            line_total = lines[index + 7]
        except IndexError:
            break

        if (
            is_money(unit_price)
            and is_quantity(quantity)
            and is_unit(unit)
            and is_vat_rate(vat_rate)
            and is_money(line_total)
        ):
            line_items.append(
                {
                    "product_code": product_code,
                    "product_name": product_name,
                    "quantity": quantity.replace(",", "."),
                    "unit": unit,
                    "unit_price": clean_amount(unit_price),
                    "net_amount": "",
                    "vat_rate": vat_rate,
                    "vat_amount": "",
                    "gross_amount": clean_amount(line_total),
                    "line_total": clean_amount(line_total),
                    "raw_line": (
                        f"{current_line} {product_code} {product_name} "
                        f"{unit_price} {quantity} {unit} {vat_rate} {line_total}"
                    ),
                }
            )

            index += 8

        else:
            index += 1

    return line_items


def extract_line_items(text):
    """
    Main line-item extraction function.

    First tries KSeF multiline layout.
    If that fails, it tries single-line extraction.
    """

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    start_index = 0

    for index, line in enumerate(lines):
        if line.lower() == "pozycje":
            start_index = index + 1
            break

    product_lines = lines[start_index:]

    multiline_items = extract_line_items_from_ksef_multiline(product_lines)

    if multiline_items:
        return multiline_items

    return extract_line_items_from_single_lines(product_lines)