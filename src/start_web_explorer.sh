#!/bin/bash
# Ptolemies Knowledge Graph Web Explorer Startup Script

echo "🌐 Starting Ptolemies Knowledge Graph Explorer"
echo "=============================================="

# Check if we're in the right directory
if [ ! -f "web_graph_explorer.py" ]; then
    echo "❌ Error: Please run this script from the ptolemies directory"
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Set Python path
export PYTHONPATH=$(pwd)

# Load environment variables (safer method)
if [ -f ".env" ]; then
    echo "📋 Loading environment variables..."
    set -a
    source .env
    set +a
fi

echo "🚀 Starting services..."
echo ""
echo "Available interfaces:"
echo "  🌐 Ptolemies Graph Explorer: http://localhost:8080"
echo "  📊 Neo4j Browser:           http://localhost:7474"
echo "  ⚙️ Graphiti Service:        http://localhost:8001"
echo ""
echo "🔍 Use Ctrl+C to stop the server"
echo ""

# Start the web explorer
python3 web_graph_explorer.py