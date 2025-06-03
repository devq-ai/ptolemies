#!/bin/bash
# Non-interactive script to list crawl targets

# Base directory
PTOLEMIES_DIR="/Users/dionedge/devqai/ptolemies"

echo "===== Ptolemies Knowledge Base Crawler ====="
echo ""
echo "Listing crawl targets..."
echo ""

cd "$PTOLEMIES_DIR" && python -m integrations.crawl4ai.cli list-targets