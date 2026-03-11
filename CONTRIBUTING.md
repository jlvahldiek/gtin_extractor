# Contributing to gtin_extractor

Thank you for your interest in contributing! This guide will help you get started.

---

## Development Setup

### Prerequisites

- Python 3.9 or newer
- System dependencies:
  - **macOS**: `brew install zbar`
  - **Linux**: `sudo apt-get install libzbar0`

### Clone and install

```bash
git clone https://github.com/jlvahldiek/gtin_extractor.git
cd gtin_extractor

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install runtime + development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install the package in editable mode
pip install -e .
```

### Running tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=gtin_extractor --cov-report=term-missing

# Run a specific test file
pytest tests/test_validation.py -v
```

### Linting and formatting

```bash
# Check formatting (black)
black --check gtin_extractor/ tests/

# Auto-format
black gtin_extractor/ tests/

# Run flake8
flake8 gtin_extractor/ tests/ --max-line-length=100

# Run pylint
pylint gtin_extractor/

# Run mypy type checks
mypy gtin_extractor/ --ignore-missing-imports
```

Using the `Makefile`:

```bash
make test      # run tests
make lint      # run all linters
make format    # auto-format with black
make typecheck # run mypy
make all       # lint + typecheck + test
```

---

## Package Structure

```
gtin_extractor/          ← Python package
├── __init__.py          ← Public API, version
├── __main__.py          ← CLI entry point (python -m gtin_extractor)
├── validation.py        ← GTIN checksum validation
├── readers.py           ← pyzbar / zxing-cpp barcode readers
├── gemini_integration.py← Gemini AI barcode extraction and product analysis
├── csv_export.py        ← CSV writing utilities
├── config.py            ← Configuration loading (YAML + env vars)
└── logging_config.py    ← Logging setup
tests/
├── conftest.py          ← Shared fixtures
├── test_validation.py
├── test_readers.py
└── test_config.py
```

---

## Contribution Guidelines

1. **Fork** the repository and create a feature branch from `main`.
2. Write tests for any new functionality.
3. Ensure `pytest` passes and coverage stays above 70 %.
4. Run `black` and `flake8` before submitting your PR.
5. Follow the existing code style and docstring conventions (Google-style).
6. Update `CHANGELOG.md` under the `[Unreleased]` section.

### Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/) where possible:

```
feat: add parallel processing via concurrent.futures
fix: handle corrupt image files in process_image
docs: update CONTRIBUTING with new make targets
test: add edge-case tests for GS1 delimiters
```

---

## Reporting Issues

Please use the GitHub issue templates:
- **Bug report**: include the command you ran, Python version, OS, and full error traceback.
- **Feature request**: describe the use-case and expected behaviour.

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
