// Ptolemies Knowledge Graph Schema for Neo4j
// This schema represents the knowledge base structure with documentation sources,
// chunks, topics, and their relationships

// ============================================
// CONSTRAINTS & INDEXES
// ============================================

// Unique constraints ensure data integrity
CREATE CONSTRAINT source_name_unique IF NOT EXISTS 
FOR (s:Source) REQUIRE s.name IS UNIQUE;

CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS 
FOR (c:Chunk) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT topic_name_unique IF NOT EXISTS 
FOR (t:Topic) REQUIRE t.name IS UNIQUE;

// Indexes for performance optimization
CREATE INDEX source_url IF NOT EXISTS FOR (s:Source) ON (s.url);
CREATE INDEX chunk_quality IF NOT EXISTS FOR (c:Chunk) ON (c.quality_score);
CREATE INDEX chunk_created IF NOT EXISTS FOR (c:Chunk) ON (c.created_at);
CREATE TEXT INDEX chunk_content IF NOT EXISTS FOR (c:Chunk) ON (c.content);
CREATE INDEX topic_category IF NOT EXISTS FOR (t:Topic) ON (t.category);

// Vector index for similarity search (requires Neo4j with vector support)
// CREATE VECTOR INDEX chunk_embedding IF NOT EXISTS
// FOR (c:Chunk) ON (c.embedding)
// OPTIONS {indexConfig: {
//   `vector.dimensions`: 1536,
//   `vector.similarity_function`: 'cosine'
// }};

// ============================================
// NODE LABELS
// ============================================

// :Source - Documentation sources (FastAPI, SurrealDB, etc.)
// Properties:
//   - name: String (unique) - e.g., "FastAPI", "SurrealDB"
//   - url: String - Base URL of the documentation
//   - chunk_count: Integer - Total chunks from this source
//   - priority: String - "high", "medium", "low"
//   - last_crawled: DateTime - When last crawled
//   - description: String - Brief description of the source

// :Chunk - Individual documentation chunks
// Properties:
//   - id: String (unique) - SurrealDB record ID
//   - title: String - Page title
//   - content: String - Chunk text content
//   - url: String - Original page URL
//   - chunk_index: Integer - Position in document
//   - total_chunks: Integer - Total chunks in document
//   - quality_score: Float - Content quality (0.0-1.0)
//   - embedding: List<Float> - 1536-dimensional vector
//   - created_at: DateTime - Creation timestamp

// :Topic - Technical topics/concepts
// Properties:
//   - name: String (unique) - e.g., "API", "database", "authentication"
//   - category: String - "framework", "library", "concept", "tool"
//   - description: String - Brief description

// :Framework - Specific framework nodes
// Properties:
//   - name: String - Framework name
//   - type: String - "frontend", "backend", "fullstack"
//   - language: String - Primary language

// ============================================
// RELATIONSHIPS
// ============================================

// (:Source)-[:HAS_CHUNK]->(:Chunk)
// Properties:
//   - crawled_at: DateTime

// (:Chunk)-[:COVERS_TOPIC]->(:Topic)
// Properties:
//   - relevance: Float - How relevant the topic is to the chunk

// (:Chunk)-[:REFERENCES]->(:Chunk)
// Properties:
//   - reference_type: String - "example", "prerequisite", "related"

// (:Topic)-[:RELATED_TO]->(:Topic)
// Properties:
//   - relationship_type: String - "parent", "sibling", "prerequisite"

// (:Source)-[:DOCUMENTS]->(:Framework)
// Properties:
//   - coverage: String - "complete", "partial", "minimal"

// (:Framework)-[:INTEGRATES_WITH]->(:Framework)
// Properties:
//   - integration_type: String - "native", "plugin", "adapter"

// ============================================
// SAMPLE DATA CREATION
// ============================================

// Create framework nodes
MERGE (fastapi:Framework {name: "FastAPI", type: "backend", language: "Python"})
MERGE (nextjs:Framework {name: "NextJS", type: "fullstack", language: "JavaScript"})
MERGE (surrealdb:Framework {name: "SurrealDB", type: "database", language: "Rust"})
MERGE (tailwind:Framework {name: "Tailwind CSS", type: "frontend", language: "CSS"})
MERGE (shadcn:Framework {name: "Shadcn/UI", type: "frontend", language: "TypeScript"})
MERGE (pydantic:Framework {name: "Pydantic AI", type: "backend", language: "Python"})
MERGE (logfire:Framework {name: "Logfire", type: "backend", language: "Python"});

// Create common topic nodes
MERGE (api:Topic {name: "API", category: "concept"})
MERGE (auth:Topic {name: "authentication", category: "concept"})
MERGE (db:Topic {name: "database", category: "concept"})
MERGE (ui:Topic {name: "user interface", category: "concept"})
MERGE (testing:Topic {name: "testing", category: "concept"})
MERGE (deployment:Topic {name: "deployment", category: "concept"})
MERGE (async:Topic {name: "async", category: "concept"})
MERGE (ml:Topic {name: "machine learning", category: "concept"})
MERGE (monitoring:Topic {name: "monitoring", category: "concept"});

// Create topic relationships
MERGE (api)-[:RELATED_TO {relationship_type: "sibling"}]->(auth)
MERGE (auth)-[:RELATED_TO {relationship_type: "prerequisite"}]->(db)
MERGE (ui)-[:RELATED_TO {relationship_type: "sibling"}]->(api)
MERGE (testing)-[:RELATED_TO {relationship_type: "sibling"}]->(deployment)
MERGE (async)-[:RELATED_TO {relationship_type: "parent"}]->(api)
MERGE (ml)-[:RELATED_TO {relationship_type: "sibling"}]->(db)
MERGE (monitoring)-[:RELATED_TO {relationship_type: "sibling"}]->(deployment);

// Create framework integrations
MERGE (fastapi)-[:INTEGRATES_WITH {integration_type: "native"}]->(pydantic)
MERGE (fastapi)-[:INTEGRATES_WITH {integration_type: "native"}]->(logfire)
MERGE (nextjs)-[:INTEGRATES_WITH {integration_type: "native"}]->(tailwind)
MERGE (nextjs)-[:INTEGRATES_WITH {integration_type: "plugin"}]->(shadcn)
MERGE (fastapi)-[:INTEGRATES_WITH {integration_type: "adapter"}]->(surrealdb);

// ============================================
// USEFUL QUERIES
// ============================================

// Find all chunks from a specific source
// MATCH (s:Source {name: "FastAPI"})-[:HAS_CHUNK]->(c:Chunk)
// RETURN c.title, c.quality_score, c.url
// ORDER BY c.quality_score DESC;

// Find chunks covering specific topics
// MATCH (c:Chunk)-[:COVERS_TOPIC]->(t:Topic {name: "authentication"})
// RETURN c.title, c.content, c.quality_score
// ORDER BY c.quality_score DESC
// LIMIT 10;

// Find related chunks through topics
// MATCH (c1:Chunk {id: $chunk_id})-[:COVERS_TOPIC]->(t:Topic)<-[:COVERS_TOPIC]-(c2:Chunk)
// WHERE c1 <> c2
// RETURN DISTINCT c2.title, c2.url, COUNT(t) as common_topics
// ORDER BY common_topics DESC
// LIMIT 5;

// Find learning path through prerequisites
// MATCH path = (t1:Topic {name: "deployment"})-[:RELATED_TO*1..3 {relationship_type: "prerequisite"}]->(t2:Topic)
// RETURN path;

// Framework documentation coverage
// MATCH (s:Source)-[:DOCUMENTS]->(f:Framework)
// RETURN f.name, COLLECT(s.name) as sources, COUNT(s) as source_count
// ORDER BY source_count DESC;