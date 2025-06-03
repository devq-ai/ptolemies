#!/bin/bash
"""
Setup script for Graphiti integration environment.

This script creates a separate virtual environment for Graphiti operations
to resolve the pydantic version conflict between SurrealDB (<2.0) and Graphiti (>=2.8).

Usage:
    ./setup_graphiti_env.sh

Requirements:
    - Python 3.10+
    - Neo4j running on localhost:7687
    - OpenAI API key in environment
"""

set -e  # Exit on any error

echo "🚀 Setting up Graphiti integration environment for Ptolemies..."

# Check Python version
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "📋 Python version: $python_version"

if [[ $(echo "$python_version < 3.10" | bc -l) -eq 1 ]]; then
    echo "❌ Python 3.10+ is required for Graphiti. Current version: $python_version"
    exit 1
fi

# Create Graphiti virtual environment
echo "📦 Creating Graphiti virtual environment..."
cd /Users/dionedge/devqai/ptolemies

if [ -d "venv_graphiti" ]; then
    echo "⚠️  venv_graphiti already exists. Removing..."
    rm -rf venv_graphiti
fi

python3 -m venv venv_graphiti
source venv_graphiti/bin/activate

echo "✅ Graphiti virtual environment created and activated"

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install Graphiti with all provider support
echo "📦 Installing Graphiti with LLM provider support..."
pip install 'graphiti-core[anthropic,groq]'

# Install additional dependencies for visualization
echo "📦 Installing visualization dependencies..."
pip install fastapi[all] uvicorn websockets

# Install Neo4j Python driver explicitly
echo "📦 Installing Neo4j driver..."
pip install neo4j>=5.23.0

# Install other required packages
echo "📦 Installing additional dependencies..."
pip install python-dotenv pydantic>=2.8.2 httpx asyncio-mqtt

# Verify Graphiti installation
echo "🔍 Verifying Graphiti installation..."
python3 -c "
import graphiti
import neo4j
import pydantic
print(f'✅ Graphiti version: {graphiti.__version__}')
print(f'✅ Neo4j driver version: {neo4j.__version__}')
print(f'✅ Pydantic version: {pydantic.__version__}')
"

# Create requirements file for Graphiti environment
echo "📄 Creating requirements file..."
pip freeze > requirements_graphiti.txt

echo "✅ Graphiti environment setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Activate environment: source venv_graphiti/bin/activate"
echo "2. Configure environment variables in .env"
echo "3. Start Neo4j: brew services start neo4j"
echo "4. Run setup verification: python3 verify_graphiti_setup.py"
echo ""
echo "🔧 Environment locations:"
echo "   - Graphiti venv: /Users/dionedge/devqai/ptolemies/venv_graphiti"
echo "   - Main venv:     /Users/dionedge/devqai/ptolemies/venv"
echo "   - Requirements:  /Users/dionedge/devqai/ptolemies/requirements_graphiti.txt"