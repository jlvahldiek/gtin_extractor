import os
import argparse
import re
import csv
import json
import time
from pathlib import Path
from PIL import Image
from pyzbar.pyzbar import decode as pyzbar_decode
import zxingcpp
import google.generativeai as genai
from tqdm import tqdm
from pyzbar.pyzbar import decode as pyzbar_decode
import zxingcpp
from tqdm import tqdm

def is_valid_gtin_checksum(barcode_data: str) -> bool:
    """Validate GTIN by checking its length and calculating the checksum."""
    if not barcode_data.isdigit():
        return False
    
    # GTIN can be 8, 12, 13, or 14 digits
    if len(barcode_data) not in (8, 12, 13, 14):
        return False
        
    # Checksum validation
    # The last digit is the check digit
    payload = barcode_data[:-1]
    check_digit = int(barcode_data[-1])
    
    # Calculate checksum
    # Reverse the payload, multiply by 3 or 1 alternating, and sum
    total = 0
    for i, char in enumerate(reversed(payload)):
        multiplier = 3 if i % 2 == 0 else 1
        total += int(char) * multiplier
        
    calculated_check = (10 - (total % 10)) % 10
    
    return check_digit == calculated_check


def extract_gtin_from_raw(raw_data: str) -> str:
    """Extract a valid GTIN from a raw barcode string (including GS1 strings)."""
    # 1. Try to find 14-digit GTIN following (01) or (02)
    match = re.search(r"\(0[12]\)(\d{14})", raw_data)
    if match:
        gtin = match.group(1)
        if is_valid_gtin_checksum(gtin):
            return gtin
            
    # 2. Standardize GS1 delimiters and search for 01 / 02
    s = raw_data.replace("\x1d", "|").replace("\x1e", "|").replace("^", "|")
    match = re.search(r"(?:^|\|)0[12](\d{14})", s)
    if match:
        gtin = match.group(1)
        if is_valid_gtin_checksum(gtin):
            return gtin
            
    # 3. Strip non-digits and look for a valid length GTIN
    digits = re.sub(r"\D", "", raw_data)
    
    # If the numeric string starts with 01 and has enough digits, grab the 14 digits
    if len(digits) >= 16 and (digits.startswith("01") or digits.startswith("02")):
        gtin = digits[2:16]
        if is_valid_gtin_checksum(gtin):
            return gtin
            
    if len(digits) in (8, 12, 13, 14):
        if is_valid_gtin_checksum(digits):
            return digits
            
    return ""


def decode_barcode_pyzbar(image: Image.Image) -> str:
    """Decode barcode using pyzbar"""
    try:
        decoded_objects = pyzbar_decode(image)
        for obj in decoded_objects:
            data = obj.data.decode('utf-8')
            gtin = extract_gtin_from_raw(data)
            if gtin:
                return gtin
    except Exception as e:
        print(f"pyzbar error: {e}")
        pass
    return ""


def decode_barcode_zxing(image: Image.Image) -> str:
    """Decode barcode using zxing-cpp"""
    try:
        barcodes = zxingcpp.read_barcodes(image, try_rotate=True, try_downscale=True)
        for barcode in barcodes:
            data = barcode.text
            gtin = extract_gtin_from_raw(data)
            if gtin:
                return gtin
    except Exception as e:
        print(f"zxing error: {e}")
        pass
    return ""


def decode_barcode_gemini(image_path: str, api_key: str) -> str:
    """Fallback: Decode barcode using Gemini APIs."""
    if not api_key:
        return ""
    
    # We add a retry loop to handle 429 Quota Exceeded errors from the free tier API.
    max_retries = 5
    base_delay = 10
    
    for attempt in range(max_retries):
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            prompt = (
                "Extract the GTIN(14) from the label in this image. "
                "Return ONLY a JSON object with a single key 'gtin' containing the string value. "
                "Example: {\"gtin\": \"00827002507791\"}"
            )
            img = Image.open(image_path)
            img = img.convert("RGB")  # Ensure RGB for Gemini compatibility (handles MPO, etc.)
            img.thumbnail((1600, 1600))
            resp = model.generate_content(
                [prompt, img], 
                generation_config={"response_mime_type": "application/json"}
            )
            data = json.loads(resp.text)
            gtin = data.get("gtin", "")
            
            # Validation
            if extract_gtin_from_raw(gtin):
                 return extract_gtin_from_raw(gtin)
            
            # If no exception and no GTIN found, break early to avoid endless retries on bad images
            break 
            
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "Quota exceeded" in err_str:
                # Identify specific quota type
                quota_type = "Unknown Quota"
                if "GenerateRequestsPerMinutePerProjectPerModel" in err_str:
                    quota_type = "Requests Per Minute (RPM)"
                elif "GenerateRequestsPerDayPerProjectPerModel" in err_str:
                    quota_type = "Daily Request Limit (RPD)"
                elif "GenerateContentInputTokensPerModelPerMinute" in err_str:
                    quota_type = "Input Token Limit"
                
                if attempt < max_retries - 1:
                    match = re.search(r"Please retry in ([\d\.]+)s", err_str)
                    if match:
                        sleep_time = float(match.group(1)) + 1.0
                    else:
                        sleep_time = base_delay * (attempt + 1)
                        
                    tqdm.write(f"Gemini {quota_type} hit. Retrying in {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
                else:
                    tqdm.write(f"Gemini error: {quota_type} exceeded after {max_retries} retries.")
            else:
                tqdm.write(f"Gemini error: {e}")
                break
                
    return ""


def process_image(image_path: str, gemini_key: str = None) -> tuple[str, str]:
    """Process a single image, attempting to read GTIN. Returns (gtin, method)."""
    try:
        with Image.open(image_path) as img:
            # We need to test pyzbar with rotations since it doesn't do it itself
            rotations = [0, 90, 180, 270]
            
            # Try pyzbar with manual rotations
            for angle in rotations:
                rotated_img = img.rotate(angle, expand=True) if angle != 0 else img
                result = decode_barcode_pyzbar(rotated_img)
                if result:
                    return result, "pyzbar"
            
            # If pyzbar fails, try zxing-cpp (which handles rotation internally)
            result = decode_barcode_zxing(img)
            if result:
                return result, "zxing"
                
        # If both primary methods fail, try Gemini
        if gemini_key:
            result = decode_barcode_gemini(image_path, gemini_key)
            if result:
                return result, "gemini"
                
    except Exception as e:
        tqdm.write(f"Error processing {image_path}: {e}")
        
    return "", ""


def main():
    parser = argparse.ArgumentParser(description="Extract GTINs from a directory of photos.")
    parser.add_argument("directory", nargs="?", default="fotos", help="Directory containing images")
    parser.add_argument("--csv", help="Path to output CSV file (e.g., results.csv)", default=None)
    parser.add_argument("--gemini-key", help="Google Gemini API Key for fallback processing", default=None)
    parser.add_argument("--limit", type=int, help="Limit the number of files to process", default=None)
    args = parser.parse_args()

    dir_path = Path(args.directory)
    if not dir_path.exists() or not dir_path.is_dir():
        print(f"Directory not found: {dir_path}")
        return

    print(f"Processing images in {dir_path}...")
    
    # Supported extensions
    valid_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif"}
    
    results = []
    
    # Filter valid files beforehand so tqdm knows the total length
    files_to_process = [f for f in dir_path.iterdir() if f.is_file() and f.suffix.lower() in valid_exts]
    
    if args.limit:
        files_to_process = files_to_process[:args.limit]
        print(f"Limiting processing to the first {args.limit} files.")
    
    for file_path in tqdm(files_to_process, desc="Scanning images"):
        gtin, method = process_image(str(file_path), gemini_key=args.gemini_key)
        if gtin:
            tqdm.write(f"Found GTIN: {gtin} in {file_path.name} (via {method})")
            results.append({"filename": file_path.name, "gtin": gtin, "status": "validated", "method": method})
        else:
            tqdm.write(f"No valid GTIN found in {file_path.name}")
            results.append({"filename": file_path.name, "gtin": "", "status": "invalid", "method": ""})

    if args.csv:
        csv_path = Path(args.csv)
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=["filename", "gtin", "gtin_detection_status", "gtin_detection_method"])
                writer.writeheader()
                writer.writerows(results)
            print(f"\nResults successfully exported to {csv_path}")
        except Exception as e:
            print(f"\nError writing to CSV {csv_path}: {e}")

if __name__ == "__main__":
    main()
