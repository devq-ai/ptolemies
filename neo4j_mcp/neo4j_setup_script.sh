#!/bin/bash

# Neo4j MCP Server Setup Script
# This script sets up the Neo4j MCP server in your DevQ.ai project

set -e

echo "🚀 Setting up Neo4j MCP Server..."

# Define paths
DEVQAI_ROOT="/Users/dionedge/devqai"
MCP_SERVERS_DIR="$DEVQAI_ROOT/mcp/mcp-servers"
NEO4J_MCP_DIR="$MCP_SERVERS_DIR/neo4j-mcp"

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p "$NEO4J_MCP_DIR"

# Create package structure
echo "📦 Setting up Python package structure..."
mkdir -p "$NEO4J_MCP_DIR/neo4j_mcp"
touch "$NEO4J_MCP_DIR/neo4j_mcp/__init__.py"

# Create the main server file
echo "💾 Creating server.py..."
cat > "$NEO4J_MCP_DIR/neo4j_mcp/server.py" << 'EOF'
#!/usr/bin/env python3
"""
Neo4j MCP Server

A Model Context Protocol server that provides Neo4j graph database integration.
This server enables natural language interactions with Neo4j databases through
Claude Code and other MCP clients.
"""

import asyncio
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Union

import neo4j
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    GetPromptRequest,
    GetPromptResult,
    ListPromptsRequest,
    ListPromptsResult,
    ListResourcesRequest,
    ListResourcesResult,
    ListToolsRequest,
    ListToolsResult,
    Prompt,
    PromptArgument,
    ReadResourceRequest,
    ReadResourceResult,
    Resource,
    TextContent,
    Tool,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Neo4jDatabase:
    """Neo4j database connection and query execution."""
    
    def __init__(self, uri: str, username: str, password: str, database: str = "neo4j"):
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        self.driver = None
        self._connect()
    
    def _connect(self):
        """Establish connection to Neo4j database."""
        try:
            self.driver = neo4j.GraphDatabase.driver(
                self.uri, 
                auth=(self.username, self.password)
            )
            # Test connection
            with self.driver.session(database=self.database) as session:
                session.run("RETURN 1")
            logger.info(f"Connected to Neo4j database: {self.database}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    def execute_query(self, query: str, parameters: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a Cypher query and return results."""
        if not self.driver:
            raise RuntimeError("No database connection")
        
        parameters = parameters or {}
        
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, parameters)
                
                # Extract results
                records = []
                for record in result:
                    records.append(dict(record))
                
                # Get summary information
                summary = result.consume()
                
                return {
                    "records": records,
                    "summary": {
                        "query": query,
                        "parameters": parameters,
                        "result_count": len(records),
                        "result_available_after": summary.result_available_after,
                        "result_consumed_after": summary.result_consumed_after,
                        "server_info": {
                            "address": summary.server.address,
                            "protocol_version": str(summary.server.protocol_version),
                        },
                        "database": summary.database,
                        "query_type": summary.query_type,
                        "plan": summary.plan.arguments if summary.plan else None,
                        "profile": summary.profile.arguments if summary.profile else None,
                        "notifications": [n.description for n in summary.notifications] if summary.notifications else [],
                        "counters": {
                            "nodes_created": summary.counters.nodes_created,
                            "nodes_deleted": summary.counters.nodes_deleted,
                            "relationships_created": summary.counters.relationships_created,
                            "relationships_deleted": summary.counters.relationships_deleted,
                            "properties_set": summary.counters.properties_set,
                            "labels_added": summary.counters.labels_added,
                            "labels_removed": summary.counters.labels_removed,
                            "indexes_added": summary.counters.indexes_added,
                            "indexes_removed": summary.counters.indexes_removed,
                            "constraints_added": summary.counters.constraints_added,
                            "constraints_removed": summary.counters.constraints_removed,
                        }
                    }
                }
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return {
                "error": str(e),
                "query": query,
                "parameters": parameters
            }
    
    def get_schema(self) -> Dict[str, Any]:
        """Get database schema information."""
        schema_info = {}
        
        try:
            with self.driver.session(database=self.database) as session:
                # Get node labels
                result = session.run("CALL db.labels()")
                schema_info["labels"] = [record["label"] for record in result]
                
                # Get relationship types
                result = session.run("CALL db.relationshipTypes()")
                schema_info["relationship_types"] = [record["relationshipType"] for record in result]
                
                # Get property keys
                result = session.run("CALL db.propertyKeys()")
                schema_info["property_keys"] = [record["propertyKey"] for record in result]
                
                # Get indexes
                result = session.run("SHOW INDEXES")
                schema_info["indexes"] = [dict(record) for record in result]
                
                # Get constraints
                result = session.run("SHOW CONSTRAINTS")
                schema_info["constraints"] = [dict(record) for record in result]
                
        except Exception as e:
            logger.error(f"Schema retrieval failed: {e}")
            schema_info["error"] = str(e)
        
        return schema_info
    
    def close(self):
        """Close database connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")


class Neo4jMCPServer:
    """Neo4j MCP Server implementation."""
    
    def __init__(self):
        self.server = Server("neo4j-mcp-server")
        self.db = None
        self._setup_handlers()
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize Neo4j database connection."""
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        username = os.getenv("NEO4J_USERNAME", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        database = os.getenv("NEO4J_DATABASE", "neo4j")
        
        try:
            self.db = Neo4jDatabase(uri, username, password, database)
            logger.info("Neo4j MCP Server initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j connection: {e}")
            sys.exit(1)
    
    def _setup_handlers(self):
        """Set up MCP request handlers."""
        
        @self.server.list_tools()
        async def list_tools() -> ListToolsResult:
            return ListToolsResult(
                tools=[
                    Tool(
                        name="execute_cypher_query",
                        description="Execute a Cypher query against the Neo4j database",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "The Cypher query to execute"
                                },
                                "parameters": {
                                    "type": "object",
                                    "description": "Optional parameters for the query",
                                    "additionalProperties": True
                                }
                            },
                            "required": ["query"]
                        }
                    ),
                    Tool(
                        name="get_database_schema",
                        description="Get the schema information of the Neo4j database",
                        inputSchema={
                            "type": "object",
                            "properties": {}
                        }
                    ),
                    Tool(
                        name="create_node",
                        description="Create a new node in the Neo4j database",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "labels": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Labels for the node"
                                },
                                "properties": {
                                    "type": "object",
                                    "description": "Properties for the node",
                                    "additionalProperties": True
                                }
                            },
                            "required": ["labels"]
                        }
                    ),
                    Tool(
                        name="create_relationship",
                        description="Create a relationship between two nodes",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "from_node_query": {
                                    "type": "string",
                                    "description": "Cypher query to find the source node"
                                },
                                "to_node_query": {
                                    "type": "string",
                                    "description": "Cypher query to find the target node"
                                },
                                "relationship_type": {
                                    "type": "string",
                                    "description": "Type of the relationship"
                                },
                                "properties": {
                                    "type": "object",
                                    "description": "Properties for the relationship",
                                    "additionalProperties": True
                                }
                            },
                            "required": ["from_node_query", "to_node_query", "relationship_type"]
                        }
                    )
                ]
            )
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            try:
                if name == "execute_cypher_query":
                    query = arguments.get("query")
                    parameters = arguments.get("parameters", {})
                    
                    if not query:
                        raise ValueError("Query is required")
                    
                    result = self.db.execute_query(query, parameters)
                    
                    return CallToolResult(
                        content=[
                            TextContent(
                                type="text",
                                text=f"Query Results:\n{self._format_query_result(result)}"
                            )
                        ]
                    )
                
                elif name == "get_database_schema":
                    schema = self.db.get_schema()
                    
                    return CallToolResult(
                        content=[
                            TextContent(
                                type="text",
                                text=f"Database Schema:\n{self._format_schema(schema)}"
                            )
                        ]
                    )
                
                elif name == "create_node":
                    labels = arguments.get("labels", [])
                    properties = arguments.get("properties", {})
                    
                    if not labels:
                        raise ValueError("At least one label is required")
                    
                    # Build CREATE query
                    labels_str = ":".join(labels)
                    props_str = self._format_properties(properties)
                    query = f"CREATE (n:{labels_str} {props_str}) RETURN n"
                    
                    result = self.db.execute_query(query)
                    
                    return CallToolResult(
                        content=[
                            TextContent(
                                type="text",
                                text=f"Node Created:\n{self._format_query_result(result)}"
                            )
                        ]
                    )
                
                elif name == "create_relationship":
                    from_query = arguments.get("from_node_query")
                    to_query = arguments.get("to_node_query")
                    rel_type = arguments.get("relationship_type")
                    properties = arguments.get("properties", {})
                    
                    if not all([from_query, to_query, rel_type]):
                        raise ValueError("All relationship parameters are required")
                    
                    # Build relationship creation query
                    props_str = self._format_properties(properties)
                    query = f"""
                    MATCH (a) WHERE {from_query}
                    MATCH (b) WHERE {to_query}
                    CREATE (a)-[r:{rel_type} {props_str}]->(b)
                    RETURN a, r, b
                    """
                    
                    result = self.db.execute_query(query)
                    
                    return CallToolResult(
                        content=[
                            TextContent(
                                type="text",
                                text=f"Relationship Created:\n{self._format_query_result(result)}"
                            )
                        ]
                    )
                
                else:
                    raise ValueError(f"Unknown tool: {name}")
                    
            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"Error: {str(e)}"
                        )
                    ],
                    isError=True
                )
        
        @self.server.list_resources()
        async def list_resources() -> ListResourcesResult:
            return ListResourcesResult(
                resources=[
                    Resource(
                        uri="neo4j://schema",
                        name="Database Schema",
                        description="Neo4j database schema information",
                        mimeType="application/json"
                    ),
                    Resource(
                        uri="neo4j://connection",
                        name="Connection Info",
                        description="Neo4j connection information",
                        mimeType="application/json"
                    )
                ]
            )
        
        @self.server.read_resource()
        async def read_resource(uri: str) -> ReadResourceResult:
            if uri == "neo4j://schema":
                schema = self.db.get_schema()
                return ReadResourceResult(
                    contents=[
                        TextContent(
                            type="text",
                            text=self._format_schema(schema)
                        )
                    ]
                )
            elif uri == "neo4j://connection":
                connection_info = {
                    "uri": self.db.uri,
                    "database": self.db.database,
                    "username": self.db.username,
                    "status": "connected" if self.db.driver else "disconnected"
                }
                return ReadResourceResult(
                    contents=[
                        TextContent(
                            type="text",
                            text=f"Connection Info:\n{self._format_dict(connection_info)}"
                        )
                    ]
                )
            else:
                raise ValueError(f"Unknown resource: {uri}")
        
        @self.server.list_prompts()
        async def list_prompts() -> ListPromptsResult:
            return ListPromptsResult(
                prompts=[
                    Prompt(
                        name="cypher_query_helper",
                        description="Help with Cypher query construction",
                        arguments=[
                            PromptArgument(
                                name="intent",
                                description="What you want to accomplish with the query",
                                required=True
                            )
                        ]
                    ),
                    Prompt(
                        name="graph_analysis",
                        description="Analyze graph structure and patterns",
                        arguments=[
                            PromptArgument(
                                name="focus",
                                description="What aspect of the graph to analyze",
                                required=True
                            )
                        ]
                    )
                ]
            )
        
        @self.server.get_prompt()
        async def get_prompt(name: str, arguments: Dict[str, str]) -> GetPromptResult:
            if name == "cypher_query_helper":
                intent = arguments.get("intent", "")
                schema = self.db.get_schema()
                
                prompt_text = f"""
                Help me write a Cypher query for: {intent}
                
                Available labels: {', '.join(schema.get('labels', []))}
                Available relationship types: {', '.join(schema.get('relationship_types', []))}
                Available properties: {', '.join(schema.get('property_keys', []))}
                
                Please provide a Cypher query that accomplishes this goal.
                """
                
                return GetPromptResult(
                    description="Cypher query construction assistance",
                    messages=[
                        {
                            "role": "user",
                            "content": {
                                "type": "text",
                                "text": prompt_text
                            }
                        }
                    ]
                )
            
            elif name == "graph_analysis":
                focus = arguments.get("focus", "")
                
                prompt_text = f"""
                Analyze the Neo4j graph with focus on: {focus}
                
                Consider:
                - Node distribution and patterns
                - Relationship patterns and density
                - Data quality and completeness
                - Performance considerations
                - Potential insights or anomalies
                
                Please provide an analysis query and interpretation approach.
                """
                
                return GetPromptResult(
                    description="Graph analysis guidance",
                    messages=[
                        {
                            "role": "user",
                            "content": {
                                "type": "text",
                                "text": prompt_text
                            }
                        }
                    ]
                )
            
            else:
                raise ValueError(f"Unknown prompt: {name}")
    
    def _format_query_result(self, result: Dict[str, Any]) -> str:
        """Format query result for display."""
        if "error" in result:
            return f"Error: {result['error']}"
        
        formatted = []
        
        # Add summary
        summary = result.get("summary", {})
        formatted.append(f"Query: {summary.get('query', 'N/A')}")
        formatted.append(f"Records returned: {summary.get('result_count', 0)}")
        
        if summary.get("counters"):
            counters = summary["counters"]
            changes = []
            for key, value in counters.items():
                if value > 0:
                    changes.append(f"{key}: {value}")
            if changes:
                formatted.append(f"Changes: {', '.join(changes)}")
        
        # Add records
        records = result.get("records", [])
        if records:
            formatted.append("\nRecords:")
            for i, record in enumerate(records[:10]):  # Limit to first 10 records
                formatted.append(f"  {i+1}: {record}")
            if len(records) > 10:
                formatted.append(f"  ... and {len(records) - 10} more records")
        
        return "\n".join(formatted)
    
    def _format_schema(self, schema: Dict[str, Any]) -> str:
        """Format schema information for display."""
        if "error" in schema:
            return f"Error retrieving schema: {schema['error']}"
        
        formatted = []
        
        labels = schema.get("labels", [])
        if labels:
            formatted.append(f"Labels ({len(labels)}): {', '.join(labels)}")
        
        rel_types = schema.get("relationship_types", [])
        if rel_types:
            formatted.append(f"Relationship Types ({len(rel_types)}): {', '.join(rel_types)}")
        
        properties = schema.get("property_keys", [])
        if properties:
            formatted.append(f"Property Keys ({len(properties)}): {', '.join(properties)}")
        
        indexes = schema.get("indexes", [])
        if indexes:
            formatted.append(f"\nIndexes ({len(indexes)}):")
            for idx in indexes:
                formatted.append(f"  - {idx.get('name', 'N/A')}: {idx.get('type', 'N/A')}")
        
        constraints = schema.get("constraints", [])
        if constraints:
            formatted.append(f"\nConstraints ({len(constraints)}):")
            for constraint in constraints:
                formatted.append(f"  - {constraint.get('name', 'N/A')}: {constraint.get('type', 'N/A')}")
        
        return "\n".join(formatted)
    
    def _format_properties(self, properties: Dict[str, Any]) -> str:
        """Format properties for Cypher query."""
        if not properties:
            return ""
        
        prop_pairs = []
        for key, value in properties.items():
            if isinstance(value, str):
                prop_pairs.append(f"{key}: '{value}'")
            else:
                prop_pairs.append(f"{key}: {value}")
        
        return "{" + ", ".join(prop_pairs) + "}"
    
    def _format_dict(self, data: Dict[str, Any]) -> str:
        """Format dictionary for display."""
        formatted = []
        for key, value in data.items():
            formatted.append(f"{key}: {value}")
        return "\n".join(formatted)
    
    async def run(self):
        """Run the MCP server."""
        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options()
                )
        finally:
            if self.db:
                self.db.close()


async def main():
    """Main entry point."""
    server = Neo4jMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
EOF

# Create requirements.txt
echo "📋 Creating requirements.txt..."
cat > "$NEO4J_MCP_DIR/requirements.txt" << 'EOF'
# Neo4j MCP Server Dependencies

# Model Context Protocol
mcp>=1.0.0

# Neo4j Python Driver
neo4j>=5.14.0

# Additional utilities
pydantic>=2.0.0
typing-extensions>=4.5.0
EOF

# Create setup.py
echo "📋 Creating setup.py..."
cat > "$NEO4J_MCP_DIR/setup.py" << 'EOF'
from setuptools import setup, find_packages

setup(
    name="neo4j-mcp",
    version="1.0.0",
    description="Neo4j Model Context Protocol Server",
    author="DevQ.ai",
    packages=find_packages(),
    install_requires=[
        "mcp>=1.0.0",
        "neo4j>=5.14.0",
        "pydantic>=2.0.0",
        "typing-extensions>=4.5.0",
    ],
    entry_points={
        "console_scripts": [
            "neo4j-mcp-server=neo4j_mcp.server:main",
        ],
    },
    python_requires=">=3.8",
)
EOF

# Create __main__.py for module execution
echo "📋 Creating __main__.py..."
cat > "$NEO4J_MCP_DIR/neo4j_mcp/__main__.py" << 'EOF'
import asyncio
from .server import main

if __name__ == "__main__":
    asyncio.run(main())
EOF

# Create README.md
echo "📖 Creating README.md..."
cat > "$NEO4J_MCP_DIR/README.md" << 'EOF'
# Neo4j MCP Server

A Model Context Protocol (MCP) server for Neo4j graph database integration with Claude Code and other MCP clients.

## Features

- Execute Cypher queries against Neo4j databases
- Retrieve database schema information
- Create nodes and relationships
- Natural language interaction with graph data
- Support for parameterized queries
- Comprehensive error handling and logging

## Installation

1. Install dependencies:
```bash
cd /Users/dionedge/devqai/mcp/mcp-servers/neo4j-mcp
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="your_password"
export NEO4J_DATABASE="neo4j"  # optional, defaults to "neo4j"
```

## Configuration

Add the following to your Claude Code MCP configuration:

```json
{
  "mcpServers": {
    "neo4j": {
      "command": "python",
      "args": ["-m", "neo4j_mcp.server"],
      "cwd": "/Users/dionedge/devqai/mcp/mcp-servers/neo4j-mcp",
      "env": {
        "NEO4J_URI": "${NEO4J_URI}",
        "NEO4J_USERNAME": "${NEO4J_USERNAME}",
        "NEO4J_PASSWORD": "${NEO4J_PASSWORD}",
        "NEO4J_DATABASE": "${NEO4J_DATABASE}",
        "PYTHONPATH": "/Users/dionedge/devqai:$PYTHONPATH"
      }
    }
  }
}
```

## Usage

### Tools Available

1. **execute_cypher_query**: Execute any Cypher query
2. **get_database_schema**: Retrieve database schema information
3. **create_node**: Create new nodes with labels and properties
4. **create_relationship**: Create relationships between existing nodes

### Resources Available

1. **neo4j://schema**: Database schema information
2. **neo4j://connection**: Connection status and information

### Prompts Available

1. **cypher_query_helper**: Get help writing Cypher queries
2. **graph_analysis**: Analyze graph structure and patterns

## Examples

### Query Examples
```cypher
// Find all nodes
MATCH (n) RETURN n LIMIT 10

// Create a person
CREATE (p:Person {name: 'John Doe', age: 30}) RETURN p

// Create a relationship
MATCH (a:Person {name: 'John Doe'})
MATCH (b:Company {name: 'DevQ.ai'})
CREATE (a)-[r:WORKS_FOR]->(b)
RETURN a, r, b
```

## Development

Run the server directly for testing:
```bash
cd /Users/dionedge/devqai/mcp/mcp-servers/neo4j-mcp
python -m neo4j_mcp.server
```

## License

MIT License
EOF

# Create .env.example
echo "🔐 Creating .env.example..."
cat > "$NEO4J_MCP_DIR/.env.example" << 'EOF'
# Neo4j Connection Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password_here
NEO4J_DATABASE=neo4j

# Optional: Enable debug logging
DEBUG=false
LOG_LEVEL=INFO
EOF

# Install dependencies
echo "📦 Installing Python dependencies..."
cd "$NEO4J_MCP_DIR"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🐍 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
echo "📦 Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Make the server executable
chmod +x "$NEO4J_MCP_DIR/neo4j_mcp/server.py"

echo "✅ Neo4j MCP Server setup complete!"
echo ""
echo "📁 Server location: $NEO4J_MCP_DIR"
echo "🔧 Next steps:"
echo "   1. Set up your Neo4j database (local or Aura)"
echo "   2. Configure environment variables:"
echo "      cp $NEO4J_MCP_DIR/.env.example $NEO4J_MCP_DIR/.env"
echo "      # Edit the .env file with your Neo4j credentials"
echo "   3. Test the server:"
echo "      cd $NEO4J_MCP_DIR"
echo "      source venv/bin/activate"
echo "      python -m neo4j_mcp.server"
echo "   4. Add the server to your Claude Code configuration"
echo ""
echo "🎉 Ready to use with Claude Code!