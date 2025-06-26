# Ptolemies MCP Server API Documentation

## 🚀 **Overview**

The Ptolemies MCP (Model Context Protocol) Server provides unified, semantic access to the DevQ.ai knowledge ecosystem through a single interface. It integrates SurrealDB vector storage, Neo4j knowledge graphs, and Dehallucinator AI validation services to deliver intelligent, context-aware responses optimized for AI assistant workflows.

### **Key Features**
- **Hybrid Knowledge Search**: Combines vector similarity and graph traversal
- **AI Code Validation**: Real-time hallucination detection with 97.3% accuracy
- **Framework Analysis**: Deep insights into technology relationships and dependencies
- **Learning Path Discovery**: Intelligent progression paths between frameworks
- **System Health Monitoring**: Comprehensive service status and diagnostics

---

## 📋 **Server Information**

### **Connection Details**
- **Server Name**: `ptolemies-mcp`
- **Version**: `1.0.0`
- **Protocol**: Model Context Protocol (MCP) 1.0
- **Transport**: stdio (standard input/output)
- **Configuration**: Environment variables via `.zed/settings.json`

### **Data Sources**
- **Neo4j Knowledge Graph**: 77 nodes, 156 relationships across 17 frameworks
- **SurrealDB Vector Store**: Document chunks with semantic embeddings
- **Dehallucinator Service**: AI pattern detection and validation

### **Environment Variables**
```bash
# Required for full functionality
SURREALDB_URL=ws://localhost:8000/rpc
SURREALDB_NAMESPACE=ptolemies
SURREALDB_DATABASE=knowledge
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=ptolemies
NEO4J_DATABASE=ptolemies
OPENAI_API_KEY=sk-...  # Optional, for embeddings
```

---

## 🛠️ **Available Tools**

### **1. Knowledge Search & Retrieval**

#### `hybrid-knowledge-search`
**Description**: Perform hybrid search combining Neo4j graph traversal with SurrealDB vector search for comprehensive knowledge retrieval.

**Input Schema**:
```json
{
  "query": "string (required)",
  "frameworks": ["string"] (optional),
  "max_results": "integer" (1-50, default: 10),
  "include_code_examples": "boolean" (default: true),
  "similarity_threshold": "number" (0.0-1.0, default: 0.7)
}
```

**Example Request**:
```json
{
  "query": "How to implement authentication in FastAPI?",
  "frameworks": ["FastAPI"],
  "max_results": 5,
  "include_code_examples": true,
  "similarity_threshold": 0.7
}
```

**Response Format**:
```json
{
  "success": true,
  "timestamp": "2024-01-20T10:30:00Z",
  "source": "ptolemies-mcp",
  "tool": "hybrid-knowledge-search",
  "query": "How to implement authentication in FastAPI?",
  "total_results": 5,
  "vector_results": [...],
  "graph_results": [...],
  "combined_results": [
    {
      "id": "doc_123",
      "type": "document_chunk",
      "content": "FastAPI provides built-in security utilities...",
      "source": "surrealdb",
      "framework": "FastAPI",
      "similarity_score": 0.92,
      "combined_score": 0.89
    }
  ],
  "frameworks_found": ["FastAPI"],
  "topics_found": ["authentication", "security"],
  "search_metadata": {
    "similarity_threshold": 0.7,
    "search_timestamp": "2024-01-20T10:30:00Z"
  }
}
```

---

#### `framework-knowledge-query`
**Description**: Query specific framework knowledge with relationship context from Neo4j and relevant documentation from SurrealDB.

**Input Schema**:
```json
{
  "framework": "string (required)",
  "topic": "string (required)",
  "depth": "integer" (1-5, default: 2),
  "include_examples": "boolean" (default: true)
}
```

**Example Request**:
```json
{
  "framework": "FastAPI",
  "topic": "authentication",
  "depth": 2,
  "include_examples": true
}
```

**Response Format**:
```json
{
  "success": true,
  "timestamp": "2024-01-20T10:30:00Z",
  "source": "ptolemies-mcp",
  "tool": "framework-knowledge-query",
  "framework": "FastAPI",
  "topic": "authentication",
  "graph_context": {
    "framework_node": {
      "name": "FastAPI",
      "type": "backend",
      "language": "Python"
    },
    "relationship_paths": [...],
    "related_frameworks": ["Pydantic", "Starlette"]
  },
  "documentation": [
    {
      "id": "doc_456",
      "content": "Authentication implementation guide...",
      "source": "FastAPI Docs",
      "quality_score": 0.95
    }
  ],
  "depth": 2,
  "include_examples": true
}
```

---

#### `learning-path-discovery`
**Description**: Discover learning progression paths between frameworks using Neo4j relationship analysis.

**Input Schema**:
```json
{
  "start_framework": "string (required)",
  "end_framework": "string (required)",
  "include_prerequisites": "boolean" (default: true),
  "difficulty_preference": "string" (enum: ["beginner", "intermediate", "advanced", "any"], default: "any")
}
```

**Example Request**:
```json
{
  "start_framework": "HTML",
  "end_framework": "FastAPI",
  "include_prerequisites": true,
  "difficulty_preference": "intermediate"
}
```

**Response Format**:
```json
{
  "success": true,
  "timestamp": "2024-01-20T10:30:00Z",
  "source": "ptolemies-mcp",
  "tool": "learning-path-discovery",
  "start_framework": "HTML",
  "end_framework": "FastAPI",
  "path_length": 4,
  "total_steps": 6,
  "estimated_duration": "6-8 weeks",
  "difficulty_rating": "intermediate",
  "learning_steps": [
    {
      "step_number": 1,
      "framework": "JavaScript",
      "topic": "ES6 fundamentals",
      "description": "Learn modern JavaScript syntax and concepts",
      "prerequisites": ["HTML", "CSS"],
      "resources": ["MDN Web Docs", "JavaScript.info"],
      "estimated_time": "2 weeks",
      "difficulty_level": "beginner"
    }
  ],
  "alternative_paths": [...],
  "prerequisites": ["HTML", "CSS", "Basic Programming"]
}
```

---

### **2. Code Validation & Analysis**

#### `validate-code-snippet`
**Description**: Validate code snippet for AI hallucinations using the dehallucinator service with knowledge graph validation.

**Input Schema**:
```json
{
  "code": "string (required)",
  "framework": "string (optional)",
  "confidence_threshold": "number" (0.0-1.0, default: 0.75),
  "include_suggestions": "boolean" (default: true)
}
```

**Example Request**:
```json
{
  "code": "from fastapi import FastAPI\napp = FastAPI()\napp.magic_method()",
  "framework": "FastAPI",
  "confidence_threshold": 0.75,
  "include_suggestions": true
}
```

**Response Format**:
```json
{
  "success": true,
  "timestamp": "2024-01-20T10:30:00Z",
  "source": "ptolemies-mcp",
  "tool": "validate-code-snippet",
  "code_snippet": "from fastapi import FastAPI\napp = FastAPI()\napp.magic_method()",
  "is_valid": false,
  "overall_confidence": 0.94,
  "frameworks_detected": ["FastAPI"],
  "issues": [
    {
      "type": "non_existent_method",
      "line": 3,
      "code": "app.magic_method()",
      "framework": "FastAPI",
      "confidence": 0.94,
      "severity": "critical",
      "description": "Method 'magic_method' does not exist in FastAPI",
      "suggestion": "Use documented FastAPI methods like app.get(), app.post(), etc."
    }
  ],
  "patterns_detected": ["ai_generated_placeholder"],
  "suggestions": [
    "Replace app.magic_method() with valid FastAPI decorator methods",
    "Refer to FastAPI documentation for available app methods"
  ],
  "analysis_metadata": {
    "confidence_threshold": 0.75,
    "analysis_timestamp": "2024-01-20T10:30:00Z"
  }
}
```

---

#### `analyze-framework-usage`
**Description**: Analyze code for framework usage patterns and provide suggestions based on validated knowledge.

**Input Schema**:
```json
{
  "code": "string (required)",
  "detect_patterns": "boolean" (default: true),
  "suggest_improvements": "boolean" (default: true)
}
```

**Example Request**:
```json
{
  "code": "from fastapi import FastAPI\napp = FastAPI()\n\n@app.get('/')\ndef root(): return {'message': 'Hello'}",
  "detect_patterns": true,
  "suggest_improvements": true
}
```

**Response Format**:
```json
{
  "success": true,
  "timestamp": "2024-01-20T10:30:00Z",
  "source": "ptolemies-mcp",
  "tool": "analyze-framework-usage",
  "code_snippet": "...",
  "frameworks_used": ["FastAPI"],
  "usage_patterns": [
    {
      "pattern": "basic_app_setup",
      "confidence": 0.98,
      "description": "Standard FastAPI application initialization"
    }
  ],
  "best_practices": [
    "Use type hints for better API documentation",
    "Add response models for consistent API responses"
  ],
  "potential_issues": [],
  "improvement_suggestions": [
    "Add response_model parameter to endpoint decorator",
    "Consider adding API versioning"
  ],
  "confidence_score": 0.92
}
```

---

### **3. Relationship Discovery**

#### `framework-dependencies`
**Description**: Analyze framework dependencies and relationships from the Neo4j knowledge graph.

**Input Schema**:
```json
{
  "framework": "string (required)",
  "include_transitive": "boolean" (default: false),
  "max_depth": "integer" (1-10, default: 3)
}
```

**Example Request**:
```json
{
  "framework": "FastAPI",
  "include_transitive": true,
  "max_depth": 2
}
```

**Response Format**:
```json
{
  "success": true,
  "timestamp": "2024-01-20T10:30:00Z",
  "source": "ptolemies-mcp",
  "tool": "framework-dependencies",
  "root_framework": "FastAPI",
  "total_dependencies": 8,
  "direct_dependencies": 3,
  "transitive_dependencies": 5,
  "dependency_nodes": [
    {
      "framework": "Pydantic",
      "version": "2.0+",
      "dependency_type": "core",
      "is_direct": true,
      "depth": 1
    }
  ],
  "dependency_relationships": [
    {
      "source_framework": "FastAPI",
      "target_framework": "Pydantic",
      "relationship_type": "DEPENDS_ON",
      "description": "Core dependency for data validation"
    }
  ],
  "circular_dependencies": [],
  "analysis_depth": 2
}
```

---

#### `topic-relationships`
**Description**: Discover topic relationships and related concepts across the knowledge graph.

**Input Schema**:
```json
{
  "topic": "string (required)",
  "relationship_types": ["string"] (optional),
  "max_results": "integer" (1-50, default: 20)
}
```

**Example Request**:
```json
{
  "topic": "authentication",
  "relationship_types": ["IMPLEMENTS", "RELATED_TO"],
  "max_results": 10
}
```

**Response Format**:
```json
{
  "success": true,
  "timestamp": "2024-01-20T10:30:00Z",
  "source": "ptolemies-mcp",
  "tool": "topic-relationships",
  "topic": "authentication",
  "related_topics": [
    {
      "source_topic": "authentication",
      "target_topic": "authorization",
      "relationship_strength": 0.89,
      "relationship_type": "RELATED_TO",
      "shared_frameworks": ["FastAPI", "Django"],
      "confidence": 0.92
    }
  ],
  "frameworks_associated": ["FastAPI", "Django", "Flask"],
  "documentation_coverage": 0.87,
  "knowledge_density": 0.94
}
```

---

### **4. Meta-Analysis**

#### `knowledge-coverage-analysis`
**Description**: Analyze documentation coverage and knowledge gaps for a specific framework across all data sources.

**Input Schema**:
```json
{
  "framework": "string (required)"
}
```

**Example Request**:
```json
{
  "framework": "FastAPI"
}
```

**Response Format**:
```json
{
  "success": true,
  "timestamp": "2024-01-20T10:30:00Z",
  "source": "ptolemies-mcp",
  "tool": "knowledge-coverage-analysis",
  "framework": "FastAPI",
  "coverage_metrics": {
    "framework": "FastAPI",
    "total_documentation_chunks": 234,
    "unique_topics_covered": 45,
    "average_quality_score": 0.89,
    "documentation_completeness": 0.87,
    "last_updated": "2024-01-15T14:30:00Z"
  },
  "knowledge_gaps": [
    {
      "framework": "FastAPI",
      "topic": "advanced_middleware",
      "gap_type": "insufficient_examples",
      "severity": "medium",
      "description": "Limited examples for custom middleware implementation",
      "suggested_resources": ["FastAPI Advanced User Guide"]
    }
  ],
  "comparison_frameworks": [
    {
      "framework": "Django",
      "coverage_score": 0.92,
      "relationship": "alternative"
    }
  ],
  "recommendations": [
    "Add more advanced middleware examples",
    "Expand WebSocket documentation coverage"
  ]
}
```

---

#### `ecosystem-overview`
**Description**: Provide comprehensive overview of the DevQ.ai ecosystem including frameworks, relationships, and capabilities.

**Input Schema**:
```json
{
  "category": "string" (enum: ["backend", "frontend", "database", "tool", "library", "all"], default: "all")
}
```

**Example Request**:
```json
{
  "category": "backend"
}
```

**Response Format**:
```json
{
  "success": true,
  "timestamp": "2024-01-20T10:30:00Z",
  "source": "ptolemies-mcp",
  "tool": "ecosystem-overview",
  "category": "backend",
  "stats": {
    "total_frameworks": 17,
    "frameworks_by_type": {
      "backend": 7,
      "frontend": 4,
      "database": 1,
      "tool": 5
    },
    "total_relationships": 156,
    "relationships_by_type": {
      "DEPENDS_ON": 45,
      "IMPLEMENTS": 34,
      "DOCUMENTED_BY": 28
    },
    "total_documentation_chunks": 1247,
    "average_quality_score": 0.87,
    "most_connected_frameworks": ["FastAPI", "NextJS", "Tailwind"],
    "trending_topics": ["authentication", "async programming", "API design"]
  },
  "featured_frameworks": [
    {
      "name": "FastAPI",
      "type": "backend",
      "language": "Python",
      "description": "Modern, fast web framework for building APIs"
    }
  ],
  "framework_categories": {
    "backend": ["FastAPI", "Logfire", "Panel"],
    "frontend": ["NextJS", "Tailwind CSS"]
  },
  "learning_paths": [
    {
      "name": "Full-Stack Development",
      "frameworks": ["HTML", "JavaScript", "NextJS", "FastAPI"],
      "difficulty": "intermediate"
    }
  ],
  "recent_updates": [],
  "health_metrics": {
    "data_freshness": 0.94,
    "system_availability": 0.999
  }
}
```

---

### **5. System Monitoring**

#### `system-health-check`
**Description**: Check the health status of all integrated services (Neo4j, SurrealDB, Dehallucinator).

**Input Schema**:
```json
{}
```

**Response Format**:
```json
{
  "success": true,
  "timestamp": "2024-01-20T10:30:00Z",
  "source": "ptolemies-mcp",
  "tool": "system-health-check",
  "neo4j_status": {
    "service": "neo4j",
    "connected": true,
    "last_ping": "2024-01-20T10:30:00Z",
    "error_message": null
  },
  "surrealdb_status": {
    "service": "surrealdb",
    "connected": true,
    "last_ping": "2024-01-20T10:30:00Z",
    "error_message": null
  },
  "dehallucinator_status": {
    "service": "dehallucinator",
    "connected": true,
    "last_ping": "2024-01-20T10:30:00Z",
    "error_message": null
  },
  "overall_healthy": true,
  "last_check": "2024-01-20T10:30:00Z"
}
```

---

## 📚 **Resources**

### **Available Resources**

#### `ptolemies://health`
**Description**: Current health status of all integrated services
**MIME Type**: `application/json`
**Content**: Real-time system health information

#### `ptolemies://stats`
**Description**: Usage statistics and performance metrics
**MIME Type**: `application/json`
**Content**: Server statistics and tool usage data

---

## 🚨 **Error Handling**

### **Error Response Format**
All errors follow a consistent format:

```json
{
  "success": false,
  "timestamp": "2024-01-20T10:30:00Z",
  "source": "ptolemies-mcp",
  "error_type": "validation_error",
  "error_message": "Missing required parameter: query",
  "error_details": {
    "tool_name": "hybrid-knowledge-search",
    "missing_parameters": ["query"]
  }
}
```

### **Common Error Types**

| Error Type | Description | Resolution |
|------------|-------------|------------|
| `server_not_initialized` | Server hasn't completed initialization | Wait for initialization or check service health |
| `service_unavailable` | One or more data sources unavailable | Check service connections and restart if needed |
| `validation_error` | Invalid input parameters | Check parameter types and required fields |
| `tool_execution_error` | Error during tool execution | Check logs and service health |
| `rate_limit_exceeded` | Too many concurrent requests | Reduce request frequency |

---

## 📈 **Performance Guidelines**

### **Request Limits**
- **Concurrent Requests**: Maximum 10 simultaneous requests
- **Response Time**: < 200ms for simple queries, < 1s for complex analysis
- **Timeout**: 30 seconds for all operations

### **Optimization Tips**
1. **Use Specific Frameworks**: Filter by framework for faster results
2. **Adjust Result Limits**: Use smaller `max_results` for faster responses
3. **Cache Awareness**: Repeated queries benefit from internal caching
4. **Batch Operations**: Combine related queries when possible

### **Best Practices**
- Monitor system health before making critical requests
- Handle partial service availability gracefully
- Implement retry logic for network-related errors
- Use appropriate confidence thresholds for code validation

---

## 🔧 **Integration Examples**

### **Zed IDE Configuration**
```json
{
  "mcpServers": {
    "ptolemies": {
      "command": "python",
      "args": ["src/ptolemies_mcp_server.py"],
      "cwd": "/Users/dionedge/devqai/ptolemies",
      "env": {
        "SURREALDB_URL": "ws://localhost:8000/rpc",
        "SURREALDB_NAMESPACE": "ptolemies",
        "SURREALDB_DATABASE": "knowledge",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "ptolemies",
        "OPENAI_API_KEY": "${OPENAI_API_KEY}",
        "PYTHONPATH": "/Users/dionedge/devqai/ptolemies/src:$PYTHONPATH"
      }
    }
  }
}
```

### **Python Client Example**
```python
import asyncio
import mcp

async def query_ptolemies():
    async with mcp.Client() as client:
        # Search for FastAPI authentication information
        result = await client.call_tool(
            "hybrid-knowledge-search",
            {
                "query": "FastAPI JWT authentication",
                "frameworks": ["FastAPI"],
                "max_results": 5
            }
        )

        print(f"Found {result['total_results']} results")

        # Validate a code snippet
        code_result = await client.call_tool(
            "validate-code-snippet",
            {
                "code": "from fastapi import FastAPI\napp = FastAPI()",
                "framework": "FastAPI"
            }
        )

        print(f"Code is valid: {code_result['is_valid']}")

# Run the example
asyncio.run(query_ptolemies())
```

---

## 📊 **Monitoring & Observability**

### **Logfire Integration**
The server integrates with Logfire for comprehensive observability:

- **Request Tracing**: All tool calls are traced with timing and metadata
- **Performance Metrics**: Response times, error rates, and throughput
- **System Health**: Service connectivity and resource usage
- **Error Tracking**: Detailed error logs with context and stack traces

### **Health Monitoring**
Regular health checks ensure optimal performance:

- **Service Connectivity**: Neo4j, SurrealDB, and Dehallucinator status
- **Data Freshness**: Age and quality of indexed knowledge
- **Resource Usage**: Memory, CPU, and network utilization
- **Performance Trends**: Historical response times and error rates

---

## 🎯 **Roadmap & Future Enhancements**

### **Planned Features**
- **Enhanced Learning Paths**: Algorithm improvements for path discovery
- **Advanced Analytics**: Framework adoption trends and popularity metrics
- **Real-time Updates**: Live knowledge base updates and notifications
- **Custom Validators**: User-defined code validation rules
- **Multi-language Support**: Expand beyond Python to JavaScript, Go, Rust

### **Performance Improvements**
- **Caching Layer**: Redis-based result caching for improved response times
- **Query Optimization**: Enhanced hybrid search algorithms
- **Parallel Processing**: Concurrent execution of independent operations
- **Load Balancing**: Multiple server instances for high availability

---

## 📞 **Support & Maintenance**

### **Troubleshooting**
1. **Check System Health**: Use `system-health-check` tool first
2. **Verify Configuration**: Ensure all environment variables are set
3. **Review Logs**: Check Logfire dashboards for detailed error information
4. **Restart Services**: Restart individual services if health checks fail

### **Maintenance Schedule**
- **Daily**: Automated health monitoring and alerting
- **Weekly**: Performance review and optimization
- **Monthly**: Knowledge base updates and service maintenance
- **Quarterly**: Major feature releases and architectural improvements

### **Contact Information**
- **Maintainer**: DevQ.ai Engineering Team
- **Email**: support@devq.ai
- **Documentation**: https://docs.devq.ai/ptolemies-mcp
- **Source Code**: https://github.com/devq-ai/ptolemies

---

**Last Updated**: January 20, 2024
**API Version**: 1.0.0
**Service Status**: Production Ready 🚀
