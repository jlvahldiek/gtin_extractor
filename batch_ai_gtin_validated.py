#!/usr/bin/env python3
import os
import sys
import base64
import json
import csv
import mimetypes
import subprocess
from pathlib import Path
import requests
from concurrent.futures import ThreadPoolExecutor

# -----------------------------
API_KEY = os.environ.get("OPENAI_API_KEY")
MODEL = "gpt-5.1"
PARALLEL_JOBS = 4

if not API_KEY:
    print("❌ Please set OPENAI_API_KEY environment variable.")
    sys.exit(1)
# -----------------------------

# GTIN validation
def validate_gtin(gtin: str) -> bool:
    """Return True if GTIN passes checksum (GTIN-8,12,13,14)"""
    digits = ''.join(filter(str.isdigit, gtin))
    if len(digits) not in (8,12,13,14):
        return False
    total = 0
    for i, d in enumerate(digits[:-1]):
        n = int(d)
        if (len(digits)-i) % 2 == 0:
            total += n * 3
        else:
            total += n
    check_digit = (10 - (total % 10)) % 10
    return check_digit == int(digits[-1])

def fix_gtin(gtin: str) -> str:
    """Correct common AI OCR errors in GTIN"""
    replacements = {'O':'0','o':'0','I':'1','l':'1','B':'8','S':'5'}
    gtin = ''.join(replacements.get(c, c) for c in gtin)
    return ''.join(filter(str.isdigit, gtin))

# HEIC → JPEG
def convert_heic_to_jpeg(path: Path) -> Path:
    tmp_file = Path(f"/tmp/tmp_{path.stem}.jpg")
    subprocess.run(["sips", "-s", "format", "jpeg", str(path), "--out", str(tmp_file)], check=True)
    return tmp_file

def encode_image_base64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

# AI extraction
def ai_extract_info(image_path: Path, prompt: str):
    ext = image_path.suffix.lower()
    if ext == ".heic":
        img_to_send = convert_heic_to_jpeg(image_path)
        mime_type = "image/jpeg"
    else:
        img_to_send = image_path
        mime_type, _ = mimetypes.guess_type(str(image_path))
        if mime_type is None:
            mime_type = "application/octet-stream"

    image_base64 = encode_image_base64(img_to_send)
    image_data_url = f"data:{mime_type};base64,{image_base64}"

    payload = {
        "model": MODEL,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text",
                     "text": f"Return ONLY valid JSON with gtin, ref, manufacturer, product_name, product_size. {prompt}"},
                    {"type": "input_image",
                     "image_url": image_data_url}
                ]
            }
        ]
    }

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    response = requests.post("https://api.openai.com/v1/responses",
                             headers=headers,
                             json=payload)
    response.raise_for_status()
    data = response.json()

    text = ""
    if "output_text" in data and data["output_text"]:
        text = data["output_text"]
    elif "output" in data and len(data["output"]) > 0:
        content = data["output"][0].get("content", [])
        if len(content) > 0:
            text = content[0].get("text", "")

    # Parse JSON
    try:
        json_data = json.loads(text)
        gtin = fix_gtin(json_data.get("gtin",""))
        ref = json_data.get("ref","")
        manufacturer = json_data.get("manufacturer","")
        product_name = json_data.get("product_name","")
        product_size = json_data.get("product_size","")
    except Exception:
        import re
        def extract(key):
            match = re.search(rf'"?{key}"?\s*[:=]\s*"?([^",\n]+)"?', text, re.I)
            return match.group(1).strip() if match else ""
        gtin = fix_gtin(extract("gtin"))
        ref = extract("ref")
        manufacturer = extract("manufacturer")
        product_name = extract("product_name")
        product_size = extract("product_size")

    gtin_valid = validate_gtin(gtin)
    confidence = 1.0 if gtin_valid else 0.5
    return gtin, ref, manufacturer, product_name, product_size, gtin_valid, confidence

def process_image(image_path: Path, prompt: str):
    basename = image_path.name
    try:
        result = ai_extract_info(image_path, prompt)
        print(f"✅ {basename} processed (GTIN: {result[0]}, valid={result[5]})")
        return [basename] + list(result)
    except Exception as e:
        print(f"❌ {basename} Error: {e}")
        return [basename,"","","","","",False,0.0]

def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <prompt> <folder> [output_csv] [parallel_jobs]")
        sys.exit(1)

    prompt = sys.argv[1]
    folder = Path(sys.argv[2])
    output_csv = sys.argv[3] if len(sys.argv) > 3 else "batch_products_validated.csv"
    parallel_jobs = int(sys.argv[4]) if len(sys.argv) > 4 else PARALLEL_JOBS

    image_files = [f for f in folder.glob("*") if f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp", ".heic"]]

    results = []
    with ThreadPoolExecutor(max_workers=parallel_jobs) as executor:
        futures = [executor.submit(process_image, f, prompt) for f in image_files]
        for future in futures:
            results.append(future.result())

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["filename","gtin","ref","manufacturer","product_name","product_size","gtin_valid","confidence"])
        writer.writerows(results)

    print(f"🎉 All images processed. CSV saved to {output_csv}")

if __name__ == "__main__":
    main()
