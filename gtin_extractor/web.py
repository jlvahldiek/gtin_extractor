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
import shutil
import tempfile
import threading
import uuid
from datetime import datetime, timedelta, timezone
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
            "Flask is required for the Web UI. " "Install it with: pip install gtin_extractor[web]"
        )

    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB upload limit

    # In-process task registry for async image processing
    _tasks: dict[str, dict] = {}
    _tasks_lock = threading.Lock()

    def _cleanup_tasks() -> None:
        """Remove tasks older than one hour to prevent unbounded memory growth."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        with _tasks_lock:
            expired = [
                tid
                for tid, task in _tasks.items()
                if datetime.fromisoformat(task.get("created_at", datetime.now(timezone.utc).isoformat()))
                < cutoff
            ]
            for tid in expired:
                del _tasks[tid]

    @app.route("/", methods=["GET"])
    def index() -> Any:
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
                        str(file_path), api_key=gemini_key or "", model=gemini_model
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

    @app.route("/api/models", methods=["POST"])
    def api_models() -> Response:
        """Return available Gemini models that support generateContent.

        Expects a JSON body with an optional ``key`` field (Gemini API key).
        Falls back to a static list when the key is absent or the API call fails.
        """
        _FALLBACK_MODELS = [
            "gemini-2.0-flash",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ]

        body = request.get_json(silent=True) or {}
        api_key = (body.get("key") or "").strip()
        if not api_key:
            return Response(
                json.dumps({"models": _FALLBACK_MODELS, "error": None}),
                mimetype="application/json",
            )

        try:
            from google import genai  # type: ignore[import]

            client = genai.Client(api_key=api_key)
            models: list[str] = []
            for model in client.models.list():
                name: str = model.name or ""
                # Strip the "models/" resource prefix used by the API
                short_name = name.removeprefix("models/")
                # Only include Gemini models that support text generation
                supported = model.supported_actions or []
                if "gemini" in short_name and "generateContent" in supported:
                    models.append(short_name)

            if not models:
                models = _FALLBACK_MODELS

            return Response(
                json.dumps({"models": models, "error": None}),
                mimetype="application/json",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to list Gemini models: %s", exc)
            return Response(
                json.dumps({"models": _FALLBACK_MODELS, "error": str(exc)}),
                mimetype="application/json",
            )

    @app.route("/api/process", methods=["POST"])
    def api_process() -> Response:
        """Start asynchronous image processing; return a task ID for polling."""
        gemini_key = request.form.get("gemini_key", "").strip() or None
        gemini_model = request.form.get("gemini_model", "gemini-2.0-flash").strip()
        remove_duplicates = request.form.get("remove_duplicates") == "on"
        uploaded_files = request.files.getlist("images")

        tmpdir = tempfile.mkdtemp()
        saved: list[Path] = []
        init_errors: list[str] = []

        for upload in uploaded_files:
            if not upload or not upload.filename:
                continue
            suffix = Path(upload.filename).suffix.lower()
            if suffix not in ALLOWED_EXTENSIONS:
                init_errors.append(f"Skipped {upload.filename}: unsupported file type.")
                continue
            dest = Path(tmpdir) / upload.filename
            upload.save(str(dest))
            saved.append(dest)

        _cleanup_tasks()

        task_id = str(uuid.uuid4())
        with _tasks_lock:
            _tasks[task_id] = {
                "status": "pending",
                "progress": 0,
                "total": len(saved),
                "current": "",
                "rows": [],
                "errors": list(init_errors),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

        def _run() -> None:
            from gtin_extractor.csv_export import build_row, deduplicate_rows
            from gtin_extractor.gemini_integration import analyze_product_gemini
            from gtin_extractor.readers import process_image

            task_errors: list[str] = list(init_errors)
            rows: list[dict] = []
            total = len(saved)
            try:
                with _tasks_lock:
                    _tasks[task_id]["status"] = "processing"

                for idx, file_path in enumerate(saved):
                    with _tasks_lock:
                        _tasks[task_id]["current"] = file_path.name
                        _tasks[task_id]["progress"] = int(idx / total * 100) if total else 100

                    try:
                        gtin, method = process_image(
                            str(file_path),
                            gemini_key=gemini_key,
                            gemini_model=gemini_model,
                        )
                        product_info = analyze_product_gemini(
                            str(file_path), api_key=gemini_key or "", model=gemini_model
                        )
                        rows.append(build_row(file_path.name, gtin, method, product_info))
                    except Exception as exc:  # noqa: BLE001
                        logger.exception("Error processing %s", file_path.name)
                        task_errors.append(f"Error processing {file_path.name}: {exc}")

                    with _tasks_lock:
                        _tasks[task_id]["rows"] = list(rows)
                        _tasks[task_id]["errors"] = list(task_errors)

                if remove_duplicates:
                    before = len(rows)
                    rows = deduplicate_rows(rows)
                    removed = before - len(rows)
                    if removed:
                        logger.info("Removed %d duplicate GTIN row(s).", removed)

                with _tasks_lock:
                    _tasks[task_id].update(
                        {
                            "status": "complete",
                            "progress": 100,
                            "current": "",
                            "rows": rows,
                            "errors": task_errors,
                        }
                    )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Task %s failed unexpectedly", task_id)
                with _tasks_lock:
                    _tasks[task_id].update(
                        {
                            "status": "error",
                            "errors": task_errors + [str(exc)],
                        }
                    )
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

        return Response(json.dumps({"task_id": task_id}), mimetype="application/json")

    @app.route("/api/progress/<task_id>", methods=["GET"])
    def api_progress(task_id: str) -> Response:
        """Return the current status and partial results for a processing task."""
        with _tasks_lock:
            task = _tasks.get(task_id)

        if task is None:
            return Response(
                json.dumps({"error": "Task not found"}),
                status=404,
                mimetype="application/json",
            )

        return Response(
            json.dumps(
                {
                    "status": task["status"],
                    "progress": task["progress"],
                    "current": task["current"],
                    "total": task["total"],
                    "rows": task["rows"],
                    "errors": task["errors"],
                }
            ),
            mimetype="application/json",
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
        logger.error("Flask is not installed. Install it with: pip install gtin_extractor[web]")
        raise SystemExit(1)

    app = _build_app()
    logger.info("Starting GTIN Extractor Web UI on http://%s:%d", args.host, args.port)
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
