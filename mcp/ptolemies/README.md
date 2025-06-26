# @devq-ai/ptolemies-mcp

[![npm version](https://badge.fury.io/js/@devq-ai%2Ftolemies-mcp.svg)](https://badge.fury.io/js/@devq-ai%2Ftolemies-mcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![DevQ.AI](https://img.shields.io/badge/DevQ.AI-Ecosystem-blue)](https://devq.ai)

> **Unified MCP Server for AI-Assisted Development**
>
> Provides semantic access to SurrealDB, Neo4j, and Dehallucinator services through a single Model Context Protocol interface optimized for AI assistant workflows.

---

## 🚀 **Quick Start**

### **Installation**

```bash
# Install via npm
npm install -g @devq-ai/ptolemies-mcp

# Or use npx (recommended)
npx @devq-ai/ptolemies-mcp
```

### **Basic Usage**

```bash
# Start the MCP server
ptolemies-mcp

# Or with custom configuration
ptolemies-mcp --neo4j-uri bolt://localhost:7687 --surrealdb-url ws://localhost:8000/rpc
```

### **MCP Client Configuration**

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "ptolemies": {
      "command": "npx",
      "args": ["-y", "@devq-ai/ptolemies-mcp"],
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "your-password",
        "SURREALDB_URL": "ws://localhost:8000/rpc",
        "SURREALDB_NAMESPACE": "ptolemies",
        "SURREALDB_DATABASE": "knowledge"
      }
    }
  }
}
```

---

## 📋 **Overview**

The Ptolemies MCP Server is a unified interface to the DevQ.AI knowledge ecosystem, combining:

- **🧠 Neo4j Knowledge Graph**: 77 nodes, 156 relationships across 17 frameworks
- **🔍 SurrealDB Vector Store**: Semantic search across documentation and code
- **🛡️ Dehallucinator AI Validation**: Real-time code validation with 97.3% accuracy

### **Key Features**

- **🔀 Hybrid Knowledge Search**: Combines graph traversal and vector similarity
- **🧪 AI Code Validation**: Detect hallucinations and validate framework usage
- **🗺️ Learning Path Discovery**: Intelligent progression paths between technologies
- **📊 Framework Analysis**: Deep insights into dependencies and relationships
- **💊 System Health Monitoring**: Real-time service status and diagnostics

---

## 🛠️ **Available Tools**

### **Knowledge Search & Retrieval**

#### `hybrid-knowledge-search`
Combines Neo4j graph traversal with SurrealDB vector search for comprehensive knowledge retrieval.

```json
{
  "query": "How to implement authentication in FastAPI?",
  "frameworks": ["FastAPI"],
  "max_results": 5,
  "similarity_threshold": 0.7
}
```

#### `framework-knowledge-query`
Query specific framework knowledge with relationship context.

```json
{
  "framework": "FastAPI",
  "topic": "authentication",
  "depth": 2,
  "include_examples": true
}
```

#### `learning-path-discovery`
Discover intelligent learning progression paths between frameworks.

```json
{
  "start_framework": "HTML",
  "end_framework": "FastAPI",
  "difficulty_preference": "intermediate"
}
```

### **Code Validation & Analysis**

#### `validate-code-snippet`
Validate code for AI hallucinations using the dehallucinator service.

```json
{
  "code": "from fastapi import FastAPI\napp = FastAPI()\napp.magic_method()",
  "framework": "FastAPI",
  "confidence_threshold": 0.75
}
```

#### `analyze-framework-usage`
Analyze code for framework usage patterns and provide suggestions.

```json
{
  "code": "from fastapi import FastAPI\napp = FastAPI()",
  "detect_patterns": true,
  "suggest_improvements": true
}
```

### **Relationship Discovery**

#### `framework-dependencies`
Analyze framework dependencies and relationships.

```json
{
  "framework": "FastAPI",
  "include_transitive": true,
  "max_depth": 2
}
```

#### `topic-relationships`
Discover topic relationships and related concepts.

```json
{
  "topic": "authentication",
  "relationship_types": ["IMPLEMENTS", "RELATED_TO"],
  "max_results": 10
}
```

### **Meta-Analysis & Monitoring**

#### `knowledge-coverage-analysis`
Analyze documentation coverage and identify knowledge gaps.

```json
{
  "framework": "FastAPI"
}
```

#### `ecosystem-overview`
Comprehensive overview of the DevQ.AI ecosystem.

```json
{
  "category": "backend"
}
```

#### `system-health-check`
Check health status of all integrated services.

```json
{}
```

---

## ⚙️ **Configuration**

### **Environment Variables**

| Variable | Default | Description |
|----------|---------|-------------|
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j connection URI |
| `NEO4J_USERNAME` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | `ptolemies` | Neo4j password |
| `NEO4J_DATABASE` | `ptolemies` | Neo4j database name |
| `SURREALDB_URL` | `ws://localhost:8000/rpc` | SurrealDB connection URL |
| `SURREALDB_NAMESPACE` | `ptolemies` | SurrealDB namespace |
| `SURREALDB_DATABASE` | `knowledge` | SurrealDB database |
| `OPENAI_API_KEY` | - | OpenAI API key (optional, for embeddings) |

### **Service Requirements**

- **Minimum Services**: 2 of 3 services must be available
- **Graceful Degradation**: Server continues with reduced functionality
- **Health Monitoring**: Real-time service status checking

#### **Neo4j Setup**
```bash
# Start Neo4j with default configuration
neo4j start

# Create ptolemies database
cypher-shell -a bolt://localhost:7687 -u neo4j -p password
CREATE DATABASE ptolemies;
```

#### **SurrealDB Setup**
```bash
# Start SurrealDB
surreal start --bind 0.0.0.0:8000 file://ptolemies.db

# Connect and set up namespace
surreal sql --conn ws://localhost:8000 --user root --pass root
USE NS ptolemies DB knowledge;
```

---

## 🎯 **Integration Examples**

### **Claude Desktop / Cline**

```json
{
  "mcpServers": {
    "ptolemies": {
      "command": "npx",
      "args": ["-y", "@devq-ai/ptolemies-mcp"],
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "your-password"
      }
    }
  }
}
```

### **Zed IDE**

```json
{
  "mcpServers": {
    "ptolemies": {
      "command": "npx",
      "args": ["-y", "@devq-ai/ptolemies-mcp"],
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "SURREALDB_URL": "ws://localhost:8000/rpc"
      }
    }
  }
}
```

### **Continue.dev**

```json
{
  "mcp": {
    "servers": {
      "ptolemies": {
        "command": "npx",
        "args": ["-y", "@devq-ai/ptolemies-mcp"]
      }
    }
  }
}
```

### **Python Client**

```python
import asyncio
from mcp import Client

async def query_ptolemies():
    async with Client() as client:
        # Connect to ptolemies MCP server
        await client.connect("npx", ["-y", "@devq-ai/ptolemies-mcp"])

        # Search for FastAPI knowledge
        result = await client.call_tool(
            "hybrid-knowledge-search",
            {
                "query": "FastAPI authentication best practices",
                "frameworks": ["FastAPI"],
                "max_results": 3
            }
        )

        print(f"Found {result['total_results']} results")

        # Validate code snippet
        validation = await client.call_tool(
            "validate-code-snippet",
            {
                "code": "from fastapi import FastAPI\napp = FastAPI()",
                "framework": "FastAPI"
            }
        )

        print(f"Code is valid: {validation['is_valid']}")

# Run the example
asyncio.run(query_ptolemies())
```

---

## 📊 **Performance**

### **Response Times**
- **Simple Queries**: < 200ms (health checks, basic searches)
- **Complex Analysis**: < 1s (hybrid search, code validation)
- **Large Results**: < 2s (ecosystem overview, learning paths)

### **Concurrency**
- **Maximum Concurrent Requests**: 10
- **Automatic Queuing**: Requests queued when limit reached
- **Timeout**: 30 seconds per operation

### **Resource Usage**
- **Memory**: ~50MB baseline, scales with result size
- **CPU**: Efficient async operations, minimal blocking
- **Network**: Optimized database queries with connection pooling

---

## 🔍 **Troubleshooting**

### **Common Issues**

#### **Service Connection Errors**
```bash
# Check service health
ptolemies-mcp --health-check

# Test individual services
neo4j status
surreal version
```

#### **Permission Errors**
```bash
# Ensure proper permissions
chmod +x node_modules/@devq-ai/ptolemies-mcp/dist/index.js

# Or reinstall globally
npm uninstall -g @devq-ai/ptolemies-mcp
npm install -g @devq-ai/ptolemies-mcp
```

#### **Environment Configuration**
```bash
# Verify environment variables
echo $NEO4J_URI
echo $SURREALDB_URL

# Test with explicit configuration
ptolemies-mcp --neo4j-uri bolt://localhost:7687 --surrealdb-url ws://localhost:8000/rpc
```

### **Debug Mode**

```bash
# Enable debug logging
DEBUG=ptolemies:* ptolemies-mcp

# Or set log level
LOG_LEVEL=debug ptolemies-mcp
```

### **Health Monitoring**

```bash
# Check system health
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/call", "params": {"name": "system-health-check", "arguments": {}}}'
```

---

## 🧪 **Development**

### **Local Development**

```bash
# Clone the repository
git clone https://github.com/devq-ai/ptolemies.git
cd ptolemies/mcp/ptolemies

# Install dependencies
npm install

# Build the project
npm run build

# Run in development mode
npm run dev
```

### **Testing**

```bash
# Run tests
npm test

# Run with coverage
npm run test:coverage

# Test specific functionality
npm run test -- --grep "hybrid search"
```

### **Contributing**

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📚 **Documentation**

### **API Reference**
- [Complete API Documentation](https://docs.devq.ai/ptolemies-mcp/api)
- [Tool Specifications](https://docs.devq.ai/ptolemies-mcp/tools)
- [Integration Guide](https://docs.devq.ai/ptolemies-mcp/integration)

### **Guides**
- [Getting Started](https://docs.devq.ai/ptolemies-mcp/getting-started)
- [Configuration Guide](https://docs.devq.ai/ptolemies-mcp/configuration)
- [Best Practices](https://docs.devq.ai/ptolemies-mcp/best-practices)
- [Troubleshooting](https://docs.devq.ai/ptolemies-mcp/troubleshooting)

### **Examples**
- [MCP Client Examples](https://docs.devq.ai/ptolemies-mcp/examples)
- [Integration Patterns](https://docs.devq.ai/ptolemies-mcp/patterns)
- [Use Cases](https://docs.devq.ai/ptolemies-mcp/use-cases)

---

## 🤝 **Community**

### **Support**
- **GitHub Issues**: [Report bugs and request features](https://github.com/devq-ai/ptolemies/issues)
- **Discord**: [Join our community](https://discord.gg/devq-ai)
- **Email**: [engineering@devq.ai](mailto:engineering@devq.ai)

### **Resources**
- **DevQ.AI Website**: [https://devq.ai](https://devq.ai)
- **Documentation**: [https://docs.devq.ai](https://docs.devq.ai)
- **Blog**: [https://blog.devq.ai](https://blog.devq.ai)

---

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🏆 **Acknowledgments**

- **Model Context Protocol**: Built on the MCP standard for AI assistant integration
- **DevQ.AI Ecosystem**: Part of the comprehensive AI-assisted development platform
- **Open Source Community**: Thanks to all contributors and supporters

---

## 🚀 **What's Next**

### **Upcoming Features**
- **Real-time Knowledge Updates**: Live synchronization with documentation sources
- **Advanced Caching**: Redis-based result caching for improved performance
- **Multi-language Support**: Expand beyond Python to JavaScript, Go, Rust
- **Custom Validators**: User-defined code validation rules
- **Learning Analytics**: Track and improve learning path recommendations

### **Roadmap**
- **Q1 2024**: Enhanced search algorithms and performance optimization
- **Q2 2024**: Real-time updates and advanced caching
- **Q3 2024**: Multi-language support and custom validators
- **Q4 2024**: Learning analytics and community features

---

**Built with ❤️ by the DevQ.AI Engineering Team**

**Status: Production Ready** 🚀
