"""AI API integration for barcode and product-label analysis.

This module keeps backward-compatible Gemini helpers and adds OpenAI support.
"""

from __future__ import annotations

import json
import logging
import re
import time
from base64 import b64encode
from pathlib import Path
from typing import Any

from gtin_extractor.validation import extract_gtin_from_raw

logger = logging.getLogger("gtin_extractor.gemini")


def _gemini_retry(
    client: object,
    model: str,
    prompt_parts: list,
    max_retries: int = 5,
    base_delay: float = 10.0,
) -> dict:
    """Call the Gemini API with automatic quota-aware retry logic.

    Args:
        client: Initialised ``genai.Client`` instance.
        model: Gemini model identifier string.
        prompt_parts: List of prompt parts (strings and/or images) to send.
        max_retries: Maximum number of attempts before giving up.
        base_delay: Base back-off delay in seconds (multiplied by attempt number).

    Returns:
        Parsed JSON response dict, or ``{}`` on failure.
    """
    for attempt in range(max_retries):
        try:
            resp = client.models.generate_content(  # type: ignore[attr-defined]
                model=model,
                contents=prompt_parts,
                config={"response_mime_type": "application/json"},
            )
            result: dict[str, Any] = json.loads(resp.text)
            return result
        except Exception as exc:
            err_str = str(exc).lower()
            if "429" in err_str or "quota" in err_str:
                quota_type = "Unknown Quota"
                if "requestsperminute" in err_str:
                    quota_type = "Requests Per Minute (RPM)"
                elif "requestsperday" in err_str:
                    quota_type = "Daily Request Limit (RPD)"
                elif "tokensperminute" in err_str:
                    quota_type = "Input Token Limit"

                if attempt < max_retries - 1:
                    match = re.search(r"retry in ([\d\.]+)s", err_str)
                    sleep_time = (
                        float(match.group(1)) + 1.0 if match else base_delay * (attempt + 1)
                    )
                    logger.warning(
                        "Gemini %s hit. Retrying in %.1fs… (attempt %d/%d)",
                        quota_type,
                        sleep_time,
                        attempt + 1,
                        max_retries,
                    )
                    time.sleep(sleep_time)
                else:
                    logger.error("Gemini %s exceeded after %d retries.", quota_type, max_retries)
            else:
                logger.error("Gemini API error: %s", exc, exc_info=True)
                break
    return {}


def _openai_retry(
    client: object,
    model: str,
    messages: list[dict[str, Any]],
    max_retries: int = 5,
    base_delay: float = 10.0,
) -> dict:
    """Call the OpenAI API with automatic quota-aware retry logic."""
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(  # type: ignore[attr-defined]
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
            )
            content = (resp.choices[0].message.content or "").strip()
            result: dict[str, Any] = json.loads(content)
            return result
        except Exception as exc:
            err_str = str(exc).lower()
            if "429" in err_str or "rate limit" in err_str or "quota" in err_str:
                if attempt < max_retries - 1:
                    sleep_time = base_delay * (attempt + 1)
                    logger.warning(
                        "OpenAI quota/rate limit hit. Retrying in %.1fs... (attempt %d/%d)",
                        sleep_time,
                        attempt + 1,
                        max_retries,
                    )
                    time.sleep(sleep_time)
                else:
                    logger.error("OpenAI quota/rate limit exceeded after %d retries.", max_retries)
            else:
                logger.error("OpenAI API error: %s", exc, exc_info=True)
                break
    return {}


def _image_as_data_url(image_path: str) -> str:
    """Return image bytes as a data URL for OpenAI vision inputs."""
    suffix = Path(image_path).suffix.lower()
    mime = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
    }.get(suffix, "image/jpeg")
    encoded = b64encode(Path(image_path).read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def decode_barcode_gemini(
    image_path: str,
    api_key: str,
    model: str = "gemini-2.0-flash",
) -> str:
    """Use the Gemini API to extract a GTIN from a product label image.

    This function is the AI-powered fallback when conventional barcode readers
    have failed to produce a result.

    Args:
        image_path: Filesystem path to the image file.
        api_key: Google Gemini API key.
        model: Gemini model identifier (default: ``gemini-2.0-flash``).

    Returns:
        A validated GTIN string, or ``""`` if extraction failed.
    """
    if not api_key:
        return ""

    from google import genai  # type: ignore[import]
    from PIL import Image  # type: ignore[import]

    client = genai.Client(api_key=api_key)
    prompt = (
        "Extract the GTIN(14) from the label in this image. "
        "Return ONLY a JSON object with a single key 'gtin' containing the string value. "
        'Example: {"gtin": "00827002507791"}'
    )

    try:
        img = Image.open(image_path).convert("RGB")
        img.thumbnail((1600, 1600))

        data = _gemini_retry(client, model, [prompt, img])
        gtin = data.get("gtin", "")
        return extract_gtin_from_raw(gtin)
    except Exception as exc:
        logger.error("Gemini barcode decode error for %s: %s", image_path, exc, exc_info=True)
        return ""


def analyze_product_gemini(
    image_path: str,
    api_key: str,
    model: str = "gemini-2.0-flash",
) -> dict:
    """Analyse a product label and extract structured metadata via Gemini.

    Args:
        image_path: Filesystem path to the image file.
        api_key: Google Gemini API key.
        model: Gemini model identifier (default: ``gemini-2.0-flash``).

    Returns:
        Dict with keys ``manufacturer``, ``ref``, ``ref_confidence``,
        ``product_name``, ``product_specs``, or an empty dict on failure.
    """
    if not api_key:
        return {}

    from google import genai  # type: ignore[import]
    from PIL import Image  # type: ignore[import]

    client = genai.Client(api_key=api_key)
    prompt = (
        "Analyze this product label and extract the following information. "
        "Return ONLY a JSON object with these exact keys:\n"
        "- 'manufacturer': The brand or manufacturer name.\n"
        "- 'ref': The REF or catalog/article number "
        "(often labeled 'REF', 'Cat.', 'Art.', or 'No.').\n"
        "- 'ref_confidence': Your confidence in the extracted REF number. "
        "Use exactly one of: 'high' (clearly labeled as REF/Cat/Art), "
        "'medium' (plausible but ambiguous label), or 'low' (uncertain or inferred).\n"
        "- 'product_name': The commercial name or description of the product.\n"
        "- 'product_specs': A concise summary of key product specifications "
        "(e.g., size, material, quantity, sterility). Separate multiple specs with a semicolon.\n"
        "If a field is not found, use an empty string.\n"
        'Example: {"manufacturer": "Medline", "ref": "DYND74155", "ref_confidence": "high", '
        '"product_name": "Sterile Gloves", "product_specs": "Size 7.5; Latex; Sterile"}'
    )

    try:
        img = Image.open(image_path).convert("RGB")
        img.thumbnail((1600, 1600))
        data = _gemini_retry(client, model, [prompt, img])
        return {
            "manufacturer": data.get("manufacturer", ""),
            "ref": data.get("ref", ""),
            "ref_confidence": data.get("ref_confidence", ""),
            "product_name": data.get("product_name", ""),
            "product_specs": data.get("product_specs", ""),
        }
    except Exception as exc:
        logger.error("Product analysis error for %s: %s", image_path, exc, exc_info=True)
        return {}


def decode_barcode_openai(
    image_path: str,
    api_key: str,
    model: str = "gpt-4.1-mini",
) -> str:
    """Use the OpenAI API to extract a GTIN from a product label image."""
    if not api_key:
        return ""

    from openai import OpenAI  # type: ignore[import]

    client = OpenAI(api_key=api_key)
    prompt = (
        "Extract the GTIN(14) from the label in this image. "
        "Return ONLY a JSON object with a single key 'gtin' containing the string value. "
        'Example: {"gtin": "00827002507791"}'
    )

    try:
        image_url = _image_as_data_url(image_path)
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ]
        data = _openai_retry(client, model, messages)
        gtin = data.get("gtin", "")
        return extract_gtin_from_raw(gtin)
    except Exception as exc:
        logger.error("OpenAI barcode decode error for %s: %s", image_path, exc, exc_info=True)
        return ""


def analyze_product_openai(
    image_path: str,
    api_key: str,
    model: str = "gpt-4.1-mini",
) -> dict:
    """Analyse a product label and extract structured metadata via OpenAI."""
    if not api_key:
        return {}

    from openai import OpenAI  # type: ignore[import]

    client = OpenAI(api_key=api_key)
    prompt = (
        "Analyze this product label and extract the following information. "
        "Return ONLY a JSON object with these exact keys:\n"
        "- 'manufacturer': The brand or manufacturer name.\n"
        "- 'ref': The REF or catalog/article number "
        "(often labeled 'REF', 'Cat.', 'Art.', or 'No.').\n"
        "- 'ref_confidence': Your confidence in the extracted REF number. "
        "Use exactly one of: 'high' (clearly labeled as REF/Cat/Art), "
        "'medium' (plausible but ambiguous label), or 'low' (uncertain or inferred).\n"
        "- 'product_name': The commercial name or description of the product.\n"
        "- 'product_specs': A concise summary of key product specifications "
        "(e.g., size, material, quantity, sterility). Separate multiple specs with a semicolon.\n"
        "If a field is not found, use an empty string.\n"
        'Example: {"manufacturer": "Medline", "ref": "DYND74155", "ref_confidence": "high", '
        '"product_name": "Sterile Gloves", "product_specs": "Size 7.5; Latex; Sterile"}'
    )

    try:
        image_url = _image_as_data_url(image_path)
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ]
        data = _openai_retry(client, model, messages)
        return {
            "manufacturer": data.get("manufacturer", ""),
            "ref": data.get("ref", ""),
            "ref_confidence": data.get("ref_confidence", ""),
            "product_name": data.get("product_name", ""),
            "product_specs": data.get("product_specs", ""),
        }
    except Exception as exc:
        logger.error("OpenAI product analysis error for %s: %s", image_path, exc, exc_info=True)
        return {}


def decode_barcode_ai(
    image_path: str,
    provider: str,
    api_key: str,
    model: str,
) -> str:
    """Decode a GTIN using the selected AI provider."""
    if provider == "openai":
        return decode_barcode_openai(image_path, api_key, model=model)
    return decode_barcode_gemini(image_path, api_key, model=model)


def analyze_product_ai(
    image_path: str,
    provider: str,
    api_key: str,
    model: str,
) -> dict:
    """Analyze product metadata using the selected AI provider."""
    if provider == "openai":
        return analyze_product_openai(image_path, api_key, model=model)
    return analyze_product_gemini(image_path, api_key, model=model)
