#!/bin/bash
# Ptolemies Setup Script

echo "🚀 Setting up Ptolemies Knowledge Base System..."
echo "=============================================="

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Function to print status
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check Python version
echo "1. Checking Python version..."
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then 
    print_status "Python $PYTHON_VERSION is installed (>= $REQUIRED_VERSION required)"
else
    print_error "Python $PYTHON_VERSION is too old. Please install Python >= $REQUIRED_VERSION"
    exit 1
fi

# Create virtual environment
echo ""
echo "2. Setting up virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_status "Virtual environment created"
else
    print_status "Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate
print_status "Virtual environment activated"

# Upgrade pip
echo ""
echo "3. Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
print_status "pip upgraded"

# Install Python dependencies
echo ""
echo "4. Installing Python dependencies..."
pip install -r requirements.txt
if [ $? -eq 0 ]; then
    print_status "Python dependencies installed"
else
    print_error "Failed to install Python dependencies"
    exit 1
fi

# Install Neo4j MCP dependencies
echo ""
echo "5. Installing Neo4j MCP dependencies..."
if [ -f "neo4j_mcp/neo4j_requirements.txt" ]; then
    pip install -r neo4j_mcp/neo4j_requirements.txt
    print_status "Neo4j MCP dependencies installed"
else
    print_warning "Neo4j requirements file not found"
fi

# Check for .env file
echo ""
echo "6. Checking environment configuration..."
if [ -f ".env" ]; then
    print_status ".env file found"
    # Source the .env file
    export $(grep -v '^#' .env | xargs)
else
    print_warning ".env file not found. Creating from template..."
    cp .env.example .env
    print_warning "Please edit .env file with your configuration"
fi

# Create necessary directories
echo ""
echo "7. Creating directory structure..."
mkdir -p .taskmaster/docs
mkdir -p .taskmaster/tasks
mkdir -p logs
mkdir -p data/crawled
mkdir -p data/embeddings
mkdir -p data/cache
print_status "Directory structure created"

# Install Node.js dependencies for MCP tools
echo ""
echo "8. Installing Node.js MCP tools..."
if command -v npm &> /dev/null; then
    # Install global MCP tools
    npm list -g @modelcontextprotocol/server-filesystem > /dev/null 2>&1 || npm install -g @modelcontextprotocol/server-filesystem
    npm list -g @modelcontextprotocol/server-fetch > /dev/null 2>&1 || npm install -g @modelcontextprotocol/server-fetch
    npm list -g @modelcontextprotocol/server-sequentialthinking > /dev/null 2>&1 || npm install -g @modelcontextprotocol/server-sequentialthinking
    print_status "MCP tools installed"
else
    print_error "npm not found. Please install Node.js"
fi

# Database setup hints
echo ""
echo "9. Database Setup Instructions:"
echo "   Neo4j:"
echo "     - Install: brew install neo4j"
echo "     - Start: neo4j start"
echo "     - Access: http://localhost:7474"
echo "     - Default credentials: neo4j/neo4j (change on first login)"
echo ""
echo "   SurrealDB:"
echo "     - Install: brew install surrealdb/tap/surreal"
echo "     - Start: surreal start --log debug --user root --pass root memory"
echo "     - Access: http://localhost:8000"

# Summary
echo ""
echo "=============================================="
echo "Setup Summary:"
echo ""

# Check key dependencies
python3 -c "import fastapi" 2>/dev/null && print_status "FastAPI installed" || print_error "FastAPI not installed"
python3 -c "import pytest" 2>/dev/null && print_status "PyTest installed" || print_error "PyTest not installed"
python3 -c "import logfire" 2>/dev/null && print_status "Logfire installed" || print_error "Logfire not installed"
python3 -c "import neo4j" 2>/dev/null && print_status "Neo4j driver installed" || print_error "Neo4j driver not installed"
python3 -c "import redis" 2>/dev/null && print_status "Redis driver installed" || print_error "Redis driver not installed"

echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys and configuration"
echo "2. Start Neo4j and SurrealDB services"
echo "3. Run ./verify-mcp-tools.sh to verify all tools"
echo "4. Run tests: pytest tests/"
echo ""
print_status "Setup complete! 🎉"