.PHONY: help test lint format typecheck build clean all

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

all: lint typecheck test ## Run lint, type-check, and tests

test: ## Run tests with coverage
	pytest tests/ --cov=gtin_extractor --cov-report=term-missing -v

lint: ## Run flake8, pylint, and black check
	flake8 gtin_extractor/ tests/ --max-line-length=100
	pylint gtin_extractor/ --fail-under=7.0
	black --check --diff gtin_extractor/ tests/

format: ## Auto-format code with black
	black gtin_extractor/ tests/

typecheck: ## Run mypy type checking
	mypy gtin_extractor/ --ignore-missing-imports

build: ## Build distribution packages
	python -m build

clean: ## Remove build artifacts and caches
	rm -rf dist/ build/ *.egg-info/ .pytest_cache/ htmlcov/ coverage.xml .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
