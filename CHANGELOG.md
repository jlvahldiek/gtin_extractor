# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [1.0.0] - 2024-01-01

### Added
- **Package refactoring**: Reorganised monolithic `gtin_barcode_extractor.py` into a proper
  Python package under `gtin_extractor/` with logical modules:
  - `validation.py` – GTIN checksum validation
  - `readers.py` – pyzbar and zxing-cpp barcode reader wrappers
  - `gemini_integration.py` – Gemini AI barcode extraction and product analysis
  - `csv_export.py` – CSV output utilities
  - `config.py` – Configuration management (YAML + environment variables)
  - `logging_config.py` – Structured logging setup
  - `__main__.py` – CLI entry point (`python -m gtin_extractor`)
- **Unit tests** in `tests/` directory covering validation, readers, and config modules.
- **GitHub Actions CI/CD workflows**:
  - `tests.yml` – Run pytest with coverage on Python 3.9–3.12
  - `lint.yml` – flake8, black, and pylint checks
  - `type-check.yml` – mypy static type checking
- **`pyproject.toml`** – PEP 517/518 compliant package configuration with `[project]` metadata.
- **`setup.py`** – Compatibility shim for older tooling.
- **`MANIFEST.in`** – Non-Python file inclusion rules.
- **`requirements-dev.txt`** – Development dependencies (pytest, black, flake8, pylint, mypy).
- **`CONTRIBUTING.md`** – Development setup and contribution guidelines.
- **`CHANGELOG.md`** – Version history (this file).
- **GitHub issue templates** for bug reports and feature requests.
- **GitHub PR template**.
- **`Makefile`** – Common development tasks (`test`, `lint`, `format`, `typecheck`, `build`).
- **`.pre-commit-config.yaml`** – Pre-commit hooks for automatic linting.
- **`.editorconfig`** – Editor configuration for consistent formatting.
- **Structured logging** replacing all `print()` / `tqdm.write()` calls throughout the codebase.
- **Configuration management** via `config.yaml` and `GTIN_*` environment variables.

### Changed
- Replaced direct `print()` / `tqdm.write()` calls with Python `logging` module.
- CLI now accepts `--config`, `--log-level`, and `--log-file` options.
- README enhanced with installation via pip, package structure, and configuration sections.

### Deprecated
- `gtin_barcode_extractor.py` (top-level monolithic script) – functionality moved to the
  `gtin_extractor` package. The script is retained for backward compatibility.
