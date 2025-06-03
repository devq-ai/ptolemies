# Ptolemies Knowledge Base Specification

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [Data Model](#data-model)
5. [API Specification](#api-specification)
6. [Integration Points](#integration-points)
7. [Security Requirements](#security-requirements)
8. [Performance Requirements](#performance-requirements)
9. [Scalability Requirements](#scalability-requirements)
10. [Deployment Architecture](#deployment-architecture)

## Overview

Ptolemies is a knowledge base system that provides persistent storage, retrieval, and management of both structured and unstructured information. It's designed to serve as a central repository for agent tools, enabling semantic search, graph-based knowledge exploration, and real-time updates.

The knowledge base is based on a local instance of SurrealDB: https://github.com/surrealdb/surrealdb/

We use crawl4ai to crawl target urls and ingest converted markdown files to SurrealDB: https://github.com/unclecode/crawl4ai

Finally we graphiti to further process the text into a knowledge graph for better and faster retrieval:https://github.com/getzep/graphiti

SurrealDB is the only database we need for this configuration. All three of these components muct be installed and the only right answer is to directly reference the documentation for implementation. 

## Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────────┐
│                       Ptolemies Knowledge Base                  │
├─────────────┬─────────────────────────────────┬────────────────┤
│             │                                 │                │
│   Access    │         Core Services           │    Storage     │
│    Layer    │                                 │     Layer      │
│             │                                 │                │
├─────────────┼─────────────────────────────────┼────────────────┤
│             │                                 │                │
│  REST API   │      Knowledge Management       │   SurrealDB    │
│             │                                 │                │
├─────────────┤      Embedding Service          ├────────────────┤
│             │                                 │                │
│  GraphQL    │      Retrieval Service          │ Vector Storage │
│             │                                 │                │
├─────────────┤      Indexing Service           ├────────────────┤
│             │                                 │                │
│  MCP Server │      Synchronization Service    │   File Store   │
│             │                                 │                │
└─────────────┴─────────────────────────────────┴────────────────┘
```

### Data Flow

1. **Ingestion Flow**:
   - Content is ingested via REST API, GraphQL, or MCP interfaces
   - Text content is processed by the Embedding Service to generate vector embeddings
   - Content and metadata are stored in SurrealDB
   - Vector embeddings are stored in the vector database
   - References between content and embeddings are established

2. **Retrieval Flow**:
   - Queries arrive via API endpoints
   - Semantic queries are processed by the Retrieval Service
   - Vector similarity search identifies relevant content
   - Graph relationships enrich results with context
   - Combined results are returned to the client

3. **Synchronization Flow**:
   - External content sources are monitored by the Sync Service
   - Changes are detected and processed for ingestion
   - Content is crawled using crawl4ai-mcp integration
   - Real-time notifications are sent to subscribers

## Core Components

### 1. Knowledge Management Service
- Handles CRUD operations for knowledge items
- Manages tags, categories, and metadata
- Implements versioning and history tracking
- Provides bulk import/export capabilities

### 2. Embedding Service
- Generates vector embeddings for text content
- Supports multiple embedding models and providers
- Implements embedding caching and optimization
- Handles batch processing for efficiency

### 3. Retrieval Service
- Processes semantic search queries
- Combines vector search with traditional filters
- Applies relevance scoring algorithms
- Implements hybrid search strategies

### 4. Indexing Service
- Maintains search indices for quick retrieval
- Handles re-indexing and index optimization
- Implements custom analyzers and tokenizers
- Supports field-specific indexing strategies

### 5. Synchronization Service
- Integrates with external content sources
- Monitors for content changes and updates
- Schedules and manages crawling operations
- Maintains content freshness metrics

## Data Model

### Knowledge Items

```
knowledge_item {
    id: string                   # Unique identifier
    title: string                # Item title
    content: string              # Primary content (text)
    content_type: string         # Type of content (text, code, etc.)
    metadata: map<string, any>   # Flexible metadata
    tags: [string]               # List of tags
    embedding_id: string         # Reference to vector embedding
    created_at: datetime         # Creation timestamp
    updated_at: datetime         # Last update timestamp
    version: integer             # Version number
    source: string               # Origin of the content
    related: [relationship]      # Graph relationships
}
```

### Embedding Storage

```
embedding {
    id: string                  # Unique identifier
    vector: [float]             # Vector representation
    model: string               # Embedding model used
    dimensions: integer         # Vector dimensions
    item_id: string             # Reference to knowledge item
    created_at: datetime        # Creation timestamp
}
```

### Relationships

```
relationship {
    type: string                # Relationship type
    source_id: string           # Source item ID
    target_id: string           # Target item ID
    weight: float               # Relationship strength
    metadata: map<string, any>  # Relationship metadata
}
```

## API Specification

### REST API Endpoints

#### Knowledge Management

```
GET    /api/v1/knowledge                  # List knowledge items
POST   /api/v1/knowledge                  # Create knowledge item
GET    /api/v1/knowledge/{id}             # Get knowledge item
PUT    /api/v1/knowledge/{id}             # Update knowledge item
DELETE /api/v1/knowledge/{id}             # Delete knowledge item
POST   /api/v1/knowledge/batch            # Batch operations
```

#### Search and Retrieval

```
GET    /api/v1/search                     # Search knowledge items
POST   /api/v1/search/semantic            # Semantic search
POST   /api/v1/search/hybrid              # Combined search
GET    /api/v1/search/similar/{id}        # Find similar items
```

#### Graph Operations

```
GET    /api/v1/graph/{id}/related         # Get related items
POST   /api/v1/graph/relationship         # Create relationship
DELETE /api/v1/graph/relationship/{id}    # Delete relationship
GET    /api/v1/graph/traverse             # Graph traversal
```

### GraphQL Schema

```graphql
type KnowledgeItem {
  id: ID!
  title: String!
  content: String!
  contentType: String!
  metadata: JSONObject
  tags: [String!]
  createdAt: DateTime!
  updatedAt: DateTime!
  version: Int!
  source: String
  related: [Relationship!]
}

type Relationship {
  id: ID!
  type: String!
  sourceId: ID!
  targetId: ID!
  weight: Float
  metadata: JSONObject
}

type Query {
  knowledgeItem(id: ID!): KnowledgeItem
  knowledgeItems(filter: KnowledgeItemFilter, limit: Int, offset: Int): [KnowledgeItem!]!
  search(query: String!, limit: Int): [KnowledgeItem!]!
  semanticSearch(text: String!, limit: Int): [KnowledgeItem!]!
  similarItems(id: ID!, limit: Int): [KnowledgeItem!]!
  relatedItems(id: ID!, relationshipType: String): [KnowledgeItem!]!
}

type Mutation {
  createKnowledgeItem(input: KnowledgeItemInput!): KnowledgeItem!
  updateKnowledgeItem(id: ID!, input: KnowledgeItemInput!): KnowledgeItem!
  deleteKnowledgeItem(id: ID!): Boolean!
  createRelationship(input: RelationshipInput!): Relationship!
  deleteRelationship(id: ID!): Boolean!
}
```

### MCP Tool Specification

```json
{
  "name": "ptolemies_knowledge",
  "description": "Ptolemies Knowledge Base access for LLMs",
  "operations": [
    {
      "name": "search",
      "description": "Search the knowledge base",
      "parameters": {
        "query": "string",
        "limit": "integer?",
        "filter": "object?"
      }
    },
    {
      "name": "retrieve",
      "description": "Retrieve a knowledge item by ID",
      "parameters": {
        "id": "string"
      }
    },
    {
      "name": "store",
      "description": "Store a new knowledge item",
      "parameters": {
        "title": "string",
        "content": "string",
        "content_type": "string?",
        "tags": "array?",
        "metadata": "object?"
      }
    },
    {
      "name": "related",
      "description": "Find related knowledge items",
      "parameters": {
        "id": "string",
        "relationship_type": "string?",
        "limit": "integer?"
      }
    }
  ]
}
```

## Integration Points

### 1. MCP Integration

Ptolemies exposes functionality through MCP servers:
- **surrealdb-mcp**: Direct database operations
- **crawl4ai-mcp**: Web content ingestion
- **ptolemies-mcp**: Knowledge base specific operations

### 2. SurrealDB Integration

- Uses SurrealDB as primary storage for structured data and relationships
- Implements graph traversal for knowledge exploration
- Leverages SurrealDB's real-time capabilities for change notifications

### 3. Graphiti Integration

- Uses Graphiti for knowledge graph visualization
- Implements custom graph layouts for knowledge exploration
- Provides interactive graph navigation

### 4. Vector Database Integration

- Stores vector embeddings for semantic search
- Implements nearest-neighbor search algorithms
- Optimizes vector storage for performance

### 5. Agent Framework Integration

- Provides tools for agent access to knowledge
- Implements context-aware knowledge retrieval
- Supports knowledge updates from agent interactions

## Security Requirements

1. **Authentication and Authorization**
   - OAuth2 authentication for API access
   - Role-based access control for knowledge items
   - Fine-grained permissions for operations
   - API key management for service access

2. **Data Protection**
   - Encryption at rest for sensitive content
   - TLS encryption for all API communications
   - PII detection and handling mechanisms
   - Secure deletion capabilities

3. **Audit and Compliance**
   - Comprehensive audit logging
   - Access and modification tracking
   - Compliance with data retention policies
   - Regular security assessments

## Performance Requirements

1. **Response Time**
   - Search operations: < 200ms (p95)
   - Item retrieval: < 100ms (p95)
   - Batch operations: < 500ms (p95)
   - Vector similarity search: < 300ms (p95)

2. **Throughput**
   - Support 100+ concurrent users
   - Handle 1000+ requests per minute
   - Process 100+ documents per minute during ingestion
   - Support 1M+ knowledge items total

3. **Resource Utilization**
   - Optimized memory usage for vector operations
   - Efficient disk I/O patterns for database access
   - Parallelized processing for batch operations
   - Caching for frequently accessed content

## Scalability Requirements

1. **Horizontal Scaling**
   - Support for distributed deployment
   - Stateless API services for easy scaling
   - Partitioned data storage for growing content
   - Load balancing for API requests

2. **Vertical Scaling**
   - Memory-optimized instance options for vector operations
   - CPU-optimized options for embedding generation
   - Storage-optimized options for content heavy deployments
   - GPU support for embedding generation

3. **Operational Scaling**
   - Automated backup and recovery
   - Monitoring and alerting infrastructure
   - Zero-downtime updates and migrations
   - Scheduled maintenance procedures

## Deployment Architecture

### Development Environment

```
┌─────────────────────────────────────────────────────────────┐
│                  Development Environment                    │
├──────────────┬──────────────┬───────────────┬──────────────┤
│              │              │               │              │
│ API Services │  SurrealDB   │ Vector Store  │  File Store  │
│  (local)     │  (local)     │  (local)      │  (local)     │
│              │              │               │              │
└──────────────┴──────────────┴───────────────┴──────────────┘
```

### Production Environment

```
┌───────────────────────────────────────────────────────────────────────┐
│                       Production Environment                           │
├────────────────┬────────────────────────────┬────────────────────────┤
│                │                            │                        │
│  Load Balancer │                            │                        │
│                │                            │                        │
├────────────────┘                            │                        │
│                                             │                        │
│  ┌─────────────┐ ┌─────────────┐           │    ┌──────────────┐    │
│  │ API Service │ │ API Service │           │    │              │    │
│  │  Instance 1 │ │  Instance 2 │           │    │  SurrealDB   │    │
│  └─────────────┘ └─────────────┘           │    │   Cluster    │    │
│                                             │    │              │    │
│  ┌─────────────┐ ┌─────────────┐           │    └──────────────┘    │
│  │  Embedding  │ │  Embedding  │           │                        │
│  │  Service 1  │ │  Service 2  │           │    ┌──────────────┐    │
│  └─────────────┘ └─────────────┘           │    │              │    │
│                                             │    │ Vector Store │    │
│  ┌─────────────┐ ┌─────────────┐           │    │   Cluster    │    │
│  │    Sync     │ │   Indexing  │           │    │              │    │
│  │   Service   │ │   Service   │           │    └──────────────┘    │
│  └─────────────┘ └─────────────┘           │                        │
│                                             │    ┌──────────────┐    │
│                                             │    │              │    │
│                                             │    │  File Store  │    │
│                                             │    │              │    │
│                                             │    └──────────────┘    │
└─────────────────────────────────────────────┴────────────────────────┘
```