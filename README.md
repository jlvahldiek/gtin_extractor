# GTIN Barcode Extractor

A robust Python tool for batch extracting and validating GTINs (Global Trade Item Numbers) from product photos. It uses multiple barcode libraries and an AI-powered fallback to ensure maximum detection rates even for difficult, rotated, or partially obscured labels.

---

## Features

- **Multi-Library Detection**: Combines `pyzbar` and `zxing-cpp` for industry-standard barcode scanning.
- **Manual & Native Rotation**: Manually rotates images to find barcodes in any orientation.
- **GS1 Support**: Intelligent parsing of GS1-formatted strings (e.g., extracting GTIN from `(01)0871...`).
- **Gemini AI Fallback**: Uses the modern `google-genai` SDK and `gemini-2.0-flash` (or newer) to analyze photos where traditional scans fail.
- **Batch Processing**: Scans entire directories with a high-performance progress bar (`tqdm`).
- **Detection Tracking**: Tracks and records which method successfully found each GTIN.
- **CSV Export**: Detailed reporting including filename, GTIN, validation status, and extraction method.

---

## Requirements

### Non-Python Dependencies
The following system libraries are required for the barcode scanning packages:

- **macOS**: `brew install zbar`
- **Linux**: `sudo apt-get install libzbar0`

### Python Dependencies
Install the required packages via pip:

```bash
pip install -r requirements.txt
```

---

## Usage

### Basic Scan
Process all images in the default `fotos/` directory:

```bash
python3 gtin_barcode_extractor.py fotos/ --csv output.csv
```

### With AI Fallback
Use a Google Gemini API key to enable AI-powered extraction for failed barcodes:

```bash
python3 gtin_barcode_extractor.py fotos/ --gemini-key YOUR_API_KEY --csv results.csv
```

### Advanced Options
- `directory`: The source folder containing images (default: `fotos`).
- `--csv`: Path to the output CSV file.
- `--gemini-key`: Your Google Gemini API key (enables AI fallback).
- `--limit`: Limit the number of files processed (e.g., `--limit 5`).

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
| `product_name` | Commercial product name extracted by Gemini |
| `product_specs` | Key product specifications extracted by Gemini (semicolon-separated) |
