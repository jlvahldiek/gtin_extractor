# GTIN Barcode Extractor

A robust Python tool for batch extracting and validating GTINs (Global Trade Item Numbers) from product photos. It uses multiple barcode libraries and an AI-powered fallback to ensure maximum detection rates even for difficult, rotated, or partially obscured labels.

[![Tests](https://github.com/jlvahldiek/gtin_extractor/actions/workflows/tests.yml/badge.svg)](https://github.com/jlvahldiek/gtin_extractor/actions/workflows/tests.yml)
[![Lint](https://github.com/jlvahldiek/gtin_extractor/actions/workflows/lint.yml/badge.svg)](https://github.com/jlvahldiek/gtin_extractor/actions/workflows/lint.yml)

---

## Features

- **Multi-Library Detection**: Combines `pyzbar` and `zxing-cpp` for industry-standard barcode scanning.
- **Manual & Native Rotation**: Manually rotates images to find barcodes in any orientation.
- **GS1 Support**: Intelligent parsing of GS1-formatted strings (e.g., extracting GTIN from `(01)0871...`).
- **Gemini AI Fallback**: Uses the modern `google-genai` SDK and `gemini-2.0-flash` (or newer) to analyze photos where traditional scans fail.
- **Batch Processing**: Scans entire directories with a high-performance progress bar (`tqdm`).
- **Detection Tracking**: Tracks and records which method successfully found each GTIN.
- **CSV Export**: Detailed reporting including filename, GTIN, validation status, and extraction method.
- **Structured Logging**: Configurable log levels (DEBUG, INFO, WARNING, ERROR) with optional file output.
- **Configuration Management**: YAML config files and environment variable support.

---

## Installation

### From source

```bash
git clone https://github.com/jlvahldiek/gtin_extractor.git
cd gtin_extractor
pip install -e .
```

### Via pip (once published to PyPI)

```bash
pip install gtin-extractor
```

### System dependencies

The `pyzbar` library requires the `zbar` shared library:

- **macOS**: `brew install zbar`
- **Linux**: `sudo apt-get install libzbar0`

### Python dependencies

```bash
pip install -r requirements.txt
```

---

## Usage

### As a Python module (recommended)

```bash
# Basic scan
python -m gtin_extractor fotos/ --csv output.csv

# With Gemini AI fallback
python -m gtin_extractor fotos/ --gemini-key YOUR_API_KEY --csv results.csv

# With custom config file
python -m gtin_extractor --config config.yaml
```

### Legacy script (backward compatibility)

```bash
python3 gtin_barcode_extractor.py fotos/ --csv output.csv
```

### CLI Options

| Option | Description | Default |
|---|---|---|
| `directory` | Directory containing images | `fotos` (or config value) |
| `--csv` | Output CSV file path | none |
| `--gemini-key` | Google Gemini API key | none |
| `--gemini-model` | Gemini model to use | `gemini-2.0-flash` |
| `--limit N` | Process only the first N images | none |
| `--log-level` | Logging verbosity (`DEBUG`/`INFO`/`WARNING`/`ERROR`) | `INFO` |
| `--log-file` | Write logs to file | none |
| `--config` | Path to `config.yaml` | `config.yaml` |

---

## Configuration

Create a `config.yaml` file in the working directory (all keys optional):

```yaml
image_dir: fotos
csv_output: results.csv
gemini_api_key: YOUR_KEY_HERE
gemini_model: gemini-2.0-flash
max_retries: 5
base_delay: 10.0
log_level: INFO
log_file: gtin_extractor.log
limit: null
```

Environment variables override YAML values. All variables are prefixed with `GTIN_`:

```bash
export GTIN_GEMINI_API_KEY=your-key
export GTIN_LOG_LEVEL=DEBUG
export GTIN_IMAGE_DIR=/path/to/images
```

---

## Package Structure

```
gtin_extractor/          ← Python package
├── __init__.py          ← Public API and version
├── __main__.py          ← CLI entry point
├── validation.py        ← GTIN checksum validation
├── readers.py           ← pyzbar / zxing-cpp barcode readers
├── gemini_integration.py← Gemini AI barcode extraction & product analysis
├── csv_export.py        ← CSV writing utilities
├── config.py            ← Configuration loading
└── logging_config.py    ← Logging setup
tests/
├── conftest.py
├── test_validation.py
├── test_readers.py
└── test_config.py
```

---

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions, coding conventions, and the PR workflow.

```bash
# Quick start
pip install -r requirements-dev.txt
make test       # run tests with coverage
make lint       # flake8 + pylint + black check
make format     # auto-format with black
make typecheck  # mypy type check
```

---

## How It Works

1. **Scan Phase 1 (`pyzbar`)**: Tries to find a barcode using `pyzbar` at 0, 90, 180, and 270-degree rotations.
2. **Scan Phase 2 (`zxing-cpp`)**: Falls back to `zxing-cpp` with native rotation and downscaling features enabled.
3. **Scan Phase 3 (Gemini GTIN fallback)**: If enabled, sends the image to Google's Gemini API for intelligent visual GTIN extraction.
4. **Product Analysis (Gemini)**: After GTIN detection, sends each image to Gemini to extract product metadata: manufacturer, REF number, product name, and key specifications.
5. **Validation**: Every extracted GTIN is validated using a length check and the GS1 checksum algorithm before being recorded.

---

## Output CSV Columns

| Column | Description |
|---|---|
| `filename` | Source image filename |
| `gtin` | Extracted & validated GTIN (empty if none found) |
| `gtin_detection_status` | `validated` or `invalid` |
| `gtin_detection_method` | `pyzbar`, `zxing`, or `gemini` |
| `manufacturer` | Brand/manufacturer name extracted by Gemini |
| `ref` | REF/catalog number extracted by Gemini |
| `ref_confidence` | Confidence in the REF number (`high`, `medium`, `low`) |
| `product_name` | Commercial product name extracted by Gemini |
| `product_specs` | Key product specifications extracted by Gemini (semicolon-separated) |

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.
