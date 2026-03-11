"""CSV export utilities for GTIN extraction results."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Iterator

logger = logging.getLogger("gtin_extractor.csv_export")

FIELDNAMES: list[str] = [
    "filename",
    "gtin",
    "gtin_detection_status",
    "gtin_detection_method",
    "manufacturer",
    "ref",
    "ref_confidence",
    "product_name",
    "product_specs",
]


def build_row(
    filename: str,
    gtin: str,
    method: str,
    product_info: dict,
) -> dict:
    """Build a result row dict from extraction outputs.

    Args:
        filename: Source image filename (basename only).
        gtin: Extracted and validated GTIN, or ``""`` if not found.
        method: Detection method string (``"pyzbar"``, ``"zxing"``, ``"gemini"``, or ``""``).
        product_info: Dict returned by :func:`~gtin_extractor.gemini_integration.analyze_product_gemini`.

    Returns:
        Row dict keyed by :data:`FIELDNAMES`.
    """
    return {
        "filename": filename,
        "gtin": gtin,
        "gtin_detection_status": "validated" if gtin else "invalid",
        "gtin_detection_method": method,
        "manufacturer": product_info.get("manufacturer", ""),
        "ref": product_info.get("ref", ""),
        "ref_confidence": product_info.get("ref_confidence", ""),
        "product_name": product_info.get("product_name", ""),
        "product_specs": product_info.get("product_specs", ""),
    }


class CSVWriter:
    """Context-manager wrapper around :class:`csv.DictWriter` for incremental CSV output.

    Example::

        with CSVWriter("results.csv") as writer:
            writer.writerow(row)
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._file = None
        self._writer: csv.DictWriter | None = None

    def __enter__(self) -> "CSVWriter":
        self._file = open(self.path, "w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=FIELDNAMES)
        self._writer.writeheader()
        self._file.flush()
        return self

    def __exit__(self, *args: object) -> None:
        if self._file:
            self._file.close()

    def writerow(self, row: dict) -> None:
        """Write *row* to the CSV and flush immediately.

        Args:
            row: Dict keyed by :data:`FIELDNAMES`.
        """
        if self._writer is None:
            raise RuntimeError("CSVWriter is not open. Use it as a context manager.")
        self._writer.writerow(row)
        if self._file:
            self._file.flush()


def write_results_csv(rows: Iterator[dict], path: str | Path) -> None:
    """Write an iterable of result rows to a CSV file at *path*.

    Args:
        rows: Iterable of row dicts keyed by :data:`FIELDNAMES`.
        path: Destination CSV file path.
    """
    path = Path(path)
    with CSVWriter(path) as writer:
        for row in rows:
            writer.writerow(row)
    logger.info("Results exported to %s", path)
