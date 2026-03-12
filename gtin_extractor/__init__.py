"""gtin_extractor – batch GTIN extraction from product label images.

Public API::

    from gtin_extractor.validation import is_valid_gtin_checksum, extract_gtin_from_raw
    from gtin_extractor.readers import process_image
    from gtin_extractor.gemini_integration import decode_barcode_gemini, analyze_product_gemini
    from gtin_extractor.csv_export import CSVWriter, build_row
    from gtin_extractor.config import load_config
"""

__version__ = "1.0.0"

from gtin_extractor.validation import extract_gtin_from_raw, is_valid_gtin_checksum

__all__ = [
    "__version__",
    "is_valid_gtin_checksum",
    "extract_gtin_from_raw",
]
