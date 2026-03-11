"""Unit tests for gtin_extractor.validation module."""

from __future__ import annotations

from gtin_extractor.validation import extract_gtin_from_raw, is_valid_gtin_checksum

# ---------------------------------------------------------------------------
# is_valid_gtin_checksum
# ---------------------------------------------------------------------------


class TestIsValidGtinChecksum:
    """Tests for the GS1 checksum algorithm."""

    # --- valid cases ---

    def test_valid_gtin_14(self):
        assert is_valid_gtin_checksum("00012345678905") is True

    def test_valid_gtin_13(self):
        # EAN-13: 5901234123457
        assert is_valid_gtin_checksum("5901234123457") is True

    def test_valid_gtin_12(self):
        # UPC-A: 012345678905
        assert is_valid_gtin_checksum("012345678905") is True

    def test_valid_gtin_8(self):
        # GTIN-8: 96385074
        assert is_valid_gtin_checksum("96385074") is True

    def test_all_zeros_gtin_8(self):
        # 0000000 payload → check = 0
        assert is_valid_gtin_checksum("00000000") is True

    # --- invalid cases ---

    def test_wrong_check_digit(self):
        assert is_valid_gtin_checksum("00012345678900") is False

    def test_non_numeric(self):
        assert is_valid_gtin_checksum("0001234567890A") is False

    def test_empty_string(self):
        assert is_valid_gtin_checksum("") is False

    def test_wrong_length_7(self):
        assert is_valid_gtin_checksum("1234567") is False

    def test_wrong_length_15(self):
        assert is_valid_gtin_checksum("123456789012345") is False

    def test_wrong_length_11(self):
        assert is_valid_gtin_checksum("12345678901") is False

    def test_wrong_check_digit_gtin_13(self):
        assert is_valid_gtin_checksum("5901234123450") is False


# ---------------------------------------------------------------------------
# extract_gtin_from_raw
# ---------------------------------------------------------------------------


class TestExtractGtinFromRaw:
    """Tests for raw barcode string GTIN extraction."""

    def test_plain_valid_gtin_14(self):
        assert extract_gtin_from_raw("00012345678905") == "00012345678905"

    def test_plain_valid_gtin_13(self):
        assert extract_gtin_from_raw("5901234123457") == "5901234123457"

    def test_plain_valid_gtin_12(self):
        assert extract_gtin_from_raw("012345678905") == "012345678905"

    def test_plain_valid_gtin_8(self):
        assert extract_gtin_from_raw("96385074") == "96385074"

    def test_gs1_parenthesis_prefix_01(self):
        assert extract_gtin_from_raw("(01)00012345678905") == "00012345678905"

    def test_gs1_parenthesis_prefix_02(self):
        assert extract_gtin_from_raw("(02)00012345678905") == "00012345678905"

    def test_gs1_pipe_delimiter(self):
        raw = "|0100012345678905|17231231|10ABC"
        assert extract_gtin_from_raw(raw) == "00012345678905"

    def test_gs1_field_separator_delimiter(self):
        # GS character (0x1D) as delimiter
        raw = "\x1d0100012345678905\x1d17231231"
        assert extract_gtin_from_raw(raw) == "00012345678905"

    def test_gs1_caret_delimiter(self):
        raw = "^0100012345678905^17231231"
        assert extract_gtin_from_raw(raw) == "00012345678905"

    def test_gs1_numeric_prefix_01(self):
        # Digits starting with "01" followed by 14-digit GTIN
        raw = "0100012345678905"
        assert extract_gtin_from_raw(raw) == "00012345678905"

    def test_invalid_raw_empty(self):
        assert extract_gtin_from_raw("") == ""

    def test_invalid_raw_letters(self):
        assert extract_gtin_from_raw("ABCDEF") == ""

    def test_wrong_check_digit_not_extracted(self):
        assert extract_gtin_from_raw("00012345678900") == ""

    def test_gs1_with_extra_data(self):
        # GS1-128 string with lot number after GTIN
        raw = "(01)00012345678905(10)LOT001"
        assert extract_gtin_from_raw(raw) == "00012345678905"
