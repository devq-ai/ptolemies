# Graphiti Integration Python Files - Complete Reference

This document provides a comprehensive overview of all Python scripts involved in the Ptolemies-Graphiti integration, organized by functionality and purpose.

## Overview

The Graphiti integration provides temporal knowledge graph capabilities to the Ptolemies knowledge base, implementing a hybrid architecture that combines SurrealDB document storage with Graphiti's temporal reasoning and relationship extraction.

## Core Integration Files

Located in `/Users/dionedge/devqai/ptolemies/src/ptolemies/integrations/graphiti/`

### 1. `__init__.py`
**Purpose**: Module documentation and initialization for Graphiti integration  
**Description**: Provides comprehensive documentation and references for the Graphiti temporal knowledge graph integration. Contains module-level documentation explaining the integration architecture and usage patterns.

### 2. `client.py`
**Purpose**: High-level Graphiti integration client  
**Description**: Main integration interface providing async operations for:
- Processing knowledge items through Graphiti for relationship extraction
- Hybrid search combining SurrealDB documents with Graphiti relationships
- Temporal reasoning over knowledge evolution
- Custom entity extraction for domain-specific content
- Cross-system referencing and data consistency

### 3. `graphiti_service.py`
**Purpose**: Standalone Graphiti service with FastAPI HTTP API  
**Description**: Runs in separate Python environment (venv_graphiti) with pydantic 2.x to resolve dependency conflicts. Provides HTTP endpoints for:
- Episode processing (`/episodes`)
- Entity search (`/entities/search`) 
- Relationship search (`/relationships/search`)
- Graph visualization (`/graph/visualize`)
- Temporal evolution (`/temporal/evolution`)
- Health checks (`/health`)

### 4. `service_wrapper.py`
**Purpose**: Service wrapper for communicating with Graphiti service  
**Description**: HTTP client that manages the lifecycle of the Graphiti service process, handling:
- Service startup/shutdown management
- HTTP API communication with retry logic
- Process lifecycle management
- Request/response handling with error recovery
- Automatic service health monitoring

### 5. `mcp_integration.py`
**Purpose**: MCP integration layer for Graphiti-enhanced tools  
**Description**: Provides MCP tools for:
- Enhanced search with temporal reasoning
- Knowledge item processing through Graphiti
- Temporal evolution tracking
- Graph management and cleanup
- Advanced LLM interaction capabilities

### 6. `visualization.py`
**Purpose**: Visual knowledge graph interface with D3.js  
**Description**: Provides interactive graph visualization with:
- Real-time graph exploration
- Temporal evolution visualization
- Conflict detection and highlighting
- WebSocket support for real-time updates
- Complete HTML interface with D3.js force-directed graphs

## Hybrid Storage Integration

### 7. `hybrid_storage.py`
**Location**: `/Users/dionedge/devqai/ptolemies/src/ptolemies/integrations/`  
**Purpose**: Hybrid knowledge management coordinating SurrealDB and Graphiti  
**Description**: Unified interface providing:
- Document storage and retrieval (SurrealDB)
- Relationship extraction and temporal reasoning (Graphiti)
- Cross-system referencing and consistency
- Hybrid search and discovery across both systems
- Coordinated operations and transaction management

## Enhanced MCP Server

### 8. `enhanced_ptolemies_mcp.py`
**Location**: `/Users/dionedge/devqai/ptolemies/src/ptolemies/mcp/`  
**Purpose**: Enhanced MCP server with Graphiti integration  
**Description**: Advanced MCP server providing 6 enhanced tools:
- `search_knowledge`: Hybrid search across documents and knowledge graph
- `store_knowledge`: Store with automatic relationship extraction
- `get_knowledge_evolution`: Track concept evolution over time
- `explore_graph`: Interactive graph exploration and visualization
- `get_related_concepts`: Find related items using graph traversal
- `temporal_reasoning`: Answer questions using temporal graph data

## Migration and Setup Scripts

### 9. `migrate_to_graphiti.py`
**Location**: `/Users/dionedge/devqai/ptolemies/`  
**Purpose**: Migration script for existing knowledge items to Graphiti  
**Description**: Comprehensive migration tool with:
- Batch processing for performance optimization
- Progress tracking and detailed reporting
- Error recovery and retry logic
- Detailed migration statistics and validation
- Resume capability for interrupted migrations

### 10. `verify_graphiti_setup.py`
**Location**: `/Users/dionedge/devqai/ptolemies/`  
**Purpose**: Verification script for Graphiti integration setup  
**Description**: Validates:
- Graphiti library installation and version compatibility
- Neo4j connectivity and authentication
- Environment variables and configuration
- Basic functionality and integration tests

### 11. `deploy_enhanced_system.py`
**Location**: `/Users/dionedge/devqai/ptolemies/`  
**Purpose**: Complete deployment script for enhanced Ptolemies system  
**Description**: Handles:
- Environment verification and setup
- Graphiti venv_graphiti environment preparation
- Database migration to Graphiti
- Enhanced MCP server deployment
- System validation and comprehensive testing

## Web Interface and Exploration

### 12. `web_graph_explorer.py`
**Location**: `/Users/dionedge/devqai/ptolemies/`  
**Purpose**: Web interface for exploring knowledge graph at http://localhost:8080  
**Description**: FastAPI application with:
- Interactive D3.js graph visualization
- Search and exploration capabilities
- Real-time data from hybrid storage system
- Midnight UI Dark Palette design system (following DevQ.ai design rules)
- Temporal evolution tracking interface

### 13. `web_graph_explorer_old.py`
**Location**: `/Users/dionedge/devqai/ptolemies/`  
**Purpose**: Previous version of web graph explorer  
**Description**: Earlier implementation of the web interface before design system update

## Testing and Validation Scripts

### 14. `test_enhanced_mcp.py`
**Location**: `/Users/dionedge/devqai/ptolemies/`  
**Purpose**: Test script for enhanced MCP server functionality  
**Description**: Validates enhanced MCP server components:
- Tool registration and functionality
- Hybrid storage integration
- Error handling and edge cases
- Performance under load

### 15. `test_hybrid_integration.py`
**Location**: `/Users/dionedge/devqai/ptolemies/`  
**Purpose**: End-to-end test for hybrid storage integration  
**Description**: Comprehensive testing of:
- SurrealDB connectivity and operations
- Graphiti service wrapper functionality
- Hybrid knowledge manager operations
- Cross-system synchronization and consistency

## Architecture Overview

The Graphiti integration implements a sophisticated hybrid architecture:

### **Storage Layer**
- **SurrealDB**: Primary document storage, metadata, search indices
- **Neo4j**: Graph database backend for Graphiti temporal relationships

### **Integration Layer**
- **Graphiti**: Temporal relationship extraction, graph reasoning, visualization  
- **Service Wrapper**: HTTP communication bridge resolving pydantic version conflicts
- **Hybrid Manager**: Coordinated operations, cross-system references, unified queries

### **Service Layer**
- **Enhanced MCP Server**: Rich toolset for LLM interaction with temporal reasoning capabilities
- **Web Interface**: Interactive graph exploration and visualization
- **Migration Tools**: Data migration and system deployment automation

## Key Features

1. **Temporal Reasoning**: Track how concepts and relationships evolve over time
2. **Hybrid Search**: Combine document content with graph relationships
3. **Relationship Extraction**: Automatic discovery of connections between concepts
4. **Interactive Visualization**: Real-time graph exploration with D3.js
5. **Cross-System Consistency**: Coordinated operations across SurrealDB and Graphiti
6. **LLM Integration**: Advanced MCP tools for AI-powered knowledge exploration

## Usage Notes

- **Dependency Management**: Graphiti service runs in separate environment (venv_graphiti) to resolve pydantic version conflicts
- **Service Architecture**: HTTP-based communication between main system and Graphiti service
- **Data Flow**: Documents stored in SurrealDB, relationships extracted to Graphiti, unified access via hybrid manager
- **Development**: Use `deploy_enhanced_system.py` for complete setup and `test_hybrid_integration.py` for validation

This integration provides advanced knowledge base capabilities including temporal reasoning, relationship discovery, and interactive graph exploration while maintaining compatibility with existing SurrealDB document storage.