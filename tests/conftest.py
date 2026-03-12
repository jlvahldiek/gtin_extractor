"""Pytest fixtures and shared test data for gtin_extractor tests."""

from __future__ import annotations

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Sample GTIN data
# ---------------------------------------------------------------------------

VALID_GTINS = [
    "00012345678905",  # GTIN-14
    "0012345678905",  # GTIN-13 (EAN-13)
    "012345678905",  # GTIN-12 (UPC-A) - 12 digits
    "00000000",  # GTIN-8 minimal (all zeros with valid check)
]

# Well-known valid GTINs used in tests
GTIN_14_VALID = "00012345678905"
GTIN_13_VALID = "5901234123457"
GTIN_12_VALID = "012345678905"
GTIN_8_VALID = "96385074"

INVALID_GTINS = [
    "",
    "abc",
    "1234567",  # 7 digits – not a valid GTIN length
    "123456789012345",  # 15 digits – too long
    "00012345678900",  # wrong check digit
    "5901234123450",  # wrong check digit on 13-digit
]

# ---------------------------------------------------------------------------
# Sample images metadata (mirrors sample_images/ directory)
# ---------------------------------------------------------------------------

#: Root directory of the repository (parent of ``tests/``).
REPO_ROOT = Path(__file__).parent.parent

#: Directory containing sample product label images.
SAMPLE_IMAGES_DIR = REPO_ROOT / "sample_images"

#: Expected GTINs for each sample image file.
SAMPLE_IMAGE_GTINS: dict[str, str] = {
    "performa_catheter.jpg": "00884450003534",
    "prelude_sheath.jpg": "10884450614911",
    "radifocus_introducer.jpg": "08935221212180",
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def valid_gtin_14() -> str:
    """Return a valid GTIN-14 string."""
    return GTIN_14_VALID


@pytest.fixture
def valid_gtin_13() -> str:
    """Return a valid GTIN-13 string."""
    return GTIN_13_VALID


@pytest.fixture
def valid_gtin_8() -> str:
    """Return a valid GTIN-8 string."""
    return GTIN_8_VALID


@pytest.fixture
def tmp_config_dir(tmp_path):
    """Return a temporary directory for config file tests."""
    return tmp_path


@pytest.fixture
def sample_images_dir() -> Path:
    """Return the path to the sample_images/ directory."""
    return SAMPLE_IMAGES_DIR
