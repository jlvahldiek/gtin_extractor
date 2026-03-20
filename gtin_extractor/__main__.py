"""CLI entry point for gtin_extractor.

Run with::

    python -m gtin_extractor [options]
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from tqdm import tqdm  # type: ignore[import]

from gtin_extractor.config import load_config
from gtin_extractor.csv_export import CSVWriter, build_row, deduplicate_rows
from gtin_extractor.gemini_integration import analyze_product_ai
from gtin_extractor.logging_config import setup_logging
from gtin_extractor.readers import process_image


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="gtin_extractor",
        description="Extract GTINs from a directory of product label photos.",
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=None,
        help="Directory containing images (default: value from config / 'fotos')",
    )
    parser.add_argument("--csv", help="Path to output CSV file", default=None)
    parser.add_argument(
        "--ai-provider",
        choices=["gemini", "openai"],
        default=None,
        help="AI provider for fallback + metadata extraction",
    )
    parser.add_argument("--gemini-key", help="Google Gemini API Key", default=None)
    parser.add_argument("--gemini-model", help="Gemini model to use", default=None)
    parser.add_argument("--openai-key", help="OpenAI API Key", default=None)
    parser.add_argument("--openai-model", help="OpenAI model to use", default=None)
    parser.add_argument(
        "--limit", type=int, help="Limit the number of files to process", default=None
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=None,
        help="Logging verbosity",
    )
    parser.add_argument("--log-file", help="Path to log file", default=None)
    parser.add_argument("--config", help="Path to config.yaml file", default=None)
    parser.add_argument(
        "--remove-duplicates",
        action="store_true",
        default=None,
        help="Remove rows with duplicate GTINs from the CSV output (keeps first occurrence)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the gtin_extractor CLI.

    Args:
        argv: Optional list of command-line arguments (defaults to sys.argv).

    Returns:
        Exit code (0 = success, 1 = error).
    """
    args = _parse_args(argv)

    # Load configuration (file + env), then apply CLI overrides
    cfg = load_config(config_file=args.config)

    if args.directory is not None:
        cfg.image_dir = args.directory
    if args.csv is not None:
        cfg.csv_output = args.csv
    if args.ai_provider is not None:
        cfg.ai_provider = args.ai_provider
    if args.gemini_key is not None:
        cfg.gemini_api_key = args.gemini_key
    if args.gemini_model is not None:
        cfg.gemini_model = args.gemini_model
    if args.openai_key is not None:
        cfg.openai_api_key = args.openai_key
    if args.openai_model is not None:
        cfg.openai_model = args.openai_model
    if args.limit is not None:
        cfg.limit = args.limit
    if args.log_level is not None:
        cfg.log_level = args.log_level
    if args.log_file is not None:
        cfg.log_file = args.log_file
    if args.remove_duplicates:
        cfg.remove_duplicates = True

    # Set up logging
    setup_logging(log_level=cfg.log_level, log_file=cfg.log_file)
    log = logging.getLogger("gtin_extractor")

    dir_path = Path(cfg.image_dir)
    if not dir_path.exists() or not dir_path.is_dir():
        log.error("Directory not found: %s", dir_path)
        return 1

    log.info("Processing images in %s …", dir_path)

    provider = (cfg.ai_provider or "gemini").strip().lower()
    if provider == "openai":
        ai_key = cfg.openai_api_key
        ai_model = cfg.openai_model
    else:
        provider = "gemini"
        ai_key = cfg.gemini_api_key
        ai_model = cfg.gemini_model

    valid_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif"}
    files_to_process = [
        f for f in dir_path.iterdir() if f.is_file() and f.suffix.lower() in valid_exts
    ]

    if cfg.limit:
        files_to_process = files_to_process[: cfg.limit]
        log.info("Limiting processing to the first %d files.", cfg.limit)

    def _iter_results():
        for file_path in tqdm(files_to_process, desc="Scanning images"):
            gtin, method = process_image(
                str(file_path),
                ai_provider=provider,
                ai_key=ai_key,
                ai_model=ai_model,
            )
            product_info = analyze_product_ai(
                str(file_path), provider=provider, api_key=ai_key or "", model=ai_model
            )

            if gtin:
                log.info("Found GTIN: %s in %s (via %s)", gtin, file_path.name, method)
            else:
                log.info("No valid GTIN found in %s", file_path.name)

            yield build_row(file_path.name, gtin, method, product_info)

    if cfg.csv_output:
        all_rows = list(_iter_results())
        if cfg.remove_duplicates:
            before = len(all_rows)
            all_rows = deduplicate_rows(all_rows)
            removed = before - len(all_rows)
            if removed:
                log.info("Removed %d duplicate GTIN row(s).", removed)
        with CSVWriter(cfg.csv_output) as writer:
            for row in all_rows:
                writer.writerow(row)
        log.info("Results exported to %s", cfg.csv_output)
    else:
        for _row in _iter_results():
            pass  # results already logged above

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
