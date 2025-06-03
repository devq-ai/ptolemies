#!/bin/bash
# Enhanced Ptolemies MCP Server Startup Script
cd /Users/dionedge/devqai/ptolemies
source /Users/dionedge/devqai/ptolemies/venv/bin/activate
export PYTHONPATH=/Users/dionedge/devqai/ptolemies
python3 -m src.ptolemies.mcp.enhanced_ptolemies_mcp
