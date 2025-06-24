================================================================================
PTOLEMIES KNOWLEDGE GRAPH - MANUAL COMPLETION SCRIPT
================================================================================
Copy and paste these commands into Neo4j Browser one section at a time
Browser URL: Check Neo4j Desktop for your devqai project browser URL
Credentials: neo4j:ptolemies
================================================================================

// CREATE TOPIC NODES - Execute these one by one in Neo4j Browser
// ================================================================
CREATE (:api:Topic {name: "API", category: "concept"});
CREATE (:authentication:Topic {name: "authentication", category: "concept"});
CREATE (:database:Topic {name: "database", category: "concept"});
CREATE (:user_interface:Topic {name: "user interface", category: "concept"});
CREATE (:testing:Topic {name: "testing", category: "concept"});
CREATE (:deployment:Topic {name: "deployment", category: "concept"});
CREATE (:async:Topic {name: "async", category: "concept"});
CREATE (:machine_learning:Topic {name: "machine learning", category: "concept"});
CREATE (:monitoring:Topic {name: "monitoring", category: "concept"});
CREATE (:animation:Topic {name: "animation", category: "concept"});
CREATE (:frontend:Topic {name: "frontend", category: "concept"});
CREATE (:backend:Topic {name: "backend", category: "concept"});
CREATE (:python:Topic {name: "Python", category: "language"});
CREATE (:javascript:Topic {name: "JavaScript", category: "language"});
CREATE (:typescript:Topic {name: "TypeScript", category: "language"});
CREATE (:css:Topic {name: "CSS", category: "language"});
CREATE (:rust:Topic {name: "Rust", category: "language"});

// CREATE SOURCE NODES - Execute these one by one in Neo4j Browser
// ================================================================
CREATE (s_fastapi:Source {name: "FastAPI", chunk_count: 8, avg_quality: 0.8, priority: "low", description: "FastAPI documentation source"});
CREATE (s_nextjs:Source {name: "NextJS", chunk_count: 5, avg_quality: 0.78, priority: "low", description: "NextJS documentation source"});
CREATE (s_surrealdb:Source {name: "SurrealDB", chunk_count: 21, avg_quality: 0.967, priority: "medium", description: "SurrealDB documentation source"});
CREATE (s_tailwind:Source {name: "Tailwind", chunk_count: 23, avg_quality: 0.87, priority: "medium", description: "Tailwind documentation source"});
CREATE (s_shadcn:Source {name: "Shadcn", chunk_count: 22, avg_quality: 0.864, priority: "medium", description: "Shadcn documentation source"});
CREATE (s_pydantic_ai:Source {name: "Pydantic AI", chunk_count: 9, avg_quality: 0.978, priority: "low", description: "Pydantic AI documentation source"});
CREATE (s_logfire:Source {name: "Logfire", chunk_count: 31, avg_quality: 0.887, priority: "medium", description: "Logfire documentation source"});
CREATE (s_pygad:Source {name: "PyGAD", chunk_count: 56, avg_quality: 0.964, priority: "high", description: "PyGAD documentation source"});
CREATE (s_bokeh:Source {name: "bokeh", chunk_count: 11, avg_quality: 0.891, priority: "medium", description: "bokeh documentation source"});
CREATE (s_panel:Source {name: "Panel", chunk_count: 22, avg_quality: 0.955, priority: "medium", description: "Panel documentation source"});
CREATE (s_wildwood:Source {name: "Wildwood", chunk_count: 10, avg_quality: 0.95, priority: "low", description: "Wildwood documentation source"});
CREATE (s_crawl4ai:Source {name: "Crawl4AI", chunk_count: 16, avg_quality: 0.956, priority: "medium", description: "Crawl4AI documentation source"});
CREATE (s_fastmcp:Source {name: "FastMCP", chunk_count: 20, avg_quality: 0.95, priority: "medium", description: "FastMCP documentation source"});
CREATE (s_animejs:Source {name: "AnimeJS", chunk_count: 1, avg_quality: 0.95, priority: "low", description: "AnimeJS documentation source"});
CREATE (s_pymc:Source {name: "PyMC", chunk_count: 23, avg_quality: 0.948, priority: "medium", description: "PyMC documentation source"});
CREATE (s_circom:Source {name: "circom", chunk_count: 12, avg_quality: 0.958, priority: "medium", description: "circom documentation source"});
CREATE (s_claude_code:Source {name: "Claude Code", chunk_count: 2, avg_quality: 0.85, priority: "low", description: "Claude Code documentation source"});

// CREATE SOURCE-FRAMEWORK RELATIONSHIPS
// ====================================
MATCH (s:Source {name: "FastAPI"}), (f:Framework {name: "FastAPI"})
CREATE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "minimal";

MATCH (s:Source {name: "NextJS"}), (f:Framework {name: "NextJS"})
CREATE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "minimal";

MATCH (s:Source {name: "SurrealDB"}), (f:Framework {name: "SurrealDB"})
CREATE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "partial";

MATCH (s:Source {name: "Tailwind"}), (f:Framework {name: "Tailwind CSS"})
CREATE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "partial";

MATCH (s:Source {name: "Shadcn"}), (f:Framework {name: "Shadcn/UI"})
CREATE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "partial";

MATCH (s:Source {name: "Pydantic AI"}), (f:Framework {name: "Pydantic AI"})
CREATE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "minimal";

MATCH (s:Source {name: "Logfire"}), (f:Framework {name: "Logfire"})
CREATE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "partial";

MATCH (s:Source {name: "PyGAD"}), (f:Framework {name: "PyGAD"})
CREATE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "complete";

MATCH (s:Source {name: "bokeh"}), (f:Framework {name: "bokeh"})
CREATE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "minimal";

MATCH (s:Source {name: "Panel"}), (f:Framework {name: "Panel"})
CREATE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "partial";

MATCH (s:Source {name: "Wildwood"}), (f:Framework {name: "Wildwood"})
CREATE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "minimal";

MATCH (s:Source {name: "Crawl4AI"}), (f:Framework {name: "Crawl4AI"})
CREATE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "partial";

MATCH (s:Source {name: "FastMCP"}), (f:Framework {name: "FastMCP"})
CREATE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "partial";

MATCH (s:Source {name: "AnimeJS"}), (f:Framework {name: "AnimeJS"})
CREATE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "minimal";

MATCH (s:Source {name: "PyMC"}), (f:Framework {name: "PyMC"})
CREATE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "partial";

MATCH (s:Source {name: "circom"}), (f:Framework {name: "circom"})
CREATE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "partial";

MATCH (s:Source {name: "Claude Code"}), (f:Framework {name: "Claude Code"})
CREATE (s)-[r:DOCUMENTS]->(f)
SET r.coverage = "minimal";

// CREATE FRAMEWORK INTEGRATIONS
// =============================
MATCH (f1:Framework {name: "FastAPI"}), (f2:Framework {name: "Pydantic AI"})
CREATE (f1)-[r:INTEGRATES_WITH]->(f2)
SET r.integration_type = "native";

MATCH (f1:Framework {name: "FastAPI"}), (f2:Framework {name: "Logfire"})
CREATE (f1)-[r:INTEGRATES_WITH]->(f2)
SET r.integration_type = "native";

MATCH (f1:Framework {name: "NextJS"}), (f2:Framework {name: "Tailwind CSS"})
CREATE (f1)-[r:INTEGRATES_WITH]->(f2)
SET r.integration_type = "native";

MATCH (f1:Framework {name: "NextJS"}), (f2:Framework {name: "Shadcn/UI"})
CREATE (f1)-[r:INTEGRATES_WITH]->(f2)
SET r.integration_type = "plugin";

MATCH (f1:Framework {name: "FastAPI"}), (f2:Framework {name: "SurrealDB"})
CREATE (f1)-[r:INTEGRATES_WITH]->(f2)
SET r.integration_type = "adapter";

// CREATE TOPIC RELATIONSHIPS
// ==========================
MATCH (t1:Topic {name: "API"}), (t2:Topic {name: "authentication"})
CREATE (t1)-[r:RELATED_TO]->(t2)
SET r.relationship_type = "sibling";

MATCH (t1:Topic {name: "authentication"}), (t2:Topic {name: "database"})
CREATE (t1)-[r:RELATED_TO]->(t2)
SET r.relationship_type = "prerequisite";

MATCH (t1:Topic {name: "user interface"}), (t2:Topic {name: "API"})
CREATE (t1)-[r:RELATED_TO]->(t2)
SET r.relationship_type = "sibling";

MATCH (t1:Topic {name: "testing"}), (t2:Topic {name: "deployment"})
CREATE (t1)-[r:RELATED_TO]->(t2)
SET r.relationship_type = "sibling";

MATCH (t1:Topic {name: "async"}), (t2:Topic {name: "API"})
CREATE (t1)-[r:RELATED_TO]->(t2)
SET r.relationship_type = "parent";

MATCH (t1:Topic {name: "machine learning"}), (t2:Topic {name: "database"})
CREATE (t1)-[r:RELATED_TO]->(t2)
SET r.relationship_type = "sibling";

MATCH (t1:Topic {name: "monitoring"}), (t2:Topic {name: "deployment"})
CREATE (t1)-[r:RELATED_TO]->(t2)
SET r.relationship_type = "sibling";

// VERIFICATION QUERIES
// ===================

// 1. Count all nodes by type
MATCH (n) RETURN labels(n)[0] as NodeType, COUNT(n) as Count ORDER BY Count DESC;

// 2. Show all frameworks
MATCH (f:Framework) RETURN f.name, f.type, f.language ORDER BY f.type, f.name;

// 3. Show all sources with statistics
MATCH (s:Source) RETURN s.name, s.chunk_count, s.avg_quality, s.priority ORDER BY s.chunk_count DESC;

// 4. Show framework integrations
MATCH (f1:Framework)-[r:INTEGRATES_WITH]->(f2:Framework) RETURN f1.name, r.integration_type, f2.name;

// 5. Show documentation coverage
MATCH (f:Framework)<-[r:DOCUMENTS]-(s:Source) RETURN f.name, s.name, r.coverage;

// FINAL STATUS CHECK
// =================
// Expected final counts:
// Framework: 17 ✅ (Already created)
// Topic: 17 (To be created)
// Source: 17 (To be created)
// Total nodes: 51
// Relationships: ~30
