"""GTIN checksum validation utilities."""

import re


def is_valid_gtin_checksum(barcode_data: str) -> bool:
    """Validate a GTIN string by checking its length and GS1 checksum digit.

    Supported lengths: 8 (GTIN-8), 12 (UPC-A), 13 (EAN-13), 14 (GTIN-14).

    Args:
        barcode_data: The numeric barcode string to validate.

    Returns:
        ``True`` if the string is a valid GTIN, ``False`` otherwise.
    """
    if not barcode_data.isdigit():
        return False

    if len(barcode_data) not in (8, 12, 13, 14):
        return False

    payload = barcode_data[:-1]
    check_digit = int(barcode_data[-1])

    total = 0
    for i, char in enumerate(reversed(payload)):
        multiplier = 3 if i % 2 == 0 else 1
        total += int(char) * multiplier

    calculated_check = (10 - (total % 10)) % 10
    return check_digit == calculated_check


def extract_gtin_from_raw(raw_data: str) -> str:
    """Extract and validate a GTIN from a raw barcode string (including GS1 strings).

    The function attempts multiple extraction strategies in order of specificity:

    1. Explicit ``(01)`` / ``(02)`` GS1 Application Identifier prefix.
    2. Pipe-delimited GS1 string after normalising common delimiters.
    3. Numeric-only extraction with GS1 AI prefix stripping.
    4. Plain numeric string of valid GTIN length.

    Args:
        raw_data: Raw string as decoded from a barcode symbol.

    Returns:
        A validated GTIN string, or an empty string if none was found.
    """
    # 1. Try to find 14-digit GTIN following (01) or (02)
    match = re.search(r"\(0[12]\)(\d{14})", raw_data)
    if match:
        gtin = match.group(1)
        if is_valid_gtin_checksum(gtin):
            return gtin

    # 2. Standardise GS1 delimiters and search for AI 01/02
    s = raw_data.replace("\x1d", "|").replace("\x1e", "|").replace("^", "|")
    match = re.search(r"(?:^|\|)0[12](\d{14})", s)
    if match:
        gtin = match.group(1)
        if is_valid_gtin_checksum(gtin):
            return gtin

    # 3. Strip non-digits and look for a valid-length GTIN
    digits = re.sub(r"\D", "", raw_data)

    if len(digits) >= 16 and (digits.startswith("01") or digits.startswith("02")):
        gtin = digits[2:16]
        if is_valid_gtin_checksum(gtin):
            return gtin

    if len(digits) in (8, 12, 13, 14):
        if is_valid_gtin_checksum(digits):
            return digits

    return ""
