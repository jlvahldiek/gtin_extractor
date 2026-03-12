"""Integration tests using real sample product label images.

These tests scan the JPEG files in ``sample_images/`` with the actual
barcode detection pipeline (no mocks) to verify end-to-end extraction.

They are skipped automatically when the ``sample_images/`` directory is
absent or a particular image file is missing, so CI without the asset
directory still passes.
"""

from __future__ import annotations

import pytest

from tests.conftest import SAMPLE_IMAGE_GTINS, SAMPLE_IMAGES_DIR
from gtin_extractor.readers import process_image
from gtin_extractor.validation import is_valid_gtin_checksum

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _skip_if_missing(filename: str):
    """Return a pytest.mark.skipif marker if the image file does not exist."""
    path = SAMPLE_IMAGES_DIR / filename
    return pytest.mark.skipif(
        not path.exists(),
        reason=f"Sample image not found: {path}",
    )


# ---------------------------------------------------------------------------
# Parametrised detection tests
# ---------------------------------------------------------------------------


class TestSampleImageGtinExtraction:
    """Verify that each sample image yields the expected GTIN."""

    @pytest.mark.parametrize("filename,expected_gtin", list(SAMPLE_IMAGE_GTINS.items()))
    def test_gtin_detected(self, filename: str, expected_gtin: str):
        """process_image() should detect the expected GTIN from the sample image."""
        image_path = SAMPLE_IMAGES_DIR / filename
        if not image_path.exists():
            pytest.skip(f"Sample image not found: {image_path}")

        gtin, method = process_image(str(image_path))

        assert gtin == expected_gtin, (
            f"Expected GTIN {expected_gtin!r} from {filename!r}, "
            f"got {gtin!r} (method={method!r})"
        )
        assert method in (
            "pyzbar",
            "zxing",
            "gemini",
        ), f"Unexpected detection method {method!r} for {filename!r}"


class TestSampleImageGtinValidity:
    """Verify that each expected sample GTIN passes the checksum validator."""

    @pytest.mark.parametrize("filename,expected_gtin", list(SAMPLE_IMAGE_GTINS.items()))
    def test_expected_gtin_is_valid(self, filename: str, expected_gtin: str):
        """The known-good GTINs for every sample image must pass the GS1 checksum."""
        assert is_valid_gtin_checksum(expected_gtin), (
            f"Expected GTIN {expected_gtin!r} for {filename!r} "
            "does not pass the GS1 checksum validation."
        )


class TestSampleImagesExist:
    """Verify that every declared sample image file is present on disk."""

    @pytest.mark.parametrize("filename", list(SAMPLE_IMAGE_GTINS.keys()))
    def test_image_file_exists(self, filename: str):
        path = SAMPLE_IMAGES_DIR / filename
        assert path.exists(), f"Missing sample image: {path}"
        assert path.stat().st_size > 0, f"Sample image is empty: {path}"
