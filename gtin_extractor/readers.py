"""Barcode reader implementations (pyzbar, zxing-cpp)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from gtin_extractor.validation import extract_gtin_from_raw

if TYPE_CHECKING:
    from PIL import Image as PILImage

logger = logging.getLogger("gtin_extractor.readers")


def decode_barcode_pyzbar(image: "PILImage.Image") -> str:
    """Decode a barcode from *image* using pyzbar.

    Args:
        image: A Pillow ``Image`` object to scan.

    Returns:
        A validated GTIN string, or ``""`` if nothing was found.
    """
    try:
        from pyzbar.pyzbar import decode as pyzbar_decode  # type: ignore[import]

        decoded_objects = pyzbar_decode(image)
        for obj in decoded_objects:
            data = obj.data.decode("utf-8")
            gtin = extract_gtin_from_raw(data)
            if gtin:
                return gtin
    except Exception as exc:
        logger.debug("pyzbar error: %s", exc)
    return ""


def decode_barcode_zxing(image: "PILImage.Image") -> str:
    """Decode a barcode from *image* using zxing-cpp.

    Args:
        image: A Pillow ``Image`` object to scan.

    Returns:
        A validated GTIN string, or ``""`` if nothing was found.
    """
    try:
        import zxingcpp  # type: ignore[import]

        barcodes = zxingcpp.read_barcodes(image, try_rotate=True, try_downscale=True)
        for barcode in barcodes:
            gtin = extract_gtin_from_raw(barcode.text)
            if gtin:
                return gtin
    except Exception as exc:
        logger.debug("zxing error: %s", exc)
    return ""


def process_image(
    image_path: str | Path,
    gemini_key: str | None = None,
    gemini_model: str = "gemini-2.0-flash",
) -> tuple[str, str]:
    """Process a single image and attempt to read a GTIN.

    Tries readers in order: pyzbar (with manual rotations) → zxing-cpp → Gemini.

    Args:
        image_path: Filesystem path to the image file.
        gemini_key: Optional Google Gemini API key; enables the AI fallback.
        gemini_model: Gemini model identifier to use for the AI fallback.

    Returns:
        A ``(gtin, method)`` tuple where *method* is one of ``"pyzbar"``,
        ``"zxing"``, ``"gemini"``, or ``""`` when nothing was found.
    """
    from PIL import Image  # type: ignore[import]

    image_path = str(image_path)

    try:
        with Image.open(image_path) as img:
            rotations = [0, 90, 180, 270]
            for angle in rotations:
                rotated = img.rotate(angle, expand=True) if angle != 0 else img
                result = decode_barcode_pyzbar(rotated)
                if result:
                    return result, "pyzbar"

            result = decode_barcode_zxing(img)
            if result:
                return result, "zxing"

        if gemini_key:
            from gtin_extractor.gemini_integration import decode_barcode_gemini

            result = decode_barcode_gemini(image_path, gemini_key, model=gemini_model)
            if result:
                return result, "gemini"

    except Exception as exc:
        logger.error("Error processing %s: %s", image_path, exc, exc_info=True)

    return "", ""
