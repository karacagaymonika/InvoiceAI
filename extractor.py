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


def clean_company_line(line):
    """
    Remove labels like 'Nazwa:' from company names.
    Example:
    'Nazwa: PROMOEFEKT SPÓŁKA Z OGRANICZONĄ ODPOWIEDZIALNOŚCIĄ'
    becomes:
    'PROMOEFEKT SPÓŁKA Z OGRANICZONĄ ODPOWIEDZIALNOŚCIĄ'
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
    patterns = [
        r"Faktura\s+VAT\s+nr\s*([A-Z0-9\/\-_\.]+)",
        r"Faktura\s+nr\s*([A-Z0-9\/\-_\.]+)",
        r"nr\s+faktury\s*[:\-]?\s*([A-Z0-9\/\-_\.]+)",
        r"numer\s+faktury\s*[:\-]?\s*([A-Z0-9\/\-_\.]+)",
        r"Numer\s+Faktury\s*[:\-]?\s*([A-Z0-9\/\-_\.]+)",
        r"invoice\s+number\s*[:\-]?\s*([A-Z0-9\/\-_\.]+)",
        r"invoice\s+no\.?\s*[:\-]?\s*([A-Z0-9\/\-_\.]+)",
    ]

    return find_first_match(text, patterns)


def extract_document_date(text):
    patterns = [
        r"data\s+wystawienia\s*[:\-]?\s*.*?(\d{4}[./-]\d{2}[./-]\d{2})",
        r"data\s+sprzedaży\s*[:\-]?\s*.*?(\d{4}[./-]\d{2}[./-]\d{2})",
        r"data\s+sprzedazy\s*[:\-]?\s*.*?(\d{4}[./-]\d{2}[./-]\d{2})",
        r"\b(\d{4}[./-]\d{2}[./-]\d{2})\b",
        r"\b(\d{2}[./-]\d{2}[./-]\d{4})\b",
    ]

    return find_first_match(text, patterns)


def extract_company_after_label(text, label):
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for index, line in enumerate(lines):
        if label.lower() in line.lower():
            for next_line in lines[index + 1 : index + 10]:
                lower_next = next_line.lower()

                # If this line contains the company name, return it cleaned
                if "nazwa" in lower_next:
                    return clean_company_line(next_line)

                # Skip registration/address/contact lines
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
        "total amount",
        "grand total",
        "amount due",
        "total due",
    ]

    amount_pattern = r"([0-9]{1,3}(?:[\s,.][0-9]{3})*[,\.][0-9]{2})"

    for line in lines:
        lower_line = line.lower()

        if any(keyword in lower_line for keyword in total_keywords):
            amounts = re.findall(amount_pattern, line)

            if amounts:
                return clean_amount(amounts[-1])

    all_amounts = re.findall(amount_pattern, text)

    if all_amounts:
        return clean_amount(all_amounts[-1])

    return ""


def extract_invoice_fields(text):
    return {
        "document_number": extract_document_number(text),
        "document_date": extract_document_date(text),
        "supplier": extract_supplier(text),
        "buyer": extract_buyer(text),
        "total_amount": extract_total_amount(text),
    }