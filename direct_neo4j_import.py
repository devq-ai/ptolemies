#!/usr/bin/env python3
"""
Direct Neo4j Import using Python Driver
Bypasses the JVM issue by using pure Python Neo4j driver
"""

from neo4j import GraphDatabase
import logging

class DirectNeo4jImporter:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="ptolemies"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        
    def close(self):
        self.driver.close()
        
    def create_topics(self):
        """Create all topic nodes."""
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
        
        with self.driver.session() as session:
            for name, category in topics:
                try:
                    result = session.run(
                        "CREATE (t:Topic {name: $name, category: $category}) RETURN t.name as created",
                        name=name, category=category
                    )
                    record = result.single()
                    print(f"✅ Created Topic: {record['created']}")
                except Exception as e:
                    print(f"❌ Failed to create Topic {name}: {e}")
                    
    def create_sources(self):
        """Create all source nodes."""
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
        
        with self.driver.session() as session:
            for name, chunks, quality, priority in sources:
                try:
                    result = session.run(
                        """CREATE (s:Source {
                            name: $name, 
                            chunk_count: $chunks, 
                            avg_quality: $quality, 
                            priority: $priority, 
                            description: $description
                        }) RETURN s.name as created""",
                        name=name, chunks=chunks, quality=quality, priority=priority,
                        description=f"{name} documentation source"
                    )
                    record = result.single()
                    print(f"✅ Created Source: {record['created']}")
                except Exception as e:
                    print(f"❌ Failed to create Source {name}: {e}")
                    
    def create_code_structure_nodes(self):
        """Create code structure node types based on MCP Crawl4AI RAG."""
        # Sample repository node
        with self.driver.session() as session:
            try:
                session.run(
                    """CREATE (r:Repository {
                        name: "Ptolemies Knowledge Base", 
                        url: "local", 
                        language: "Python",
                        description: "Local knowledge base repository"
                    })"""
                )
                print("✅ Created sample Repository node")
            except Exception as e:
                print(f"❌ Failed to create Repository: {e}")
                
    def create_relationships(self):
        """Create key relationships."""
        relationships = [
            # Source-Framework relationships
            ("FastAPI", "FastAPI", "minimal"),
            ("PyGAD", "PyGAD", "complete"),
            ("SurrealDB", "SurrealDB", "partial"),
            # Framework integrations
            ("FastAPI", "Pydantic AI", "native"),
            ("NextJS", "Tailwind CSS", "native"),
        ]
        
        with self.driver.session() as session:
            # Source-Framework relationships
            for source_name, framework_name, coverage in relationships[:3]:
                try:
                    session.run(
                        """MATCH (s:Source {name: $source}), (f:Framework {name: $framework})
                           CREATE (s)-[r:DOCUMENTS]->(f)
                           SET r.coverage = $coverage""",
                        source=source_name, framework=framework_name, coverage=coverage
                    )
                    print(f"✅ Created DOCUMENTS: {source_name} -> {framework_name}")
                except Exception as e:
                    print(f"❌ Failed relationship {source_name} -> {framework_name}: {e}")
                    
            # Framework integrations
            for f1_name, f2_name, int_type in relationships[3:]:
                try:
                    session.run(
                        """MATCH (f1:Framework {name: $f1}), (f2:Framework {name: $f2})
                           CREATE (f1)-[r:INTEGRATES_WITH]->(f2)
                           SET r.integration_type = $type""",
                        f1=f1_name, f2=f2_name, type=int_type
                    )
                    print(f"✅ Created INTEGRATES_WITH: {f1_name} -> {f2_name}")
                except Exception as e:
                    print(f"❌ Failed integration {f1_name} -> {f2_name}: {e}")
                    
    def verify_import(self):
        """Verify the import results."""
        with self.driver.session() as session:
            result = session.run(
                "MATCH (n) RETURN labels(n)[0] as NodeType, COUNT(n) as Count ORDER BY Count DESC"
            )
            
            print("\n🔍 Final Node Counts:")
            total_nodes = 0
            for record in result:
                node_type = record["NodeType"]
                count = record["Count"]
                total_nodes += count
                print(f"  {node_type}: {count}")
            
            print(f"\nTotal Nodes: {total_nodes}")
            
            # Check relationships
            rel_result = session.run(
                "MATCH ()-[r]->() RETURN type(r) as RelType, COUNT(r) as Count"
            )
            
            print("\n🔗 Relationships:")
            for record in rel_result:
                rel_type = record["RelType"]
                count = record["Count"]
                print(f"  {rel_type}: {count}")

def main():
    print("🚀 Starting Direct Neo4j Import...")
    
    importer = DirectNeo4jImporter()
    
    try:
        print("\n📋 Creating Topics...")
        importer.create_topics()
        
        print("\n📊 Creating Sources...")
        importer.create_sources()
        
        print("\n🏗️ Creating Code Structure...")
        importer.create_code_structure_nodes()
        
        print("\n🔗 Creating Relationships...")
        importer.create_relationships()
        
        print("\n✅ Import Complete!")
        importer.verify_import()
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
    finally:
        importer.close()

if __name__ == "__main__":
    main()