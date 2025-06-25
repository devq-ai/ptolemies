#!/usr/bin/env python3
"""
Manual Neo4j Completion Script
Provides commands for manual execution in Neo4j Browser to complete the knowledge graph
"""

def generate_topic_creation_commands():
    """Generate individual topic creation commands."""
    topics = [
        ("API", "concept"),
        ("authentication", "concept"),
        ("database", "concept"),
        ("user interface", "concept"),
        ("testing", "concept"),
        ("deployment", "concept"),
        ("async", "concept"),
        ("machine learning", "concept"),
        ("monitoring", "concept"),
        ("animation", "concept"),
        ("frontend", "concept"),
        ("backend", "concept"),
        ("Python", "language"),
        ("JavaScript", "language"),
        ("TypeScript", "language"),
        ("CSS", "language"),
        ("Rust", "language")
    ]
    
    print("// CREATE TOPIC NODES - Execute these one by one in Neo4j Browser")
    print("// ================================================================")
    for name, category in topics:
        print(f'CREATE (:{name.replace(" ", "_").lower()}:Topic {{name: "{name}", category: "{category}"}});')
    print()

def generate_source_creation_commands():
    """Generate source creation commands."""
    sources = [
        ("FastAPI", 8, 0.800, "low"),
        ("NextJS", 5, 0.780, "low"),
        ("SurrealDB", 21, 0.967, "medium"),
        ("Tailwind", 23, 0.870, "medium"),
        ("Shadcn", 22, 0.864, "medium"),
        ("Pydantic AI", 9, 0.978, "low"),
        ("Logfire", 31, 0.887, "medium"),
        ("PyGAD", 56, 0.964, "high"),
        ("bokeh", 11, 0.891, "medium"),
        ("Panel", 22, 0.955, "medium"),
        ("Wildwood", 10, 0.950, "low"),
        ("Crawl4AI", 16, 0.956, "medium"),
        ("FastMCP", 20, 0.950, "medium"),
        ("AnimeJS", 1, 0.950, "low"),
        ("PyMC", 23, 0.948, "medium"),
        ("circom", 12, 0.958, "medium"),
        ("Claude Code", 2, 0.850, "low")
    ]
    
    print("// CREATE SOURCE NODES - Execute these one by one in Neo4j Browser")
    print("// ================================================================")
    for name, chunks, quality, priority in sources:
        var_name = name.replace(" ", "_").replace("/", "_").lower()
        print(f'CREATE (s_{var_name}:Source {{name: "{name}", chunk_count: {chunks}, avg_quality: {quality}, priority: "{priority}", description: "{name} documentation source"}});')
    print()

def generate_relationship_commands():
    """Generate relationship creation commands."""
    print("// CREATE SOURCE-FRAMEWORK RELATIONSHIPS")
    print("// ====================================")
    
    source_framework_map = [
        ("FastAPI", "FastAPI", "minimal"),
        ("NextJS", "NextJS", "minimal"),
        ("SurrealDB", "SurrealDB", "partial"),
        ("Tailwind", "Tailwind CSS", "partial"),
        ("Shadcn", "Shadcn/UI", "partial"),
        ("Pydantic AI", "Pydantic AI", "minimal"),
        ("Logfire", "Logfire", "partial"),
        ("PyGAD", "PyGAD", "complete"),
        ("bokeh", "bokeh", "minimal"),
        ("Panel", "Panel", "partial"),
        ("Wildwood", "Wildwood", "minimal"),
        ("Crawl4AI", "Crawl4AI", "partial"),
        ("FastMCP", "FastMCP", "partial"),
        ("AnimeJS", "AnimeJS", "minimal"),
        ("PyMC", "PyMC", "partial"),
        ("circom", "circom", "partial"),
        ("Claude Code", "Claude Code", "minimal")
    ]
    
    for source, framework, coverage in source_framework_map:
        print(f'MATCH (s:Source {{name: "{source}"}}), (f:Framework {{name: "{framework}"}})')
        print(f'CREATE (s)-[r:DOCUMENTS]->(f)')
        print(f'SET r.coverage = "{coverage}";')
        print()
    
    print("// CREATE FRAMEWORK INTEGRATIONS")
    print("// =============================")
    
    integrations = [
        ("FastAPI", "Pydantic AI", "native"),
        ("FastAPI", "Logfire", "native"),
        ("NextJS", "Tailwind CSS", "native"),
        ("NextJS", "Shadcn/UI", "plugin"),
        ("FastAPI", "SurrealDB", "adapter")
    ]
    
    for f1, f2, int_type in integrations:
        print(f'MATCH (f1:Framework {{name: "{f1}"}}), (f2:Framework {{name: "{f2}"}})')
        print(f'CREATE (f1)-[r:INTEGRATES_WITH]->(f2)')
        print(f'SET r.integration_type = "{int_type}";')
        print()
    
    print("// CREATE TOPIC RELATIONSHIPS")
    print("// ==========================")
    
    topic_relationships = [
        ("API", "authentication", "sibling"),
        ("authentication", "database", "prerequisite"),
        ("user interface", "API", "sibling"),
        ("testing", "deployment", "sibling"),
        ("async", "API", "parent"),
        ("machine learning", "database", "sibling"),
        ("monitoring", "deployment", "sibling")
    ]
    
    for t1, t2, rel_type in topic_relationships:
        print(f'MATCH (t1:Topic {{name: "{t1}"}}), (t2:Topic {{name: "{t2}"}})')
        print(f'CREATE (t1)-[r:RELATED_TO]->(t2)')
        print(f'SET r.relationship_type = "{rel_type}";')
        print()

def generate_verification_commands():
    """Generate verification commands."""
    print("// VERIFICATION QUERIES")
    print("// ===================")
    print()
    print("// 1. Count all nodes by type")
    print("MATCH (n) RETURN labels(n)[0] as NodeType, COUNT(n) as Count ORDER BY Count DESC;")
    print()
    print("// 2. Show all frameworks")
    print("MATCH (f:Framework) RETURN f.name, f.type, f.language ORDER BY f.type, f.name;")
    print()
    print("// 3. Show all sources with statistics")
    print("MATCH (s:Source) RETURN s.name, s.chunk_count, s.avg_quality, s.priority ORDER BY s.chunk_count DESC;")
    print()
    print("// 4. Show framework integrations")
    print("MATCH (f1:Framework)-[r:INTEGRATES_WITH]->(f2:Framework) RETURN f1.name, r.integration_type, f2.name;")
    print()
    print("// 5. Show documentation coverage")
    print("MATCH (f:Framework)<-[r:DOCUMENTS]-(s:Source) RETURN f.name, s.name, r.coverage;")
    print()

def main():
    """Generate complete manual Neo4j completion script."""
    print("=" * 80)
    print("PTOLEMIES KNOWLEDGE GRAPH - MANUAL COMPLETION SCRIPT")
    print("=" * 80)
    print("Copy and paste these commands into Neo4j Browser one section at a time")
    print("Browser URL: Check Neo4j Desktop for your devqai project browser URL")
    print("Credentials: neo4j:ptolemies")
    print("=" * 80)
    print()
    
    generate_topic_creation_commands()
    generate_source_creation_commands()
    generate_relationship_commands()
    generate_verification_commands()
    
    print("// FINAL STATUS CHECK")
    print("// =================")
    print("// Expected final counts:")
    print("// Framework: 17 ✅ (Already created)")
    print("// Topic: 17 (To be created)")
    print("// Source: 17 (To be created)")
    print("// Total nodes: 51")
    print("// Relationships: ~30")

if __name__ == "__main__":
    main()