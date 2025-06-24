// Vector Search Setup for Ptolemies Knowledge Graph
// =================================================
// Execute these in Neo4j Browser to enable semantic similarity search

// 1. Create vector index for semantic similarity (if supported)
// Note: This requires Neo4j 5.x with vector capabilities
CREATE VECTOR INDEX framework_similarity IF NOT EXISTS
FOR (f:Framework) ON (f.embedding)
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 384,
    `vector.similarity_function`: 'cosine'
  }
};

// 2. Create vector index for topics
CREATE VECTOR INDEX topic_similarity IF NOT EXISTS
FOR (t:Topic) ON (t.embedding)
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 384,
    `vector.similarity_function`: 'cosine'
  }
};

// 3. Create vector index for chunks (when imported)
CREATE VECTOR INDEX chunk_similarity IF NOT EXISTS
FOR (c:Chunk) ON (c.embedding)
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 384,
    `vector.similarity_function`: 'cosine'
  }
};

// 4. Full-text search indexes for content discovery
CREATE FULLTEXT INDEX framework_search IF NOT EXISTS
FOR (f:Framework) ON EACH [f.name];

CREATE FULLTEXT INDEX topic_search IF NOT EXISTS
FOR (t:Topic) ON EACH [t.name];

CREATE FULLTEXT INDEX source_search IF NOT EXISTS
FOR (s:Source) ON EACH [s.name, s.description];

// 5. Similarity queries (examples to test after vectors are added)

// Find similar frameworks by name
// CALL db.index.fulltext.queryNodes("framework_search", "API Python") 
// YIELD node, score 
// RETURN node.name, node.type, score;

// Find similar topics
// CALL db.index.fulltext.queryNodes("topic_search", "database authentication") 
// YIELD node, score 
// RETURN node.name, node.category, score;

// Vector similarity example (after embeddings are added):
// MATCH (f:Framework {name: "FastAPI"})
// CALL db.index.vector.queryNodes('framework_similarity', 5, f.embedding)
// YIELD node, score
// RETURN node.name, node.type, score;