// Neo4j Browser Import Commands for Ptolemies Knowledge Base
// ===========================================================
// Copy and paste these commands into your Neo4j Browser at http://localhost:7475
// Make sure you're connected to your devqai project

// 1. CREATE CONSTRAINTS AND INDEXES
// ================================
CREATE CONSTRAINT source_name_unique IF NOT EXISTS 
FOR (s:Source) REQUIRE s.name IS UNIQUE;

CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS 
FOR (c:Chunk) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT topic_name_unique IF NOT EXISTS 
FOR (t:Topic) REQUIRE t.name IS UNIQUE;

CREATE INDEX source_url IF NOT EXISTS FOR (s:Source) ON (s.url);
CREATE INDEX chunk_quality IF NOT EXISTS FOR (c:Chunk) ON (c.quality_score);
CREATE INDEX chunk_created IF NOT EXISTS FOR (c:Chunk) ON (c.created_at);
CREATE TEXT INDEX chunk_content IF NOT EXISTS FOR (c:Chunk) ON (c.content);
CREATE INDEX topic_category IF NOT EXISTS FOR (t:Topic) ON (t.category);

// 2. CREATE FRAMEWORK NODES
// ========================
MERGE (fastapi:Framework {name: "FastAPI", type: "backend", language: "Python"})
MERGE (nextjs:Framework {name: "NextJS", type: "fullstack", language: "JavaScript"})
MERGE (surrealdb:Framework {name: "SurrealDB", type: "database", language: "Rust"})
MERGE (tailwind:Framework {name: "Tailwind CSS", type: "frontend", language: "CSS"})
MERGE (shadcn:Framework {name: "Shadcn/UI", type: "frontend", language: "TypeScript"})
MERGE (pydantic:Framework {name: "Pydantic AI", type: "backend", language: "Python"})
MERGE (logfire:Framework {name: "Logfire", type: "backend", language: "Python"})
MERGE (pygad:Framework {name: "PyGAD", type: "backend", language: "Python"})
MERGE (bokeh:Framework {name: "bokeh", type: "backend", language: "Python"})
MERGE (panel:Framework {name: "Panel", type: "backend", language: "Python"})
MERGE (wildwood:Framework {name: "Wildwood", type: "tool", language: "Various"})
MERGE (crawl4ai:Framework {name: "Crawl4AI", type: "tool", language: "Python"})
MERGE (fastmcp:Framework {name: "FastMCP", type: "tool", language: "Python"})
MERGE (animejs:Framework {name: "AnimeJS", type: "frontend", language: "JavaScript"})
MERGE (pymc:Framework {name: "PyMC", type: "backend", language: "Python"})
MERGE (circom:Framework {name: "circom", type: "tool", language: "Various"})
MERGE (claudecode:Framework {name: "Claude Code", type: "tool", language: "Various"});

// 3. CREATE TOPIC NODES
// ====================
MERGE (api:Topic {name: "API", category: "concept"})
MERGE (auth:Topic {name: "authentication", category: "concept"})
MERGE (db:Topic {name: "database", category: "concept"})
MERGE (ui:Topic {name: "user interface", category: "concept"})
MERGE (testing:Topic {name: "testing", category: "concept"})
MERGE (deployment:Topic {name: "deployment", category: "concept"})
MERGE (async:Topic {name: "async", category: "concept"})
MERGE (ml:Topic {name: "machine learning", category: "concept"})
MERGE (monitoring:Topic {name: "monitoring", category: "concept"})
MERGE (animation:Topic {name: "animation", category: "concept"})
MERGE (frontend:Topic {name: "frontend", category: "concept"})
MERGE (backend:Topic {name: "backend", category: "concept"})
MERGE (python:Topic {name: "Python", category: "language"})
MERGE (javascript:Topic {name: "JavaScript", category: "language"})
MERGE (typescript:Topic {name: "TypeScript", category: "language"})
MERGE (css:Topic {name: "CSS", category: "language"})
MERGE (rust:Topic {name: "Rust", category: "language"});

// 4. CREATE SOURCE NODES (Manual - based on our 17 sources)
// ========================================================
MERGE (s1:Source {name: "FastAPI", chunk_count: 8, avg_quality: 0.800, priority: "low", description: "FastAPI documentation source"})
MERGE (s2:Source {name: "NextJS", chunk_count: 5, avg_quality: 0.780, priority: "low", description: "NextJS documentation source"})
MERGE (s3:Source {name: "SurrealDB", chunk_count: 21, avg_quality: 0.967, priority: "medium", description: "SurrealDB documentation source"})
MERGE (s4:Source {name: "Tailwind", chunk_count: 23, avg_quality: 0.870, priority: "medium", description: "Tailwind documentation source"})
MERGE (s5:Source {name: "Shadcn", chunk_count: 22, avg_quality: 0.864, priority: "medium", description: "Shadcn documentation source"})
MERGE (s6:Source {name: "Pydantic AI", chunk_count: 9, avg_quality: 0.978, priority: "low", description: "Pydantic AI documentation source"})
MERGE (s7:Source {name: "Logfire", chunk_count: 31, avg_quality: 0.887, priority: "medium", description: "Logfire documentation source"})
MERGE (s8:Source {name: "PyGAD", chunk_count: 56, avg_quality: 0.964, priority: "high", description: "PyGAD documentation source"})
MERGE (s9:Source {name: "bokeh", chunk_count: 11, avg_quality: 0.891, priority: "medium", description: "bokeh documentation source"})
MERGE (s10:Source {name: "Panel", chunk_count: 22, avg_quality: 0.955, priority: "medium", description: "Panel documentation source"})
MERGE (s11:Source {name: "Wildwood", chunk_count: 10, avg_quality: 0.950, priority: "low", description: "Wildwood documentation source"})
MERGE (s12:Source {name: "Crawl4AI", chunk_count: 16, avg_quality: 0.956, priority: "medium", description: "Crawl4AI documentation source"})
MERGE (s13:Source {name: "FastMCP", chunk_count: 20, avg_quality: 0.950, priority: "medium", description: "FastMCP documentation source"})
MERGE (s14:Source {name: "AnimeJS", chunk_count: 1, avg_quality: 0.950, priority: "low", description: "AnimeJS documentation source"})
MERGE (s15:Source {name: "PyMC", chunk_count: 23, avg_quality: 0.948, priority: "medium", description: "PyMC documentation source"})
MERGE (s16:Source {name: "circom", chunk_count: 12, avg_quality: 0.958, priority: "medium", description: "circom documentation source"})
MERGE (s17:Source {name: "Claude Code", chunk_count: 2, avg_quality: 0.850, priority: "low", description: "Claude Code documentation source"});

// 5. CREATE SOURCE-FRAMEWORK RELATIONSHIPS
// =======================================
MATCH (s:Source {name: "FastAPI"}), (f:Framework {name: "FastAPI"})
MERGE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "minimal";

MATCH (s:Source {name: "NextJS"}), (f:Framework {name: "NextJS"})
MERGE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "minimal";

MATCH (s:Source {name: "SurrealDB"}), (f:Framework {name: "SurrealDB"})
MERGE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "partial";

MATCH (s:Source {name: "Tailwind"}), (f:Framework {name: "Tailwind CSS"})
MERGE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "partial";

MATCH (s:Source {name: "Shadcn"}), (f:Framework {name: "Shadcn/UI"})
MERGE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "partial";

MATCH (s:Source {name: "Pydantic AI"}), (f:Framework {name: "Pydantic AI"})
MERGE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "minimal";

MATCH (s:Source {name: "Logfire"}), (f:Framework {name: "Logfire"})
MERGE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "partial";

MATCH (s:Source {name: "PyGAD"}), (f:Framework {name: "PyGAD"})
MERGE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "complete";

MATCH (s:Source {name: "bokeh"}), (f:Framework {name: "bokeh"})
MERGE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "minimal";

MATCH (s:Source {name: "Panel"}), (f:Framework {name: "Panel"})
MERGE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "partial";

MATCH (s:Source {name: "Wildwood"}), (f:Framework {name: "Wildwood"})
MERGE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "minimal";

MATCH (s:Source {name: "Crawl4AI"}), (f:Framework {name: "Crawl4AI"})
MERGE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "partial";

MATCH (s:Source {name: "FastMCP"}), (f:Framework {name: "FastMCP"})
MERGE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "partial";

MATCH (s:Source {name: "AnimeJS"}), (f:Framework {name: "AnimeJS"})
MERGE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "minimal";

MATCH (s:Source {name: "PyMC"}), (f:Framework {name: "PyMC"})
MERGE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "partial";

MATCH (s:Source {name: "circom"}), (f:Framework {name: "circom"})
MERGE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "partial";

MATCH (s:Source {name: "Claude Code"}), (f:Framework {name: "Claude Code"})
MERGE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "minimal";

// 6. CREATE FRAMEWORK INTEGRATIONS
// ===============================
MATCH (f1:Framework {name: "FastAPI"}), (f2:Framework {name: "Pydantic AI"})
MERGE (f1)-[r:INTEGRATES_WITH]->(f2)
SET r.integration_type = "native";

MATCH (f1:Framework {name: "FastAPI"}), (f2:Framework {name: "Logfire"})
MERGE (f1)-[r:INTEGRATES_WITH]->(f2)
SET r.integration_type = "native";

MATCH (f1:Framework {name: "NextJS"}), (f2:Framework {name: "Tailwind CSS"})
MERGE (f1)-[r:INTEGRATES_WITH]->(f2)
SET r.integration_type = "native";

MATCH (f1:Framework {name: "NextJS"}), (f2:Framework {name: "Shadcn/UI"})
MERGE (f1)-[r:INTEGRATES_WITH]->(f2)
SET r.integration_type = "plugin";

MATCH (f1:Framework {name: "FastAPI"}), (f2:Framework {name: "SurrealDB"})
MERGE (f1)-[r:INTEGRATES_WITH]->(f2)
SET r.integration_type = "adapter";

// 7. CREATE TOPIC RELATIONSHIPS
// ============================
MATCH (t1:Topic {name: "API"}), (t2:Topic {name: "authentication"})
MERGE (t1)-[r:RELATED_TO]->(t2)
SET r.relationship_type = "sibling";

MATCH (t1:Topic {name: "authentication"}), (t2:Topic {name: "database"})
MERGE (t1)-[r:RELATED_TO]->(t2)
SET r.relationship_type = "prerequisite";

MATCH (t1:Topic {name: "user interface"}), (t2:Topic {name: "API"})
MERGE (t1)-[r:RELATED_TO]->(t2)
SET r.relationship_type = "sibling";

MATCH (t1:Topic {name: "testing"}), (t2:Topic {name: "deployment"})
MERGE (t1)-[r:RELATED_TO]->(t2)
SET r.relationship_type = "sibling";

MATCH (t1:Topic {name: "async"}), (t2:Topic {name: "API"})
MERGE (t1)-[r:RELATED_TO]->(t2)
SET r.relationship_type = "parent";

MATCH (t1:Topic {name: "machine learning"}), (t2:Topic {name: "database"})
MERGE (t1)-[r:RELATED_TO]->(t2)
SET r.relationship_type = "sibling";

MATCH (t1:Topic {name: "monitoring"}), (t2:Topic {name: "deployment"})
MERGE (t1)-[r:RELATED_TO]->(t2)
SET r.relationship_type = "sibling";

// 8. VERIFICATION QUERIES
// ======================
// Run these to verify the import worked:

// Count all nodes by type
MATCH (n)
RETURN labels(n)[0] as NodeType, COUNT(n) as Count
ORDER BY Count DESC;

// Show source distribution
MATCH (s:Source)
RETURN s.name, s.chunk_count, s.avg_quality, s.priority
ORDER BY s.chunk_count DESC;

// Show framework integrations
MATCH (f1:Framework)-[r:INTEGRATES_WITH]->(f2:Framework)
RETURN f1.name, r.integration_type, f2.name
ORDER BY f1.name;

// Show documentation coverage
MATCH (f:Framework)<-[:DOCUMENTS]-(s:Source)
RETURN f.name, f.type, f.language, COLLECT(s.name) as sources
ORDER BY SIZE(sources) DESC;

// ============================================================
// NOTE: This creates the graph structure without chunk content
// The 292 individual chunks would need to be imported separately
// due to their large size and complex data structure.
// ============================================================