// Useful Neo4j Queries for Ptolemies Knowledge Graph
// ================================================

// 1. BASIC EXPLORATION QUERIES
// ---------------------------

// Count all nodes by label
MATCH (n)
RETURN labels(n)[0] as Label, COUNT(n) as Count
ORDER BY Count DESC;

// View source distribution
MATCH (s:Source)
RETURN s.name, s.chunk_count, s.avg_quality, s.priority
ORDER BY s.chunk_count DESC;

// Top topics across all chunks
MATCH (c:Chunk)-[:COVERS_TOPIC]->(t:Topic)
RETURN t.name, t.category, COUNT(c) as mentions
ORDER BY mentions DESC
LIMIT 20;

// Framework documentation coverage
MATCH (f:Framework)<-[:DOCUMENTS]-(s:Source)
RETURN f.name, f.type, f.language, COLLECT(s.name) as sources
ORDER BY SIZE(sources) DESC;


// 2. CONTENT DISCOVERY QUERIES
// ---------------------------

// Find high-quality chunks about a specific topic
MATCH (c:Chunk)-[:COVERS_TOPIC]->(t:Topic {name: "authentication"})
WHERE c.quality_score > 0.8
RETURN c.title, c.content, c.quality_score, c.url
ORDER BY c.quality_score DESC
LIMIT 10;

// Find chunks from specific source about a topic
MATCH (s:Source {name: "FastAPI"})-[:HAS_CHUNK]->(c:Chunk)-[:COVERS_TOPIC]->(t:Topic {name: "API"})
RETURN c.title, c.content, c.quality_score
ORDER BY c.quality_score DESC;

// Search chunks by content (requires full-text index)
CALL db.index.fulltext.queryNodes("chunk_content", "async authentication")
YIELD node, score
RETURN node.title, node.content, score
ORDER BY score DESC
LIMIT 10;


// 3. RELATIONSHIP EXPLORATION
// ---------------------------

// Find related topics through shared chunks
MATCH (t1:Topic {name: "API"})-[:COVERS_TOPIC]-(c:Chunk)-[:COVERS_TOPIC]-(t2:Topic)
WHERE t1 <> t2
RETURN t2.name, COUNT(DISTINCT c) as shared_chunks
ORDER BY shared_chunks DESC
LIMIT 10;

// Learning path - find prerequisite topics
MATCH path = (t1:Topic)-[:RELATED_TO*1..3 {relationship_type: "prerequisite"}]->(t2:Topic)
WHERE t1.name = "deployment"
RETURN path;

// Framework integration network
MATCH (f1:Framework)-[r:INTEGRATES_WITH]->(f2:Framework)
RETURN f1.name, r.integration_type, f2.name
ORDER BY f1.name;

// Cross-source topic coverage
MATCH (s:Source)-[:HAS_CHUNK]->(c:Chunk)-[:COVERS_TOPIC]->(t:Topic)
RETURN t.name, COLLECT(DISTINCT s.name) as sources, COUNT(DISTINCT s) as source_count
ORDER BY source_count DESC
LIMIT 15;


// 4. SIMILARITY & RECOMMENDATIONS
// ---------------------------

// Find similar chunks based on shared topics
MATCH (c1:Chunk {id: "document_chunks:xyz"})-[:COVERS_TOPIC]->(t:Topic)<-[:COVERS_TOPIC]-(c2:Chunk)
WHERE c1 <> c2
WITH c2, COUNT(t) as common_topics
RETURN c2.title, c2.url, common_topics
ORDER BY common_topics DESC
LIMIT 5;

// Recommend chunks based on topic interests
MATCH (t:Topic)<-[:COVERS_TOPIC]-(c:Chunk)
WHERE t.name IN ["FastAPI", "async", "API"]
WITH c, COUNT(DISTINCT t) as topic_matches
WHERE topic_matches >= 2
RETURN c.title, c.content, c.quality_score, topic_matches
ORDER BY topic_matches DESC, c.quality_score DESC
LIMIT 10;

// Find documentation gaps
MATCH (t:Topic)
OPTIONAL MATCH (t)<-[:COVERS_TOPIC]-(c:Chunk)
WITH t, COUNT(c) as coverage
WHERE coverage < 3
RETURN t.name, t.category, coverage
ORDER BY coverage ASC;


// 5. ANALYTICS QUERIES
// -----------------------

// Source quality distribution
MATCH (s:Source)-[:HAS_CHUNK]->(c:Chunk)
RETURN s.name, 
       AVG(c.quality_score) as avg_quality,
       MIN(c.quality_score) as min_quality,
       MAX(c.quality_score) as max_quality,
       COUNT(c) as total_chunks
ORDER BY avg_quality DESC;

// Topic network density
MATCH (t:Topic)
OPTIONAL MATCH (t)-[r:RELATED_TO]-(other:Topic)
RETURN t.name, COUNT(r) as connections
ORDER BY connections DESC;

// Content freshness by source
MATCH (s:Source)-[:HAS_CHUNK]->(c:Chunk)
RETURN s.name, 
       MAX(c.created_at) as latest_chunk,
       MIN(c.created_at) as oldest_chunk,
       COUNT(c) as total_chunks
ORDER BY latest_chunk DESC;


// 6. DATA QUALITY CHECKS
// ---------------------

// Find chunks without topics
MATCH (c:Chunk)
WHERE NOT EXISTS((c)-[:COVERS_TOPIC]->(:Topic))
RETURN c.id, c.title, c.source_name
LIMIT 20;

// Find orphaned topics
MATCH (t:Topic)
WHERE NOT EXISTS((t)<-[:COVERS_TOPIC]-(:Chunk))
RETURN t.name, t.category;

// Check for duplicate sources
MATCH (s:Source)
WITH s.name as name, COLLECT(s) as sources
WHERE SIZE(sources) > 1
RETURN name, SIZE(sources) as duplicates;

// Verify chunk counts
MATCH (s:Source)-[:HAS_CHUNK]->(c:Chunk)
WITH s, COUNT(c) as actual_count
WHERE s.chunk_count <> actual_count
RETURN s.name, s.chunk_count as reported, actual_count;


// 7. GRAPH VISUALIZATION QUERIES
// -----------------------------

// Topic network for visualization
MATCH (t1:Topic)-[r:RELATED_TO]-(t2:Topic)
RETURN t1, r, t2
LIMIT 50;

// Source-Framework-Topic overview
MATCH (s:Source)-[:DOCUMENTS]->(f:Framework)
MATCH (s)-[:HAS_CHUNK]->(c:Chunk)-[:COVERS_TOPIC]->(t:Topic)
WITH s, f, COLLECT(DISTINCT t) as topics
RETURN s, f, topics[0..5] as sample_topics;

// Framework integration graph
MATCH (f:Framework)-[r:INTEGRATES_WITH]-(other:Framework)
RETURN f, r, other;


// 8. ADMIN & MAINTENANCE
// ---------------------

// Database statistics
CALL apoc.meta.stats()
YIELD nodeCount, relCount, labelCount, relTypeCount
RETURN nodeCount, relCount, labelCount, relTypeCount;

// Index status
SHOW INDEXES;

// Constraint status
SHOW CONSTRAINTS;

// Clear all data (USE WITH CAUTION!)
// MATCH (n) DETACH DELETE n;

// Export graph schema
CALL apoc.meta.schema()
YIELD value
RETURN value;