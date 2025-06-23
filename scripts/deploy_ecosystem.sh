#!/bin/bash
# Ptolemies Ecosystem Deployment Script
# Deploys and integrates Ptolemies components with DevQ.AI ecosystem

set -e

echo "🚀 Deploying Ptolemies to DevQ.AI Ecosystem"
echo "============================================="

# Configuration
PROJECT_ROOT="/Users/dionedge/devqai/ptolemies"
DEVQAI_ROOT="/Users/dionedge/devqai"

# Check prerequisites
echo "📋 Checking prerequisites..."

# Check Python version
python3 --version || { echo "❌ Python 3 not found"; exit 1; }

# Check Neo4j availability (optional)
if command -v neo4j &> /dev/null; then
    echo "✅ Neo4j CLI available"
else
    echo "⚠️  Neo4j CLI not found - manual database setup required"
fi

# Check required directories
if [ ! -d "$DEVQAI_ROOT" ]; then
    echo "❌ DevQ.AI root directory not found: $DEVQAI_ROOT"
    exit 1
fi

echo "✅ Prerequisites checked"

# Set up environment
echo "🔧 Setting up environment..."

# Export environment variables
export DEVQAI_ROOT="$DEVQAI_ROOT"
export PYTHONPATH="$DEVQAI_ROOT:$PROJECT_ROOT/src:$PYTHONPATH"
export LOGFIRE_PROJECT_NAME="ptolemies-knowledge-base"

# Core Ptolemies configuration
export CRAWLER_MAX_DEPTH=2
export CRAWLER_MAX_PAGES=250
export CRAWLER_DELAY_MS=1000

# Neo4j configuration (with defaults)
export NEO4J_URI="${NEO4J_URI:-bolt://localhost:7687}"
export NEO4J_USERNAME="${NEO4J_USERNAME:-neo4j}"
export NEO4J_PASSWORD="${NEO4J_PASSWORD:-password}"
export NEO4J_DATABASE="${NEO4J_DATABASE:-neo4j}"

# SurrealDB configuration (with defaults)
export SURREALDB_URL="${SURREALDB_URL:-ws://localhost:8000/rpc}"
export SURREALDB_USERNAME="${SURREALDB_USERNAME:-root}"
export SURREALDB_PASSWORD="${SURREALDB_PASSWORD:-root}"

echo "✅ Environment configured"

# Install dependencies
echo "📦 Installing dependencies..."
cd "$PROJECT_ROOT"

# Create and activate virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✅ Python dependencies installed in virtual environment"
else
    echo "⚠️  No requirements.txt found - manual dependency installation required"
fi

# Install Neo4j MCP server
echo "🔧 Installing Neo4j MCP server..."
cd "$PROJECT_ROOT/neo4j_mcp"
pip install -e .
echo "✅ Neo4j MCP server installed"

# Test installations
echo "🧪 Testing installations..."

cd "$PROJECT_ROOT"

# Test FastAPI application
echo "Testing FastAPI application..."
PYTHONPATH=src python -c "
import sys
sys.path.insert(0, 'src')
try:
    from main import app
    print('✅ FastAPI application loads successfully')
except Exception as e:
    print(f'❌ FastAPI application failed to load: {e}')
    sys.exit(1)
"

# Test Neo4j MCP server
echo "Testing Neo4j MCP server..."
cd neo4j_mcp
python -c "
try:
    from neo4j_mcp_server import Neo4jMCPServer
    print('✅ Neo4j MCP server loads successfully')
except Exception as e:
    print(f'❌ Neo4j MCP server failed to load: {e}')
    exit(1)
"

cd "$PROJECT_ROOT"

# Test Crawl4AI integration
echo "Testing Crawl4AI integration..."
PYTHONPATH=src python -c "
import sys
sys.path.insert(0, 'src')
try:
    from crawl4ai_integration import PtolemiesCrawler
    print('✅ Crawl4AI integration loads successfully')
except Exception as e:
    print(f'❌ Crawl4AI integration failed to load: {e}')
    exit(1)
"

echo "✅ All components tested successfully"

# Generate MCP configuration
echo "⚙️  Generating MCP configuration..."

CLAUDE_CONFIG_DIR="$HOME/.claude"
mkdir -p "$CLAUDE_CONFIG_DIR"

cat > "$CLAUDE_CONFIG_DIR/ptolemies_mcp_config.json" << EOF
{
  "mcpServers": {
    "ptolemies": {
      "command": "python3",
      "args": ["-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"],
      "cwd": "$PROJECT_ROOT/src",
      "env": {
        "PYTHONPATH": "$PROJECT_ROOT/src",
        "LOGFIRE_PROJECT_NAME": "ptolemies-knowledge-base",
        "CRAWLER_MAX_DEPTH": "2",
        "CRAWLER_MAX_PAGES": "250",
        "CRAWLER_DELAY_MS": "1000"
      }
    },
    "neo4j": {
      "command": "python3",
      "args": ["-m", "neo4j_mcp_server"],
      "cwd": "$PROJECT_ROOT/neo4j_mcp",
      "env": {
        "NEO4J_URI": "$NEO4J_URI",
        "NEO4J_USERNAME": "$NEO4J_USERNAME",
        "NEO4J_PASSWORD": "$NEO4J_PASSWORD",
        "NEO4J_DATABASE": "$NEO4J_DATABASE",
        "LOGFIRE_PROJECT_NAME": "ptolemies-neo4j"
      }
    }
  }
}
EOF

echo "✅ MCP configuration generated: $CLAUDE_CONFIG_DIR/ptolemies_mcp_config.json"

# Create service start scripts
echo "📜 Creating service scripts..."

# FastAPI service script
cat > "$PROJECT_ROOT/scripts/start_api.sh" << 'EOF'
#!/bin/bash
# Start Ptolemies FastAPI service

cd "$(dirname "$0")/.."
source venv/bin/activate
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"

echo "🚀 Starting Ptolemies FastAPI service..."
cd src
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
EOF

chmod +x "$PROJECT_ROOT/scripts/start_api.sh"

# Neo4j MCP service script
cat > "$PROJECT_ROOT/scripts/start_neo4j_mcp.sh" << 'EOF'
#!/bin/bash
# Start Neo4j MCP server

cd "$(dirname "$0")/.."
source venv/bin/activate
cd neo4j_mcp

echo "🚀 Starting Neo4j MCP server..."
python -m neo4j_mcp_server
EOF

chmod +x "$PROJECT_ROOT/scripts/start_neo4j_mcp.sh"

echo "✅ Service scripts created"

# Create health check script
cat > "$PROJECT_ROOT/scripts/health_check.sh" << 'EOF'
#!/bin/bash
# Health check for Ptolemies services

echo "🏥 Ptolemies Health Check"
echo "========================"

# Check FastAPI service
echo "Checking FastAPI service..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ FastAPI service is healthy"
else
    echo "❌ FastAPI service is not responding"
fi

# Check Neo4j connectivity
echo "Checking Neo4j connectivity..."
if python3 -c "
import neo4j
try:
    driver = neo4j.GraphDatabase.driver('$NEO4J_URI', auth=('$NEO4J_USERNAME', '$NEO4J_PASSWORD'))
    with driver.session() as session:
        session.run('RETURN 1')
    print('✅ Neo4j database is accessible')
    driver.close()
except Exception as e:
    print(f'❌ Neo4j database is not accessible: {e}')
"; then
    echo "Neo4j check completed"
fi

echo "Health check completed"
EOF

chmod +x "$PROJECT_ROOT/scripts/health_check.sh"

echo "✅ Health check script created"

# Summary
echo ""
echo "🎉 Ptolemies Ecosystem Deployment Complete!"
echo "==========================================="
echo ""
echo "📋 Deployment Summary:"
echo "  ✅ Environment configured"
echo "  ✅ Dependencies installed"
echo "  ✅ FastAPI application ready"
echo "  ✅ Neo4j MCP server ready"
echo "  ✅ Crawl4AI integration ready"
echo "  ✅ MCP configuration generated"
echo "  ✅ Service scripts created"
echo ""
echo "🚀 Quick Start:"
echo "  1. Start FastAPI: ./scripts/start_api.sh"
echo "  2. Start Neo4j MCP: ./scripts/start_neo4j_mcp.sh"
echo "  3. Health check: ./scripts/health_check.sh"
echo ""
echo "📖 Configuration:"
echo "  - MCP Config: $CLAUDE_CONFIG_DIR/ptolemies_mcp_config.json"
echo "  - Integration docs: deployment/ecosystem_integration.md"
echo ""
echo "🔗 Endpoints:"
echo "  - FastAPI: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - Health: http://localhost:8000/health"
echo ""
echo "✨ Ptolemies is ready for the DevQ.AI ecosystem!"
EOF