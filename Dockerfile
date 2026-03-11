# syntax=docker/dockerfile:1
# ─────────────────────────────────────────────────────────────────────────────
# GTIN Extractor – Docker image
#
# Supports both CLI and Web-UI modes.
#
# Build:
#   docker build -t gtin_extractor .
#
# Run CLI:
#   docker run --rm -v /path/to/images:/data gtin_extractor \
#       python -m gtin_extractor /data --csv /data/results.csv
#
# Run Web UI (see also docker-compose.yml):
#   docker run --rm -p 5000:5000 gtin_extractor gtin-web
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.12-slim

WORKDIR /app

# Copy dependency manifests first for better layer caching
COPY requirements.txt pyproject.toml setup.py ./
COPY gtin_extractor/ ./gtin_extractor/

# Install system runtime deps (libzbar0, libgl1) plus temporary C++ build tools
# needed to compile zxing-cpp from source on platforms without a pre-built wheel
# (e.g. arm64).  Build tools are purged after the pip install to keep the image slim.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libzbar0 \
        libgl1 \
        cmake \
        make \
        g++ \
    && pip install --no-cache-dir \
        -r requirements.txt \
        "Flask>=3.0.0,<4" \
        PyYAML>=6.0 \
        python-dotenv>=1.0.0 \
    && pip install --no-cache-dir -e . \
    && apt-get purge -y --auto-remove cmake make g++ \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for security
RUN useradd -m -u 1000 gtin
USER gtin

# Default data directory; mount your images here
VOLUME ["/data"]

# Expose the Web UI port
EXPOSE 5000

# Default command: start the Web UI
CMD ["gtin-web", "--host", "0.0.0.0", "--port", "5000"]
