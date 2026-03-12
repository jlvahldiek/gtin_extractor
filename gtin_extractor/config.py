"""Configuration management for gtin_extractor.

Supports loading settings from:
- A ``config.yaml`` file (optional).
- Environment variables (with optional ``.env`` file loading via python-dotenv).
- Hard-coded default values.

Environment variables take precedence over ``config.yaml``, which takes precedence
over built-in defaults.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("gtin_extractor.config")

# ---------------------------------------------------------------------------
# Default values
# ---------------------------------------------------------------------------

DEFAULTS: dict[str, Any] = {
    "image_dir": "fotos",
    "csv_output": None,
    "gemini_api_key": None,
    "gemini_model": "gemini-2.0-flash",
    "max_retries": 5,
    "base_delay": 10.0,
    "log_level": "INFO",
    "log_file": None,
    "limit": None,
    "remove_duplicates": False,
}


@dataclass
class Config:
    """Centralised configuration container.

    Attributes:
        image_dir: Directory to scan for images.
        csv_output: Path for the CSV output file (``None`` = stdout/no file).
        gemini_api_key: Google Gemini API key.
        gemini_model: Gemini model identifier.
        max_retries: Maximum API retry attempts.
        base_delay: Base back-off delay in seconds.
        log_level: Logging level string (DEBUG, INFO, WARNING, ERROR).
        log_file: Optional path to write log output to a file.
        limit: Optional maximum number of images to process.
        remove_duplicates: When ``True``, deduplicate output rows by GTIN.
    """

    image_dir: str = DEFAULTS["image_dir"]
    csv_output: str | None = DEFAULTS["csv_output"]
    gemini_api_key: str | None = DEFAULTS["gemini_api_key"]
    gemini_model: str = DEFAULTS["gemini_model"]
    max_retries: int = DEFAULTS["max_retries"]
    base_delay: float = DEFAULTS["base_delay"]
    log_level: str = DEFAULTS["log_level"]
    log_file: str | None = DEFAULTS["log_file"]
    limit: int | None = DEFAULTS["limit"]
    remove_duplicates: bool = DEFAULTS["remove_duplicates"]

    # Extra keys from config file / env that are not declared above
    extra: dict[str, Any] = field(default_factory=dict)


def _load_dotenv(env_file: str | Path | None = None) -> None:
    """Attempt to load a ``.env`` file using *python-dotenv* (optional dependency).

    Args:
        env_file: Path to the ``.env`` file. Defaults to ``.env`` in the current
            working directory when ``None``.
    """
    try:
        from dotenv import load_dotenv  # type: ignore[import]

        path = Path(env_file) if env_file else Path(".env")
        if path.exists():
            load_dotenv(dotenv_path=path)
            logger.debug("Loaded environment variables from %s", path)
    except ImportError:
        logger.debug("python-dotenv not installed; skipping .env loading.")


def _load_yaml(config_file: str | Path) -> dict[str, Any]:
    """Load a YAML config file.

    Args:
        config_file: Path to the YAML file.

    Returns:
        Parsed content as a dict, or ``{}`` when the file does not exist or
        YAML is not installed.
    """
    path = Path(config_file)
    if not path.exists():
        return {}
    try:
        import yaml  # type: ignore[import]

        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        logger.debug("Loaded config from %s", path)
        return data
    except ImportError:
        logger.warning("PyYAML not installed; skipping %s.", path)
        return {}
    except Exception as exc:
        logger.warning("Failed to parse %s: %s", path, exc)
        return {}


def load_config(
    config_file: str | Path | None = None,
    env_file: str | Path | None = None,
) -> Config:
    """Build a :class:`Config` from files and environment variables.

    Loading order (later sources override earlier ones):
    1. Built-in :data:`DEFAULTS`.
    2. ``config.yaml`` / *config_file* (if present).
    3. Environment variables.

    Args:
        config_file: Path to a YAML config file. Defaults to ``config.yaml`` in
            the current working directory.
        env_file: Path to a ``.env`` file (requires *python-dotenv*).

    Returns:
        Populated :class:`Config` instance.
    """
    # Load .env first so its variables appear in os.environ
    _load_dotenv(env_file)

    # YAML values
    yaml_path = config_file if config_file is not None else "config.yaml"
    yaml_data = _load_yaml(yaml_path)

    def get(key: str, default: Any = None) -> Any:
        """Resolve a value from env → yaml → default."""
        env_key = f"GTIN_{key.upper()}"
        if env_key in os.environ:
            return os.environ[env_key]
        if key in yaml_data:
            return yaml_data[key]
        return default

    def get_int(key: str, default: Any = None) -> Any:
        val = get(key, default)
        if val is None:
            return None
        try:
            return int(val)
        except (TypeError, ValueError):
            return default

    def get_float(key: str, default: Any = None) -> Any:
        val = get(key, default)
        if val is None:
            return None
        try:
            return float(val)
        except (TypeError, ValueError):
            return default

    def get_bool(key: str, default: Any = None) -> bool:
        val = get(key, default)
        if val is None:
            return bool(default) if default is not None else False
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ("1", "true", "yes", "on")
        return bool(val)

    known_keys = set(DEFAULTS.keys())
    extra = {k: v for k, v in yaml_data.items() if k not in known_keys}

    return Config(
        image_dir=get("image_dir", DEFAULTS["image_dir"]),
        csv_output=get("csv_output", DEFAULTS["csv_output"]),
        gemini_api_key=get("gemini_api_key", DEFAULTS["gemini_api_key"]),
        gemini_model=get("gemini_model", DEFAULTS["gemini_model"]),
        max_retries=get_int("max_retries", DEFAULTS["max_retries"]),
        base_delay=get_float("base_delay", DEFAULTS["base_delay"]),
        log_level=get("log_level", DEFAULTS["log_level"]),
        log_file=get("log_file", DEFAULTS["log_file"]),
        limit=get_int("limit", DEFAULTS["limit"]),
        remove_duplicates=get_bool("remove_duplicates", DEFAULTS["remove_duplicates"]),
        extra=extra,
    )
