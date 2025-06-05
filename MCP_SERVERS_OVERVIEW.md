# MCP Servers Overview for DevQ.ai

This document provides a comprehensive overview of all Model Context Protocol (MCP) servers integrated with the DevQ.ai project.

## Available MCP Servers

### 1. Context7 MCP Server
**Path**: `./mcp/mcp-servers/context7-mcp`
**Purpose**: Advanced contextual reasoning with 7-hop depth analysis
**Technology**: Python-based local server
**Database**: Redis (Upstash)

**Configuration**:
```yaml
context7:
  command: python
  args: ["-m", "context7_mcp.server"]
  cwd: "./devqai/mcp/mcp-servers/context7-mcp"
  env:
    UPSTASH_REDIS_REST_URL: "${UPSTASH_REDIS_REST_URL}"
    UPSTASH_REDIS_REST_TOKEN: "${UPSTASH_REDIS_REST_TOKEN}"
```

**Features**:
- Multi-hop contextual reasoning
- Redis-backed persistent memory
- Complex query processing
- Relationship mapping

**Terminal Commands**:
```bash
start-context7    # Start the server
```

### 2. Crawl4AI MCP Server
**Path**: `./mcp/mcp-servers/crawl4ai-mcp`
**Purpose**: Web scraping and content extraction
**Technology**: Python-based local server

**Configuration**:
```yaml
crawl4ai:
  command: python
  args: ["-m", "crawl4ai_mcp.server"]
  cwd: "./devqai/mcp/mcp-servers/crawl4ai-mcp"
```

**Features**:
- Intelligent web scraping
- Content extraction and parsing
- Document processing
- Research automation

**Terminal Commands**:
```bash
start-crawl4ai    # Start the server
```

### 3. Ptolemies Knowledge Base MCP Server
**Path**: `./ptolemies`
**Purpose**: Custom knowledge base integration with vector search
**Technology**: Python-based with SurrealDB
**Database**: SurrealDB

**Configuration**:
```yaml
ptolemies:
  command: python
  args: ["-m", "ptolemies.mcp.ptolemies_mcp"]
  cwd: "./devqai/ptolemies"
```

**Features**:
- Vector search capabilities
- Knowledge graph operations
- Domain-specific knowledge integration
- Persistent knowledge storage

**Terminal Commands**:
```bash
start-ptolemies   # Start the MCP server
setup-db          # Initialize database
verify-db         # Verify database setup
```

**Database Setup**:
```bash
cd ptolemies
./setup-database.sh
python verify-database.py
```

### 4. Dart AI MCP Server
**Purpose**: Smart code assistance and development intelligence
**Technology**: NPX-based external server
**Provider**: Dart AI

**Configuration**:
```yaml
dart:
  command: npx
  args: ["-y", "dart-mcp-server"]
  env:
    DART_TOKEN: "${DART_TOKEN}"
```

**Features**:
- Intelligent code analysis
- Development assistance
- Code quality insights
- Architecture recommendations

**Terminal Commands**:
```bash
start-dart        # Start the server
dart-test         # Test configuration
```

### 5. NPX-Based Core Servers

#### Filesystem Server
```yaml
filesystem:
  command: npx
  args: ["-y", "@modelcontextprotocol/server-filesystem", "."]
```
**Features**: File read/write operations for current project directory

#### Git Server
```yaml
git:
  command: npx
  args: ["-y", "@modelcontextprotocol/server-git"]
```
**Features**: Version control operations, commits, branch management

#### Fetch Server
```yaml
fetch:
  command: npx
  args: ["-y", "@modelcontextprotocol/server-fetch"]
```
**Features**: API calls and external resource access

#### Memory Server
```yaml
memory:
  command: npx
  args: ["-y", "@modelcontextprotocol/server-memory"]
```
**Features**: Persistent memory across sessions

#### Sequential Thinking Server
```yaml
sequentialthinking:
  command: npx
  args: ["-y", "@modelcontextprotocol/server-sequentialthinking"]
```
**Features**: Enhanced step-by-step problem solving

#### Inspector (Optional)
```yaml
inspector:
  command: npx
  args: ["-y", "@modelcontextprotocol/inspector"]
```
**Features**: Debug MCP server connections

## Environment Variables

### Required for Local Servers
```bash
# Context7 Redis Configuration
UPSTASH_REDIS_REST_URL=your_redis_url
UPSTASH_REDIS_REST_TOKEN=your_redis_token

# SurrealDB Configuration (for Ptolemies)
SURREALDB_URL=ws://localhost:8000/rpc
SURREALDB_USERNAME=root
SURREALDB_PASSWORD=root
SURREALDB_NAMESPACE=ptolemies
SURREALDB_DATABASE=knowledge

# Dart AI Configuration
DART_TOKEN=dsa_1a21dba13961ac8abbe58ea7f9cb7d5621148dc2f3c79a9d346ef40430795e8f
```

### DevQ.ai Project Variables
```bash
DEVQAI_ROOT=/path/to/devqai
PYTHONPATH=$DEVQAI_ROOT:$PYTHONPATH
MCP_SERVERS_PATH=$DEVQAI_ROOT/mcp/mcp-servers
PTOLEMIES_PATH=$DEVQAI_ROOT/ptolemies
```

## Server Management

### Starting All Servers
```bash
# Local Python servers
start-context7
start-crawl4ai
start-ptolemies

# External NPX servers
start-dart

# Inspector for debugging
mcp-inspect
```

### Health Checks
```bash
# Test individual servers
dart-test                    # Test Dart AI
verify-db                    # Test Ptolemies/SurrealDB
show_env_vars               # Check environment

# General MCP inspection
npx -y @modelcontextprotocol/inspector
```

## Integration Patterns

### Development Workflow
1. **Context7**: Provides multi-hop reasoning for complex queries
2. **Dart AI**: Analyzes code quality and suggests improvements
3. **Ptolemies**: Integrates domain-specific knowledge
4. **Crawl4AI**: Gathers external documentation and research
5. **Git**: Manages version control operations
6. **Filesystem**: Handles file operations

### Data Flow
```
External Sources → Crawl4AI → Ptolemies Knowledge Base
                                     ↓
Code Analysis ← Dart AI ← Context7 ← Knowledge Queries
     ↓
Git Operations ← Development Decisions ← Filesystem Operations
```

## Prerequisites

### System Requirements
- **Node.js**: For NPX-based servers
- **Python 3.12**: For local MCP servers
- **SurrealDB**: For Ptolemies knowledge base
- **Redis**: For Context7 memory (Upstash)

### Installation Verification
```bash
# Check Node.js/NPX
node --version
npx --version

# Check Python
python --version
python -c "import surrealdb"

# Check SurrealDB
surreal version

# Check Redis connection
curl -H "Authorization: Bearer $UPSTASH_REDIS_REST_TOKEN" $UPSTASH_REDIS_REST_URL
```

## Security Considerations

### Token Management
- Store sensitive tokens in environment variables
- Use separate tokens for different environments
- Regularly rotate API tokens
- Monitor token usage and access

### Network Security
- Local servers run on localhost only
- External API calls use secure HTTPS
- Database connections use appropriate authentication
- MCP protocol uses secure communication channels

## Troubleshooting

### Common Issues

#### Server Won't Start
```bash
# Check environment variables
echo $DART_TOKEN
echo $UPSTASH_REDIS_REST_URL

# Verify dependencies
npm list -g dart-mcp-server
python -c "import context7_mcp"

# Check ports and processes
lsof -i :8000  # SurrealDB default port
ps aux | grep mcp
```

#### Database Connection Issues
```bash
# SurrealDB
surreal start --log trace --user root --pass root memory
verify-db

# Redis
curl -H "Authorization: Bearer $UPSTASH_REDIS_REST_TOKEN" $UPSTASH_REDIS_REST_URL/ping
```

#### Permission Issues
```bash
# NPX cache
npx clear-npx-cache

# Python modules
pip install --upgrade -r requirements.txt

# File permissions
chmod +x setup-database.sh
```

## Performance Monitoring

### Server Metrics
- Response times for each MCP server
- Memory usage of local Python servers
- Database query performance
- Network latency for external services

### Optimization Tips
- Cache frequently accessed knowledge base queries
- Batch similar requests to external APIs
- Monitor Redis memory usage for Context7
- Optimize SurrealDB queries for Ptolemies

## Future Enhancements

### Planned Integrations
- Additional domain-specific MCP servers
- Enhanced monitoring and logging
- Load balancing for high-traffic scenarios
- Automated failover mechanisms

### Development Roadmap
- Custom MCP server templates
- Integrated testing framework
- Performance analytics dashboard
- Advanced security features