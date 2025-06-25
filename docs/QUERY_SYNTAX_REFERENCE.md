# Ptolemies Query Syntax Reference

## 📚 Overview

This document provides actual query syntax and example results for accessing the 784-page Ptolemies knowledge base through SurrealDB, Neo4j, and MCP interfaces.

---

## 🔍 SurrealDB Vector Search Queries

### 1. Basic Semantic Search

**Query:**
```sql
-- Find documents similar to a query using vector embeddings
SELECT *,
       vector::similarity::cosine(embedding, $query_embedding) AS similarity
FROM document_chunks
WHERE vector::similarity::cosine(embedding, $query_embedding) > 0.7
ORDER BY similarity DESC
LIMIT 5;
```

**Example Result:**
```json
[
  {
    "id": "document_chunks:fastapi_auth_42",
    "source_name": "FastAPI",
    "source_url": "https://fastapi.tiangolo.com/tutorial/security/",
    "title": "FastAPI Security and Authentication",
    "content": "FastAPI provides several tools to handle security...",
    "chunk_index": 3,
    "total_chunks": 12,
    "quality_score": 0.95,
    "topics": ["FastAPI", "Authentication", "Security", "JWT"],
    "embedding": [...1536 dimensions...],
    "similarity": 0.912,
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

### 2. Filtered Search by Source

**Query:**
```sql
-- Search within specific documentation sources
SELECT id, title, source_name, quality_score,
       vector::similarity::cosine(embedding, $query_embedding) AS similarity
FROM document_chunks
WHERE source_name IN ['FastAPI', 'Python', 'Authentication']
  AND quality_score >= 0.8
  AND vector::similarity::cosine(embedding, $query_embedding) > 0.75
ORDER BY similarity DESC
LIMIT 10;
```

**Example Result:**
```json
[
  {
    "id": "document_chunks:fastapi_security_12",
    "title": "OAuth2 with Password and Bearer",
    "source_name": "FastAPI",
    "quality_score": 0.92,
    "similarity": 0.889
  },
  {
    "id": "document_chunks:python_jwt_3",
    "title": "JWT Implementation in Python",
    "source_name": "Python",
    "quality_score": 0.85,
    "similarity": 0.823
  }
]
```

### 3. Aggregate Statistics

**Query:**
```sql
-- Get knowledge base statistics
SELECT 
    count() AS total_chunks,
    count(DISTINCT source_name) AS unique_sources,
    avg(quality_score) AS avg_quality,
    min(created_at) AS earliest_doc,
    max(created_at) AS latest_doc
FROM document_chunks
GROUP ALL;
```

**Result:**
```json
{
  "total_chunks": 784,
  "unique_sources": 17,
  "avg_quality": 0.847,
  "earliest_doc": "2024-01-10T08:00:00Z",
  "latest_doc": "2024-01-20T16:30:00Z"
}
```

### 4. Topic-based Search

**Query:**
```sql
-- Find documents containing specific topics
SELECT id, title, topics, quality_score
FROM document_chunks
WHERE topics CONTAINS 'Authentication'
   OR topics CONTAINS 'JWT'
   OR topics CONTAINS 'Security'
ORDER BY quality_score DESC
LIMIT 5;
```

**Example Result:**
```json
[
  {
    "id": "document_chunks:auth_guide_15",
    "title": "Complete Authentication Guide",
    "topics": ["Authentication", "JWT", "OAuth2", "Security"],
    "quality_score": 0.96
  },
  {
    "id": "document_chunks:jwt_best_practices_8",
    "title": "JWT Security Best Practices",
    "topics": ["JWT", "Security", "Tokens", "Best Practices"],
    "quality_score": 0.93
  }
]
```

---

## 🕸️ Neo4j Graph Database Queries

### 1. Find Concept and Related Documents

**Query:**
```cypher
// Find a concept and all documents containing it
MATCH (c:Concept {name: 'Authentication'})
OPTIONAL MATCH (c)-[r:APPEARS_IN]->(d:Document)
RETURN c.name AS concept,
       c.category AS category,
       c.frequency AS frequency,
       collect({
           title: d.title,
           source: d.source_name,
           relevance: r.frequency
       }) AS documents
ORDER BY c.frequency DESC;
```

**Example Result:**
```json
{
  "concept": "Authentication",
  "category": "Security",
  "frequency": 156,
  "documents": [
    {
      "title": "FastAPI Security and Authentication",
      "source": "FastAPI",
      "relevance": 12
    },
    {
      "title": "OAuth2 Implementation Guide",
      "source": "Authentication",
      "relevance": 10
    },
    {
      "title": "JWT Best Practices",
      "source": "Security",
      "relevance": 9
    }
  ]
}
```

### 2. Find Related Concepts

**Query:**
```cypher
// Find concepts related to a starting concept
MATCH (c1:Concept {name: 'FastAPI'})-[r:RELATED_TO]-(c2:Concept)
RETURN c1.name AS from_concept,
       c2.name AS to_concept,
       r.strength AS relationship_strength,
       c2.category AS category
ORDER BY r.strength DESC
LIMIT 10;
```

**Example Result:**
```json
[
  {
    "from_concept": "FastAPI",
    "to_concept": "Python",
    "relationship_strength": 0.95,
    "category": "Language"
  },
  {
    "from_concept": "FastAPI",
    "to_concept": "API",
    "relationship_strength": 0.92,
    "category": "Technical"
  },
  {
    "from_concept": "FastAPI",
    "to_concept": "Async",
    "relationship_strength": 0.87,
    "category": "Programming"
  }
]
```

### 3. Shortest Path Between Documents

**Query:**
```cypher
// Find shortest path between two types of documents
MATCH (start:Document), (end:Document)
WHERE start.source_name = 'FastAPI' 
  AND end.source_name = 'Authentication'
  AND start.title CONTAINS 'Middleware'
  AND end.title CONTAINS 'JWT'
MATCH path = shortestPath((start)-[*1..3]-(end))
RETURN start.title AS from_doc,
       end.title AS to_doc,
       length(path) AS path_length,
       [node IN nodes(path) | 
           CASE 
               WHEN node:Document THEN 'Doc: ' + node.title
               WHEN node:Concept THEN 'Concept: ' + node.name
           END
       ] AS path
LIMIT 1;
```

**Example Result:**
```json
{
  "from_doc": "FastAPI Middleware Tutorial",
  "to_doc": "JWT Authentication Guide",
  "path_length": 2,
  "path": [
    "Doc: FastAPI Middleware Tutorial",
    "Concept: Middleware",
    "Doc: JWT Authentication Guide"
  ]
}
```

### 4. Document Similarity Network

**Query:**
```cypher
// Find documents with strong relationships
MATCH (d1:Document)-[r:RELATED_TO]-(d2:Document)
WHERE r.strength > 0.8
RETURN d1.title AS document1,
       d2.title AS document2,
       r.strength AS similarity,
       r.shared_topics AS common_topics
ORDER BY r.strength DESC
LIMIT 5;
```

**Example Result:**
```json
[
  {
    "document1": "FastAPI Security Tutorial",
    "document2": "JWT Implementation Guide",
    "similarity": 0.92,
    "common_topics": ["Authentication", "Security", "JWT"]
  },
  {
    "document1": "OAuth2 with FastAPI",
    "document2": "API Authentication Patterns",
    "similarity": 0.89,
    "common_topics": ["OAuth2", "Authentication", "API"]
  }
]
```

### 5. Graph Pattern Matching

**Query:**
```cypher
// Find triangular relationships between concepts
MATCH (c1:Concept)-[r1:RELATED_TO]->(c2:Concept)-[r2:RELATED_TO]->(c3:Concept)-[r3:RELATED_TO]->(c1)
WHERE r1.strength > 0.7 
  AND r2.strength > 0.7 
  AND r3.strength > 0.7
RETURN c1.name AS concept1,
       c2.name AS concept2,
       c3.name AS concept3,
       (r1.strength + r2.strength + r3.strength) / 3 AS avg_strength
ORDER BY avg_strength DESC
LIMIT 3;
```

**Example Result:**
```json
[
  {
    "concept1": "Authentication",
    "concept2": "JWT",
    "concept3": "Security",
    "avg_strength": 0.87
  },
  {
    "concept1": "API",
    "concept2": "FastAPI", 
    "concept3": "Middleware",
    "avg_strength": 0.82
  }
]
```

---

## 🔧 MCP (Model Context Protocol) Queries

### 1. Search Tool Query

**MCP Request:**
```json
{
  "tool": "ptolemies_search",
  "parameters": {
    "query": "How to implement FastAPI authentication middleware?",
    "search_type": "hybrid",
    "max_results": 5,
    "include_code_examples": true,
    "sources": ["FastAPI", "Authentication", "Python"]
  }
}
```

**MCP Response:**
```json
{
  "status": "success",
  "results": [
    {
      "title": "FastAPI OAuth2 Password Bearer",
      "content": "Here's a complete example of implementing authentication...",
      "code_example": "from fastapi import Depends, FastAPI...",
      "relevance_score": 0.94,
      "source": "FastAPI",
      "url": "https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/",
      "tags": ["authentication", "oauth2", "jwt", "middleware"]
    }
  ],
  "metadata": {
    "total_results": 5,
    "search_time_ms": 67.3,
    "sources_consulted": ["FastAPI", "Authentication", "Python"],
    "search_strategy": "hybrid"
  }
}
```

### 2. Concept Exploration Query

**MCP Request:**
```json
{
  "tool": "ptolemies_explore_concepts",
  "parameters": {
    "starting_concept": "Authentication",
    "exploration_depth": 2,
    "include_relationships": true,
    "max_concepts": 10
  }
}
```

**MCP Response:**
```json
{
  "concept_map": {
    "central_concept": {
      "name": "Authentication",
      "category": "Security",
      "frequency": 156
    },
    "related_concepts": [
      {
        "name": "JWT",
        "relationship": "IMPLEMENTATION_OF",
        "strength": 0.92
      },
      {
        "name": "OAuth2",
        "relationship": "STANDARD_FOR",
        "strength": 0.89
      }
    ],
    "second_level_concepts": {
      "JWT": ["Token Validation", "Claims", "Expiration"],
      "OAuth2": ["Authorization Code", "Client Credentials"]
    }
  },
  "supporting_documents": 42
}
```

### 3. Code Example Query

**MCP Request:**
```json
{
  "tool": "ptolemies_find_code",
  "parameters": {
    "technology": "FastAPI",
    "pattern": "authentication middleware",
    "language": "python",
    "include_explanation": true
  }
}
```

**MCP Response:**
```json
{
  "code_examples": [
    {
      "title": "JWT Authentication Middleware",
      "code": "from fastapi import Depends, HTTPException, status\nfrom fastapi.security import OAuth2PasswordBearer\n...",
      "explanation": "This middleware validates JWT tokens on protected routes...",
      "complexity": "intermediate",
      "dependencies": ["fastapi", "python-jose", "passlib"]
    }
  ],
  "total_found": 8
}
```

---

## 🔀 Hybrid Query Examples (Python API)

### 1. Basic Hybrid Search

**Python Code:**
```python
from src.hybrid_query_engine import HybridQueryEngine, QueryType

# Initialize engine
engine = await create_hybrid_engine()

# Perform hybrid search
results, metrics = await engine.search(
    query="FastAPI authentication best practices",
    query_type=QueryType.HYBRID_BALANCED,
    limit=10
)
```

**Result Structure:**
```python
{
    "results": [
        {
            "id": "doc_123",
            "title": "FastAPI Security Best Practices",
            "content": "Complete guide to securing FastAPI applications...",
            "source_name": "FastAPI",
            "source_url": "https://...",
            "combined_score": 0.923,
            "semantic_score": 0.891,
            "graph_score": 0.876,
            "found_via": ["semantic_search", "graph_search"],
            "topics": ["Security", "FastAPI", "Authentication"]
        }
    ],
    "metrics": {
        "total_time_ms": 78.4,
        "semantic_time_ms": 35.2,
        "graph_time_ms": 31.8,
        "fusion_time_ms": 11.4,
        "overlap_count": 3
    }
}
```

### 2. Concept Expansion Search

**Python Code:**
```python
results, metrics = await engine.search(
    query="database optimization",
    query_type=QueryType.CONCEPT_EXPANSION,
    limit=15
)
```

**Expanded Concepts:**
```python
{
    "original_query": "database optimization",
    "expanded_concepts": [
        "query optimization",
        "indexing strategies", 
        "caching",
        "connection pooling",
        "performance tuning"
    ],
    "results_per_concept": {
        "database optimization": 5,
        "query optimization": 3,
        "indexing strategies": 4,
        "caching": 2,
        "performance tuning": 1
    }
}
```

### 3. Cached Query

**Python Code:**
```python
# First query (cache miss)
result1 = await api.search_documentation(
    query="FastAPI middleware",
    max_results=5
)
print(f"Cache miss: {result1['search_time_ms']}ms")

# Second query (cache hit)
result2 = await api.search_documentation(
    query="FastAPI middleware",
    max_results=5
)
print(f"Cache hit: {result2['search_time_ms']}ms")
```

**Performance Comparison:**
```
Cache miss: 82.3ms
Cache hit: 0.8ms
Improvement: 102.9x faster
```

---

## 📊 Query Performance Summary

| Query Type | Database | Average Time | Result Count |
|------------|----------|--------------|--------------|
| Vector Similarity | SurrealDB | 20-50ms | 10-50 results |
| Graph Traversal | Neo4j | 15-40ms | Variable |
| Concept Search | Neo4j | 25-35ms | 5-20 concepts |
| Hybrid Search | Combined | 50-100ms | 10-20 results |
| Cached Query | Redis | <1ms | Same as original |

---

## 🔑 Key Takeaways

1. **SurrealDB**: Best for semantic similarity searches using vector embeddings
2. **Neo4j**: Best for exploring relationships and concept connections
3. **MCP**: Provides unified interface for tool-based access
4. **Hybrid Engine**: Combines all sources for comprehensive results
5. **Cache Layer**: Provides sub-millisecond access for repeated queries

The 784-page Ptolemies knowledge base can be queried through multiple interfaces, each optimized for different use cases while maintaining sub-100ms performance targets.