# AI-Only Product Extraction with GTIN Validation

This Python script performs **batch AI-based extraction** of product information (GTIN, reference, manufacturer, product name, product size) from images using **OpenAI GPT‑5.1**. It validates GTINs using the official checksum algorithm.

---

## Features

- AI-only extraction (no barcode libraries)
- Supports **HEIC, JPEG, PNG, WebP**
- Automatic **HEIC → JPEG conversion** on macOS
- Parallel processing for batch speed
- Outputs CSV with `gtin_valid` and `confidence` columns
- Optional OCR-like correction of GTIN digits

---

## Requirements

- Python 3.11+
- macOS (for built-in `sips`) or modify for other OS image conversion
- OpenAI API Key

Install Python dependencies:

```bash
pip install -r requirements.txt

## Run
export OPENAI_API_KEY="your_api_key_here"

python3 batch_ai_gtin_validated.py "Extract product info" ./fotos batch_products_validated.csv 4
