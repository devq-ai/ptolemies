# Neo4j MCP Server

A Model Context Protocol (MCP) server that provides Neo4j graph database integration for the DevQ.AI ecosystem.

## Features

- **Cypher Query Execution**: Execute arbitrary Cypher queries against Neo4j
- **Schema Introspection**: Retrieve database schema information
- **Node Management**: Create and manage graph nodes
- **Relationship Management**: Create and manage graph relationships
- **Comprehensive Logging**: Full Logfire instrumentation for observability
- **Resource Access**: Access connection and schema information via MCP resources
- **Prompt Templates**: Built-in prompts for Cypher query assistance

## Installation

```bash
pip install -e .
```

## Configuration

Set the following environment variables:

```bash
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="your_password"
export NEO4J_DATABASE="neo4j"
```

## Usage

### As MCP Server

Start the server:

```bash
neo4j-mcp-server
```

### Configuration in Claude Code

Add to your `.claude/settings.local.json`:

```json
{
  "mcpServers": {
    "neo4j": {
      "command": "python",
      "args": ["-m", "neo4j_mcp_server"],
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "your_password",
        "NEO4J_DATABASE": "neo4j"
      }
    }
  }
}
```

## Tools

### execute_cypher_query
Execute a Cypher query against the Neo4j database.

**Parameters:**
- `query` (string, required): The Cypher query to execute
- `parameters` (object, optional): Parameters for the query

### get_database_schema
Retrieve the database schema information including labels, relationship types, property keys, indexes, and constraints.

### create_node
Create a new node in the database.

**Parameters:**
- `labels` (array, required): Array of labels for the node
- `properties` (object, optional): Properties for the node

### create_relationship
Create a relationship between two nodes.

**Parameters:**
- `from_node_query` (string, required): Cypher query to find the source node
- `to_node_query` (string, required): Cypher query to find the target node
- `relationship_type` (string, required): Type of the relationship
- `properties` (object, optional): Properties for the relationship

## Resources

### neo4j://schema
Access the database schema information.

### neo4j://connection
Access connection information and status.

## Prompts

### cypher_query_helper
Provides assistance with Cypher query construction based on the database schema.

### graph_analysis
Provides guidance for analyzing graph structure and patterns.

## Monitoring

The server includes comprehensive Logfire instrumentation:

- Connection management
- Query execution metrics
- Error tracking
- Performance monitoring
- MCP operation logging

## Testing

Run the test suite:

```bash
python -m pytest tests/test_neo4j_mcp_server.py -v
```

## Development

The server is built using:

- **MCP Protocol**: Standard Model Context Protocol implementation
- **Neo4j Python Driver**: Official Neo4j driver for Python
- **Logfire**: Comprehensive observability and monitoring
- **Async/Await**: Full async support for performance

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Claude Code   │────│  Neo4j MCP     │────│    Neo4j        │
│   (Client)      │    │  Server         │    │   Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                       ┌─────────────────┐
                       │    Logfire      │
                       │  Monitoring     │
                       └─────────────────┘
```

## Contributing

1. Follow the DevQ.AI development standards
2. Include comprehensive tests for new features
3. Add Logfire instrumentation for all operations
4. Update documentation for API changes

## License

MIT License - see LICENSE file for details.