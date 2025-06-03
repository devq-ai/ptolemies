# Ptolemies Knowledge Base

A SurrealDB-powered knowledge graph system with semantic search capabilities for AI agents.

## Overview

Ptolemies is a hybrid knowledge base system that combines graph database capabilities with vector search to provide a comprehensive knowledge management solution for AI agents and applications. It leverages SurrealDB for structured data, relationships, and vector search capabilities.

## Features

- **Semantic Search**: Find information based on meaning, not just keywords
- **Knowledge Graph**: Explore relationships between knowledge items
- **Real-time Updates**: Get notified when knowledge changes
- **Multi-modal Support**: Store and retrieve text, code, and references to media
- **Agent-friendly API**: Designed for AI agent integration via MCP
- **Web Crawling**: Automatically ingest content from the web
- **Flexible Schema**: Adapt to evolving knowledge structures

## Architecture

Ptolemies uses a hybrid architecture:

- **SurrealDB**: Primary database for structured data, relationships, and vector search
- **Graphiti**: Visualization layer for knowledge graph exploration
- **MCP Integration**: Model Context Protocol servers for agent access
- **Vector Embeddings**: Semantic representations of content for similarity search

## Getting Started

### Prerequisites

- SurrealDB
- Python 3.10+
- Node.js 18+ (for graphiti visualization, optional)
- Docker (optional, for containerized deployment)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/devq-ai/ptolemies.git
   cd ptolemies
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure the environment:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. Setup the database:
   ```bash
   ./setup-database.sh
   ```

5. Verify the installation:
   ```bash
   ./verify-database.py
   ```

## Using the CLI

Ptolemies comes with a powerful command-line interface for managing the knowledge base.

### Start the database:
```bash
./cli.py db start
```

### Ingest content from a URL:
```bash
./cli.py ingest url https://surrealdb.com/docs/surrealdb --tags=database,documentation
```

### Search for content:
```bash
# Keyword search
./cli.py search keyword "graph database"

# Semantic search
./cli.py search semantic "How do vector embeddings work?"
```

### Manage knowledge items:
```bash
# List items
./cli.py item list --tags=database

# Create item
./cli.py item create --title "Example Item" --content "This is an example." --tags=example,test

# Get item details
./cli.py item get <item_id> --show-relationships

# Update item
./cli.py item update <item_id> --title "Updated Title" --update-embedding

# Delete item
./cli.py item delete <item_id>
```

### Import/Export:
```bash
# Export knowledge
./cli.py data export --output knowledge_export.json --include-embeddings

# Import knowledge
./cli.py data import --input knowledge_export.json --include-embeddings
```

## Using the MCP Server

Ptolemies provides a Model Context Protocol (MCP) server for AI agent integration:

```bash
# Start the MCP server
python -m ptolemies.mcp.ptolemies_mcp
```

The server provides the following MCP tools:
- `search`: Semantic search in the knowledge base
- `retrieve`: Get a specific knowledge item by ID
- `store`: Store a new knowledge item
- `related`: Find related items through graph relationships

## Integration with Crawl4AI

Ptolemies integrates with Crawl4AI MCP for web content ingestion:

```bash
# Display configured crawl targets
./display-crawl-targets.py

# Run a crawl
python -m ptolemies.integrations.crawl4ai.cli crawl-url https://surrealdb.com/docs/surrealdb --depth 2 --tags=database,documentation
```

## Development

### Project Structure

```
ptolemies/
├── cli.py                    # Command-line interface
├── setup-database.sh         # Database setup script
├── verify-database.py        # Database verification script
├── crawl_targets.md          # Crawl target configuration
├── db/                       # Database operations
│   └── surrealdb_client.py   # SurrealDB client
├── integrations/             # External integrations
│   └── crawl4ai/             # Crawl4AI integration
├── mcp/                      # MCP server implementation
│   └── ptolemies_mcp.py      # MCP server
├── models/                   # Data models
│   └── knowledge_item.py     # Core data models
└── data/                     # Data storage
    ├── files/                # Stored files
    └── crawl_targets.json    # Crawl target configuration
```

## License

MIT