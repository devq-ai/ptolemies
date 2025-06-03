#!/bin/bash
# Run the crawler to ingest all targets

# Base directory
PTOLEMIES_DIR="/Users/dionedge/devqai/ptolemies"

# Activate virtual environment
source "$PTOLEMIES_DIR/venv/bin/activate"

# Run the crawler
echo "Starting crawl of all targets from crawl_targets.json..."
python "$PTOLEMIES_DIR/crawl-targets.py"

echo "Crawl completed!"