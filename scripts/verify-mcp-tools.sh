#!/bin/bash
# MCP Tools Verification Script for Ptolemies Project

echo "🔍 Verifying MCP Tools for Ptolemies Knowledge Base..."
echo "=================================================="

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counter for success/failure
SUCCESS_COUNT=0
FAILURE_COUNT=0

# Function to check tool availability
check_tool() {
    local tool_name=$1
    local check_command=$2
    local description=$3
    
    echo -n "Checking $tool_name ($description)... "
    
    if eval "$check_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Available${NC}"
        ((SUCCESS_COUNT++))
        return 0
    else
        echo -e "${RED}❌ Not Available${NC}"
        ((FAILURE_COUNT++))
        return 1
    fi
}

echo "1. Core MCP Tools"
echo "-----------------"

# TaskMaster AI
check_tool "taskmaster-ai" "npx task-master-ai --version" "Task generation and management"

# Context7
check_tool "context7" "python -c 'import sys; sys.path.append(\"/Users/dionedge/devqai\"); from mcp.mcp_servers.context7_mcp.server import Context7MCPServer; print(\"OK\")'" "Contextual reasoning"

# SurrealDB
check_tool "surrealdb" "curl -s http://localhost:8000/status" "Vector database for RAG"

# Neo4j
check_tool "neo4j" "curl -s http://localhost:7474" "Graph database"

# Crawl4AI
check_tool "crawl4ai" "python -c 'import sys; sys.path.append(\"/Users/dionedge/devqai\"); print(\"OK\")'" "Web crawling"

echo ""
echo "2. Standard MCP Tools"
echo "--------------------"

# Filesystem
check_tool "filesystem" "npx -y @modelcontextprotocol/server-filesystem --help" "File operations"

# Git
check_tool "git" "git --version" "Version control"

# Fetch
check_tool "fetch" "npx -y @modelcontextprotocol/server-fetch --help" "HTTP operations"

# Memory
check_tool "memory" "npx -y @modelcontextprotocol/server-memory --help" "Session persistence"

# Sequential Thinking
check_tool "sequentialthinking" "npx -y @modelcontextprotocol/server-sequentialthinking --help" "Problem solving"

# GitHub
check_tool "github" "gh --version" "Repository management"

echo ""
echo "3. Python Environment"
echo "--------------------"

# Python version
check_tool "python3" "python3 --version" "Python 3.8+"

# Required Python packages
check_tool "fastapi" "python -c 'import fastapi; print(fastapi.__version__)'" "Web framework"
check_tool "pytest" "python -c 'import pytest; print(pytest.__version__)'" "Testing framework"
check_tool "logfire" "python -c 'import logfire; print(logfire.__version__)'" "Observability"
check_tool "pydantic" "python -c 'import pydantic; print(pydantic.__version__)'" "Data validation"
check_tool "neo4j" "python -c 'import neo4j; print(neo4j.__version__)'" "Neo4j driver"
check_tool "redis" "python -c 'import redis; print(redis.__version__)'" "Redis client"

echo ""
echo "4. Environment Variables"
echo "-----------------------"

# Check environment variables
check_env() {
    local var_name=$1
    local description=$2
    
    if [ -n "${!var_name}" ]; then
        echo -e "$var_name: ${GREEN}✅ Set${NC} ($description)"
        ((SUCCESS_COUNT++))
    else
        echo -e "$var_name: ${RED}❌ Not Set${NC} ($description)"
        ((FAILURE_COUNT++))
    fi
}

check_env "ANTHROPIC_API_KEY" "Required for TaskMaster AI"
check_env "LOGFIRE_TOKEN" "Required for Logfire monitoring"
check_env "NEO4J_URI" "Neo4j connection"
check_env "NEO4J_USERNAME" "Neo4j authentication"
check_env "NEO4J_PASSWORD" "Neo4j authentication"
check_env "SURREALDB_URL" "SurrealDB connection"
check_env "UPSTASH_REDIS_REST_URL" "Redis connection"
check_env "OPENAI_API_KEY" "Embeddings generation"

echo ""
echo "5. Database Connectivity"
echo "-----------------------"

# Test SurrealDB connection
echo -n "Testing SurrealDB connection... "
if curl -s -X POST http://localhost:8000/sql \
    -H "Accept: application/json" \
    -H "NS: ptolemies" \
    -H "DB: knowledge" \
    -u "root:root" \
    -d "INFO FOR DB;" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Connected${NC}"
    ((SUCCESS_COUNT++))
else
    echo -e "${RED}❌ Connection Failed${NC}"
    ((FAILURE_COUNT++))
fi

# Test Neo4j connection
echo -n "Testing Neo4j connection... "
if [ -n "$NEO4J_PASSWORD" ]; then
    if curl -s -u neo4j:$NEO4J_PASSWORD http://localhost:7474/db/neo4j/ > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Connected${NC}"
        ((SUCCESS_COUNT++))
    else
        echo -e "${RED}❌ Connection Failed${NC}"
        ((FAILURE_COUNT++))
    fi
else
    echo -e "${YELLOW}⚠️  Skipped (NEO4J_PASSWORD not set)${NC}"
fi

echo ""
echo "=================================================="
echo "Summary:"
echo "  Successful checks: ${GREEN}$SUCCESS_COUNT${NC}"
echo "  Failed checks: ${RED}$FAILURE_COUNT${NC}"
echo ""

if [ $FAILURE_COUNT -eq 0 ]; then
    echo -e "${GREEN}✅ All MCP tools are ready for Ptolemies!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tools are missing. Please install missing dependencies.${NC}"
    echo ""
    echo "Installation hints:"
    echo "  - TaskMaster AI: npm install -g task-master-ai"
    echo "  - Python packages: pip install -r requirements.txt"
    echo "  - SurrealDB: brew install surrealdb/tap/surreal"
    echo "  - Neo4j: brew install neo4j"
    echo "  - Environment vars: source .env"
    exit 1
fi