# GTIN Barcode Extractor

A robust Python tool for batch extracting and validating GTINs (Global Trade Item Numbers) from product photos. It uses multiple barcode libraries and an AI-powered fallback to ensure maximum detection rates even for difficult, rotated, or partially obscured labels.

[![Tests](https://github.com/jlvahldiek/gtin_extractor/actions/workflows/tests.yml/badge.svg)](https://github.com/jlvahldiek/gtin_extractor/actions/workflows/tests.yml)
[![Lint](https://github.com/jlvahldiek/gtin_extractor/actions/workflows/lint.yml/badge.svg)](https://github.com/jlvahldiek/gtin_extractor/actions/workflows/lint.yml)

---

## Features

- **Multi-Library Detection**: Combines `pyzbar` and `zxing-cpp` for industry-standard barcode scanning.
- **Manual & Native Rotation**: Manually rotates images to find barcodes in any orientation.
- **GS1 Support**: Intelligent parsing of GS1-formatted strings (e.g., extracting GTIN from `(01)0871...`).
- **AI Fallback (Gemini or OpenAI)**: Supports both Google Gemini (`google-genai`) and OpenAI vision models for difficult scans and product metadata extraction.
- **Batch Processing**: Scans entire directories with a high-performance progress bar (`tqdm`).
- **Detection Tracking**: Tracks and records which method successfully found each GTIN.
- **Duplicate Removal**: Optional `--remove-duplicates` flag deduplicates the final CSV by GTIN value.
- **Web UI**: Platform-independent browser-based interface — upload images, view results in a table, and download CSV (requires `Flask`).
- **Docker Support**: Ready-to-use `Dockerfile` and `docker-compose.yml` for containerised deployment.
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

# Optional extras
pip install -e ".[config]"    # YAML config + .env file support
pip install -e ".[web]"       # Flask Web UI
```

### Via pip (once published to PyPI)

```bash
pip install gtin-extractor
pip install "gtin-extractor[web]"   # include Web UI
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
python -m gtin_extractor fotos/ --ai-provider gemini --gemini-key YOUR_API_KEY --csv results.csv

# With OpenAI AI fallback
python -m gtin_extractor fotos/ --ai-provider openai --openai-key YOUR_API_KEY --csv results.csv

# Remove duplicate GTINs from the output CSV
python -m gtin_extractor fotos/ --csv results.csv --remove-duplicates

# With custom config file
python -m gtin_extractor --config config.yaml
```

### Web UI

Install Flask and launch the browser-based interface:

```bash
pip install gtin_extractor[web]
gtin-web                        # opens on http://localhost:5000
# or
python -m gtin_extractor.web --port 5000
```

Then open [http://localhost:5000](http://localhost:5000) in any browser on any platform.
The Web UI lets you upload images, set options (Gemini key, duplicate removal), view
results in a table, and download the CSV — all without using the command line.

### Docker

Build the image and run the Web UI:

```bash
docker build -t gtin_extractor .
docker run --rm -p 5000:5000 gtin_extractor
# open http://localhost:5000
```

Or use Docker Compose:

```bash
docker compose up          # starts the Web UI on port 5000
```

Process a local folder with the CLI via Docker:

```bash
docker compose run --rm gtin-cli
# or pass a custom directory:
docker run --rm -v /path/to/images:/data gtin_extractor \
    python -m gtin_extractor /data --csv /data/results.csv --remove-duplicates
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
| `--ai-provider` | AI provider to use (`gemini` or `openai`) | `gemini` |
| `--gemini-key` | Google Gemini API key | none |
| `--gemini-model` | Gemini model to use | `gemini-2.0-flash` |
| `--openai-key` | OpenAI API key | none |
| `--openai-model` | OpenAI model to use | `gpt-4.1-mini` |
| `--limit N` | Process only the first N images | none |
| `--remove-duplicates` | Remove rows with duplicate GTINs from CSV | off |
| `--log-level` | Logging verbosity (`DEBUG`/`INFO`/`WARNING`/`ERROR`) | `INFO` |
| `--log-file` | Write logs to file | none |
| `--config` | Path to `config.yaml` | `config.yaml` |

---

## Configuration

Create a `config.yaml` file in the working directory (all keys optional):

```yaml
image_dir: fotos
csv_output: results.csv
ai_provider: gemini
gemini_api_key: YOUR_KEY_HERE
gemini_model: gemini-2.0-flash
openai_api_key: YOUR_OPENAI_KEY_HERE
openai_model: gpt-4.1-mini
max_retries: 5
base_delay: 10.0
log_level: INFO
log_file: gtin_extractor.log
limit: null
remove_duplicates: false
```

Environment variables override YAML values. All variables are prefixed with `GTIN_`:

```bash
export GTIN_GEMINI_API_KEY=your-key
export GTIN_OPENAI_API_KEY=your-openai-key
export GTIN_AI_PROVIDER=openai
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
├── csv_export.py        ← CSV writing utilities + deduplication
├── config.py            ← Configuration loading
├── logging_config.py    ← Logging setup
├── web.py               ← Flask Web UI entry point
└── templates/           ← HTML templates for Web UI
    ├── index.html
    └── results.html
sample_images/           ← Example product label photos for testing & demo
├── performa_catheter.jpg   (GTIN 00884450003534 – Merit Medical Performa)
├── prelude_sheath.jpg      (GTIN 10884450614911 – Merit Medical Prelude)
├── radifocus_introducer.jpg(GTIN 08935221212180 – Terumo Radifocus II)
└── README.md
tests/
├── conftest.py
├── test_validation.py
├── test_readers.py
├── test_csv_export.py
├── test_config.py
└── test_sample_images.py← Integration tests using real sample images
Dockerfile               ← Docker image definition
docker-compose.yml       ← Docker Compose configuration
```

---

## Sample Images

The `sample_images/` directory contains three ready-to-scan medical device
product label images for demonstration and integration testing:

| File | Product | GTIN |
|---|---|---|
| `performa_catheter.jpg` | Merit Medical – Performa® Angiographic Catheter | `00884450003534` |
| `prelude_sheath.jpg` | Merit Medical – Prelude® Sheath Introducer | `10884450614911` |
| `radifocus_introducer.jpg` | Terumo – Radifocus® Introducer II | `08935221212180` |

Try the samples immediately after installation:

```bash
python -m gtin_extractor sample_images/ --csv sample_results.csv
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
3. **Scan Phase 3 (AI GTIN fallback)**: If enabled, sends the image to Gemini or OpenAI for intelligent visual GTIN extraction.
4. **Product Analysis (AI)**: After GTIN detection, sends each image to the selected AI provider to extract product metadata: manufacturer, REF number, product name, and key specifications.
5. **Validation**: Every extracted GTIN is validated using a length check and the GS1 checksum algorithm before being recorded.

---

## Output CSV Columns

| Column | Description |
|---|---|
| `filename` | Source image filename |
| `gtin` | Extracted & validated GTIN (empty if none found) |
| `gtin_detection_status` | `validated` or `invalid` |
| `gtin_detection_method` | `pyzbar`, `zxing`, or `gemini` |
| `manufacturer` | Brand/manufacturer name extracted by AI |
| `ref` | REF/catalog number extracted by AI |
| `ref_confidence` | Confidence in the REF number (`high`, `medium`, `low`) |
| `product_name` | Commercial product name extracted by AI |
| `product_specs` | Key product specifications extracted by AI (semicolon-separated) |

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.
