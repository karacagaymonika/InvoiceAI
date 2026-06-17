import re


def find_first_match(text, patterns):
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
    return ""


def clean_amount(amount):
    if not amount:
        return ""

    amount = amount.strip()
    amount = amount.replace("PLN", "")
    amount = amount.replace("zł", "")
    amount = amount.replace("zl", "")
    amount = amount.strip()

    return amount


def amount_to_number(amount):
    """
    Convert Polish money format into a number.
    Example:
    1 491,56 -> 1491.56
    85,20 -> 85.20
    """
    if not amount:
        return 0

    cleaned = amount.replace(" ", "")
    cleaned = cleaned.replace(".", "")
    cleaned = cleaned.replace(",", ".")

    try:
        return float(cleaned)
    except ValueError:
        return 0


def clean_company_line(line):
    """
    Remove labels like 'Nazwa:' from company names.
    """
    line = line.strip()

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


def extract_document_number(text):
    """
    Extract invoice number.
    Handles Polish invoices where:
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
    Supports:
    05.06.2026
    2026-06-05
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


def extract_company_after_label(text, label):
    """
    Extract company name after labels like:
    Sprzedawca
    Nabywca
    Buyer
    Supplier
    """

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for index, line in enumerate(lines):
        if label.lower() in line.lower():
            for next_line in lines[index + 1 : index + 12]:
                lower_next = next_line.lower()

                if "nazwa" in lower_next:
                    return clean_company_line(next_line)

                if any(
                    word in lower_next
                    for word in [
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
                ):
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


def extract_total_amount(text):
    """
    Extract invoice total amount.

    Important:
    We only match Polish money format with comma:
    85,20
    1 491,56

    This avoids accidentally reading dates like 19.06 as money.
    """

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    total_keywords = [
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

    amount_pattern = r"([0-9]{1,3}(?:[\s.][0-9]{3})*,[0-9]{2})"

    for line in lines:
        lower_line = line.lower()

        if any(keyword in lower_line for keyword in total_keywords):
            amounts = re.findall(amount_pattern, line)

            if amounts:
                return clean_amount(amounts[-1])

    safe_amounts = []

    for line in lines:
        lower_line = line.lower()

        if any(
            word in lower_line
            for word in [
                "wersja",
                "http",
                "ksef",
                "telefon",
                "nip",
                "regon",
                "data",
                "email",
            ]
        ):
            continue

        amounts = re.findall(amount_pattern, line)

        for amount in amounts:
            safe_amounts.append(amount)

    if safe_amounts:
        largest_amount = max(safe_amounts, key=amount_to_number)
        return clean_amount(largest_amount)

    return ""


def extract_product_code(line):
    """
    Try to extract product code / SKU from the start of a product line.
    """

    patterns = [
        r"(?:sku|kod|code|indeks|symbol)\s*[:\-]?\s*([A-Z0-9\/\-_\.]+)",
        r"^([A-Z0-9]{6,})\s+",
    ]

    return find_first_match(line, patterns)


def extract_quantity_and_unit(line):
    """
    Extract quantity and unit.
    Examples:
    10 szt.
    5 pcs
    1 kg
    """

    pattern = r"\b(\d+[,.]?\d*)\s*(szt|szt\.|pcs|piece|unit|kg|g|l|ml|opak|op\.?)\b"

    match = re.search(pattern, line, re.IGNORECASE)

    if match:
        quantity = match.group(1).replace(",", ".")
        unit = match.group(2)
        return quantity, unit

    return "", ""


def extract_vat_rate(line):
    """
    Extract VAT rate.
    Examples:
    23%
    8%
    """

    match = re.search(r"\b(\d{1,2})\s*%", line)

    if match:
        return match.group(1) + "%"

    return ""


def extract_money_values(line):
    """
    Extract money values from one line.
    Only comma money format is used to avoid dates.
    """

    amount_pattern = r"([0-9]{1,3}(?:[\s.][0-9]{3})*,[0-9]{2})"
    amounts = re.findall(amount_pattern, line)

    return [clean_amount(amount) for amount in amounts]


def clean_product_name(line, amounts, product_code, quantity, unit, vat_rate):
    """
    Remove extracted values from raw line to leave cleaner product name.
    """

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

    words_to_remove = [
        "SKU:",
        "sku:",
        "Kod:",
        "kod:",
        "Code:",
        "code:",
    ]

    for word in words_to_remove:
        product_name = product_name.replace(word, "")

    product_name = product_name.strip(" -|:;")

    return product_name


def extract_line_items(text):
    """
    Extract product/service lines from invoice text.

    Creates structure needed later for inventory:
    product code, product name, quantity, unit, prices, VAT and totals.
    """

    lines = [line.strip() for line in text.splitlines() if line.strip()]
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

        product_code = extract_product_code(line)
        quantity, unit = extract_quantity_and_unit(line)
        vat_rate = extract_vat_rate(line)

        product_name = clean_product_name(
            line=line,
            amounts=amounts,
            product_code=product_code,
            quantity=quantity,
            unit=unit,
            vat_rate=vat_rate,
        )

        unit_price = ""
        net_amount = ""
        vat_amount = ""
        gross_amount = ""
        line_total = ""

        if len(amounts) == 1:
            line_total = amounts[0]

        elif len(amounts) == 2:
            unit_price = amounts[0]
            line_total = amounts[1]

        elif len(amounts) == 3:
            unit_price = amounts[0]
            net_amount = amounts[1]
            line_total = amounts[2]

        elif len(amounts) >= 4:
            unit_price = amounts[0]
            net_amount = amounts[-3]
            vat_amount = amounts[-2]
            gross_amount = amounts[-1]
            line_total = amounts[-1]

        line_items.append(
            {
                "product_code": product_code,
                "product_name": product_name,
                "quantity": quantity,
                "unit": unit,
                "unit_price": unit_price,
                "net_amount": net_amount,
                "vat_rate": vat_rate,
                "vat_amount": vat_amount,
                "gross_amount": gross_amount,
                "line_total": line_total,
                "raw_line": line,
            }
        )

    return line_items


def extract_invoice_fields(text):
    return {
        "document_number": extract_document_number(text),
        "document_date": extract_document_date(text),
        "supplier": extract_supplier(text),
        "buyer": extract_buyer(text),
        "total_amount": extract_total_amount(text),
    }