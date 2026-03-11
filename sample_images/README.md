# Sample Product Label Images

This directory contains example product label photographs used for testing
and showcasing the GTIN Extractor tool.

All images contain a GS1-128 barcode encoding a 14-digit GTIN that can be
detected by the `pyzbar` / `zxing-cpp` barcode readers built into the package.

---

## Images

### `performa_catheter.jpg`

| Field | Value |
|---|---|
| **Product** | Performa® Angiographic Catheter |
| **Manufacturer** | Merit Medical |
| **REF** | 7701-A0 |
| **LOT** | I2759901 |
| **Use By** | 2025-12-31 |
| **GTIN-14** | `00884450003534` |
| **Barcode format** | GS1-128 `(01)00884450003534(17)251231(10)I2759901` |

---

### `prelude_sheath.jpg`

| Field | Value |
|---|---|
| **Product** | Prelude® Sheath Introducer |
| **Manufacturer** | Merit Medical |
| **REF** | PSI-4F-23-035 |
| **LOT** | H3140944 |
| **Use By** | 2028-02-10 |
| **GTIN-14** | `10884450614911` |
| **Barcode format** | GS1-128 `(01)10884450614911(17)280210(10)H3140944` |

---

### `radifocus_introducer.jpg`

| Field | Value |
|---|---|
| **Product** | Radifocus® Introducer II |
| **Manufacturer** | Terumo |
| **REF** | RS*R60G07PQ |
| **LOT** | 250515VB |
| **Use By** | 2027-10-31 |
| **GTIN-14** | `08935221212180` |
| **Barcode format** | GS1-128 `(01)08935221212180(17)271031(10)250515VB` |

---

## Quick scan

```bash
# Scan all sample images with the CLI
python -m gtin_extractor sample_images/ --csv sample_results.csv

# Or using Docker
docker run --rm -v $(pwd)/sample_images:/data gtin_extractor \
    python -m gtin_extractor /data --csv /data/results.csv
```

## Running the tests

```bash
pytest tests/test_sample_images.py -v
```
