"""Platform-independent Web UI for gtin_extractor.

Start with::

    python -m gtin_extractor.web
    # or
    gtin-web

Then open http://localhost:5000 in your browser.

Requires Flask (``pip install gtin_extractor[web]``).
"""

from __future__ import annotations

import csv
import io
import json
import logging
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger("gtin_extractor.web")

try:
    from flask import Flask, Response, render_template, request, send_file  # type: ignore[import]

    _FLASK_AVAILABLE = True
except ImportError:
    _FLASK_AVAILABLE = False

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif"}


def _build_app() -> Any:
    """Create and configure the Flask application."""
    if not _FLASK_AVAILABLE:
        raise RuntimeError(
            "Flask is required for the Web UI. "
            "Install it with: pip install gtin_extractor[web]"
        )

    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB upload limit

    @app.route("/", methods=["GET"])
    def index() -> str:
        return render_template("index.html")

    @app.route("/process", methods=["POST"])
    def process() -> Any:
        from gtin_extractor.csv_export import build_row, deduplicate_rows
        from gtin_extractor.gemini_integration import analyze_product_gemini
        from gtin_extractor.readers import process_image

        gemini_key = request.form.get("gemini_key", "").strip() or None
        gemini_model = request.form.get("gemini_model", "gemini-2.0-flash").strip()
        remove_duplicates = request.form.get("remove_duplicates") == "on"
        uploaded_files = request.files.getlist("images")

        rows: list[dict] = []
        errors: list[str] = []

        with tempfile.TemporaryDirectory() as tmpdir:
            saved: list[Path] = []
            for upload in uploaded_files:
                if not upload or not upload.filename:
                    continue
                suffix = Path(upload.filename).suffix.lower()
                if suffix not in ALLOWED_EXTENSIONS:
                    errors.append(f"Skipped {upload.filename}: unsupported file type.")
                    continue
                dest = Path(tmpdir) / upload.filename
                upload.save(str(dest))
                saved.append(dest)

            for file_path in saved:
                try:
                    gtin, method = process_image(
                        str(file_path),
                        gemini_key=gemini_key,
                        gemini_model=gemini_model,
                    )
                    product_info = analyze_product_gemini(
                        str(file_path), api_key=gemini_key, model=gemini_model
                    )
                    rows.append(build_row(file_path.name, gtin, method, product_info))
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Error processing %s", file_path.name)
                    errors.append(f"Error processing {file_path.name}: {exc}")

        if remove_duplicates:
            before = len(rows)
            rows = deduplicate_rows(rows)
            removed = before - len(rows)
            if removed:
                logger.info("Removed %d duplicate GTIN row(s).", removed)

        return render_template(
            "results.html",
            rows=rows,
            errors=errors,
            remove_duplicates=remove_duplicates,
        )

    @app.route("/download", methods=["POST"])
    def download() -> Response:
        """Generate and return the results as a downloadable CSV."""
        from gtin_extractor.csv_export import FIELDNAMES

        # Row data is posted as hidden form fields
        rows_json = request.form.get("rows_json", "[]")
        try:
            rows: list[dict] = json.loads(rows_json)
        except (ValueError, TypeError):
            rows = []

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

        csv_bytes = io.BytesIO(output.getvalue().encode("utf-8"))
        return send_file(
            csv_bytes,
            mimetype="text/csv",
            as_attachment=True,
            download_name="gtin_results.csv",
        )

    return app


def main() -> None:
    """Entry point for the gtin-web command."""
    import argparse

    from gtin_extractor.logging_config import setup_logging

    parser = argparse.ArgumentParser(
        prog="gtin-web",
        description="Start the GTIN Extractor Web UI.",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5000, help="Port to listen on (default: 5000)")
    parser.add_argument("--debug", action="store_true", help="Enable Flask debug mode")
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging verbosity",
    )
    args = parser.parse_args()

    setup_logging(log_level=args.log_level)

    if not _FLASK_AVAILABLE:
        logger.error(
            "Flask is not installed. Install it with: pip install gtin_extractor[web]"
        )
        raise SystemExit(1)

    app = _build_app()
    logger.info("Starting GTIN Extractor Web UI on http://%s:%d", args.host, args.port)
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
