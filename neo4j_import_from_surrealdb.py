#!/usr/bin/env python3
"""
Neo4j Import Script for Ptolemies Knowledge Base
Imports chunks from SurrealDB into Neo4j graph structure
"""

import asyncio
import subprocess
import json
from typing import List, Dict, Any
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class Neo4jImporter:
    """Import SurrealDB chunks into Neo4j knowledge graph."""
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687", 
                 neo4j_user: str = "neo4j",
                 neo4j_password: str = None):
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password or os.getenv("NEO4J_PASSWORD")
        
    def run_surreal_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute SurrealDB query and return results."""
        cmd = [
            'surreal', 'sql',
            '--conn', 'ws://localhost:8000/rpc',
            '--user', 'root',
            '--pass', 'root',
            '--ns', 'ptolemies',
            '--db', 'knowledge',
            '--json'
        ]
        
        try:
            result = subprocess.run(
                cmd,
                input=query,
                text=True,
                capture_output=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Parse JSON output
                output = result.stdout.strip()
                if output:
                    try:
                        data = json.loads(output)
                        # SurrealDB returns array of results
                        if isinstance(data, list) and len(data) > 0:
                            result_data = data[0]
                            if isinstance(result_data, dict):
                                return result_data.get('result', [])
                            elif isinstance(result_data, list):
                                return result_data
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e}")
                        print(f"Raw output: {output}")
            return []
            
        except Exception as e:
            print(f"SurrealDB query failed: {e}")
            return []
    
    def run_cypher_query(self, query: str, database: str = "neo4j") -> bool:
        """Execute Cypher query in Neo4j."""
        if not self.neo4j_password:
            print("❌ Neo4j password not set. Please set NEO4J_PASSWORD environment variable.")
            return False
            
        cmd = [
            'cypher-shell',
            '-a', self.neo4j_uri,
            '-u', self.neo4j_user,
            '-p', self.neo4j_password,
            '-d', database
        ]
        
        try:
            result = subprocess.run(
                cmd,
                input=query,
                text=True,
                capture_output=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return True
            else:
                print(f"Cypher error: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"Neo4j query failed: {e}")
            return False
    
    async def fetch_all_chunks(self) -> List[Dict[str, Any]]:
        """Fetch all chunks from SurrealDB."""
        print("📊 Fetching chunks from SurrealDB...")
        
        query = """
        SELECT 
            id,
            source_name,
            source_url,
            title,
            content,
            chunk_index,
            total_chunks,
            quality_score,
            topics,
            created_at
        FROM document_chunks
        ORDER BY source_name, chunk_index;
        """
        
        chunks = self.run_surreal_query(query)
        print(f"✅ Fetched {len(chunks)} chunks from SurrealDB")
        return chunks
    
    async def fetch_source_summary(self) -> List[Dict[str, Any]]:
        """Fetch source summary from SurrealDB."""
        print("📊 Fetching source summary...")
        
        query = """
        SELECT 
            source_name,
            COUNT() as chunk_count,
            AVG(quality_score) as avg_quality
        FROM document_chunks
        GROUP BY source_name;
        """
        
        sources = self.run_surreal_query(query)
        print(f"✅ Found {len(sources)} unique sources")
        return sources
    
    def create_source_node(self, source_name: str, chunk_count: int, avg_quality: float, database: str = "neo4j") -> bool:
        """Create a source node in Neo4j."""
        # Determine priority based on chunk count
        if chunk_count > 50:
            priority = "high"
        elif chunk_count > 10:
            priority = "medium"
        else:
            priority = "low"
            
        query = f"""
        MERGE (s:Source {{name: '{source_name}'}})
        SET s.chunk_count = {chunk_count},
            s.avg_quality = {avg_quality:.3f},
            s.priority = '{priority}',
            s.last_imported = datetime(),
            s.description = '{source_name} documentation source'
        RETURN s;
        """
        
        return self.run_cypher_query(query, database)
    
    def create_chunk_node(self, chunk: Dict[str, Any], database: str = "neo4j") -> bool:
        """Create a chunk node in Neo4j."""
        # Escape single quotes in text fields
        chunk_id = chunk['id']
        title = chunk.get('title', '').replace("'", "''")
        content = chunk.get('content', '')[:1000].replace("'", "''")  # Limit content length
        source_url = chunk.get('source_url', '').replace("'", "''")
        
        query = f"""
        MERGE (c:Chunk {{id: '{chunk_id}'}})
        SET c.title = '{title}',
            c.content = '{content}',
            c.url = '{source_url}',
            c.chunk_index = {chunk.get('chunk_index', 0)},
            c.total_chunks = {chunk.get('total_chunks', 1)},
            c.quality_score = {chunk.get('quality_score', 0.5)},
            c.created_at = datetime('{chunk.get('created_at', datetime.now().isoformat())}')
        RETURN c;
        """
        
        return self.run_cypher_query(query, database)
    
    def create_source_chunk_relationship(self, source_name: str, chunk_id: str, database: str = "neo4j") -> bool:
        """Create relationship between source and chunk."""
        query = f"""
        MATCH (s:Source {{name: '{source_name}'}}),
              (c:Chunk {{id: '{chunk_id}'}})
        MERGE (s)-[r:HAS_CHUNK]->(c)
        SET r.imported_at = datetime()
        RETURN r;
        """
        
        return self.run_cypher_query(query, database)
    
    def create_topic_relationships(self, chunk_id: str, topics: List[str], database: str = "neo4j") -> bool:
        """Create topic nodes and relationships."""
        if not topics:
            return True
            
        for topic in topics[:5]:  # Limit to 5 topics per chunk
            topic_name = str(topic).replace("'", "''")
            
            # Create topic node
            topic_query = f"""
            MERGE (t:Topic {{name: '{topic_name}'}})
            SET t.category = CASE 
                WHEN '{topic_name}' IN ['API', 'database', 'authentication', 'testing'] 
                THEN 'concept'
                WHEN '{topic_name}' IN ['Python', 'JavaScript', 'TypeScript'] 
                THEN 'language'
                ELSE 'framework'
            END
            RETURN t;
            """
            
            if self.run_cypher_query(topic_query, database):
                # Create relationship
                rel_query = f"""
                MATCH (c:Chunk {{id: '{chunk_id}'}}),
                      (t:Topic {{name: '{topic_name}'}})
                MERGE (c)-[r:COVERS_TOPIC]->(t)
                SET r.relevance = 0.8
                RETURN r;
                """
                
                self.run_cypher_query(rel_query, database)
        
        return True
    
    def create_framework_relationships(self, source_name: str, database: str = "neo4j") -> bool:
        """Create framework documentation relationships."""
        # Map sources to frameworks
        framework_map = {
            "FastAPI": "FastAPI",
            "NextJS": "NextJS",
            "SurrealDB": "SurrealDB",
            "Tailwind": "Tailwind CSS",
            "Shadcn": "Shadcn/UI",
            "Pydantic AI": "Pydantic AI",
            "Logfire": "Logfire",
            "PyGAD": "PyGAD",
            "bokeh": "bokeh",
            "Panel": "Panel",
            "Wildwood": "Wildwood",
            "Crawl4AI": "Crawl4AI",
            "FastMCP": "FastMCP",
            "AnimeJS": "AnimeJS",
            "PyMC": "PyMC",
            "circom": "circom",
            "Claude Code": "Claude Code"
        }
        
        if source_name in framework_map:
            framework_name = framework_map[source_name]
            
            # Determine framework type
            if source_name in ["FastAPI", "Pydantic AI", "Logfire", "PyGAD", "PyMC"]:
                framework_type = "backend"
                language = "Python"
            elif source_name in ["NextJS", "AnimeJS"]:
                framework_type = "frontend"
                language = "JavaScript"
            elif source_name in ["Tailwind", "Shadcn"]:
                framework_type = "frontend"
                language = "CSS"
            elif source_name == "SurrealDB":
                framework_type = "database"
                language = "Rust"
            else:
                framework_type = "tool"
                language = "Various"
            
            query = f"""
            MERGE (f:Framework {{name: '{framework_name}'}})
            SET f.type = '{framework_type}',
                f.language = '{language}'
            WITH f
            MATCH (s:Source {{name: '{source_name}'}})
            MERGE (s)-[r:DOCUMENTS]->(f)
            SET r.coverage = CASE
                WHEN s.chunk_count > 50 THEN 'complete'
                WHEN s.chunk_count > 20 THEN 'partial'
                ELSE 'minimal'
            END
            RETURN r;
            """
            
            return self.run_cypher_query(query, database)
        
        return True
    
    def setup_database(self):
        """Setup the ptolemies database."""
        print("🗄️ Setting up ptolemies database...")
        
        # First, try to create the database using system database
        try:
            create_db_query = "CREATE DATABASE ptolemies IF NOT EXISTS"
            if self.run_cypher_query(create_db_query, database="system"):
                print("✅ Database 'ptolemies' created/verified")
                return True
        except Exception as e:
            print(f"Could not create ptolemies database: {e}")
        
        # If that fails, we'll use the default neo4j database
        print("📝 Using default 'neo4j' database")
        return True

    async def import_all(self):
        """Main import process."""
        print("🚀 Starting Neo4j import from SurrealDB...")
        print(f"Neo4j URI: {self.neo4j_uri}")
        
        # Step 0: Setup database
        self.setup_database()
        
        # Use the default neo4j database in your devqai project
        target_database = "neo4j"
        print(f"📊 Using '{target_database}' database in your devqai project")
        
        # Step 1: Create schema
        print(f"\n📋 Creating Neo4j schema in '{target_database}' database...")
        with open('/Users/dionedge/devqai/ptolemies/neo4j_schema.cypher', 'r') as f:
            schema_queries = f.read().split(';')
            
        for query in schema_queries:
            query = query.strip()
            if query and not query.startswith('//'):
                self.run_cypher_query(query + ';', database=target_database)
        
        print("✅ Schema created")
        
        # Step 2: Import sources
        print("\n📦 Importing sources...")
        sources = await self.fetch_source_summary()
        
        for source in sources:
            source_name = source['source_name']
            chunk_count = source['chunk_count']
            avg_quality = source.get('avg_quality', 0.8)
            
            if self.create_source_node(source_name, chunk_count, avg_quality):
                print(f"✅ Created source: {source_name} ({chunk_count} chunks)")
                self.create_framework_relationships(source_name)
        
        # Step 3: Import chunks
        print("\n📄 Importing chunks...")
        chunks = await self.fetch_all_chunks()
        
        imported_count = 0
        for i, chunk in enumerate(chunks):
            if i % 50 == 0:
                print(f"Progress: {i}/{len(chunks)} chunks...")
            
            chunk_id = chunk['id']
            source_name = chunk['source_name']
            
            # Create chunk node
            if self.create_chunk_node(chunk):
                # Create source relationship
                self.create_source_chunk_relationship(source_name, chunk_id)
                
                # Create topic relationships
                topics = chunk.get('topics', [])
                if topics:
                    self.create_topic_relationships(chunk_id, topics)
                
                imported_count += 1
        
        print(f"\n✅ Import complete! Imported {imported_count}/{len(chunks)} chunks")
        
        # Step 4: Verify import
        print("\n🔍 Verifying import...")
        verification_query = """
        MATCH (s:Source)
        RETURN s.name as source, s.chunk_count as chunks
        ORDER BY s.chunk_count DESC;
        """
        
        self.run_cypher_query(verification_query)
        
        print("\n🎉 Neo4j import completed successfully!")
        print("\nUseful queries to try:")
        print("- MATCH (s:Source)-[:HAS_CHUNK]->(c:Chunk) RETURN s.name, COUNT(c) as chunks;")
        print("- MATCH (c:Chunk)-[:COVERS_TOPIC]->(t:Topic) RETURN t.name, COUNT(c) as mentions ORDER BY mentions DESC LIMIT 10;")
        print("- MATCH (f:Framework)<-[:DOCUMENTS]-(s:Source) RETURN f.name, COLLECT(s.name) as sources;")


async def main():
    """Main execution function."""
    # Get Neo4j password from environment or prompt
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    if not neo4j_password:
        print("⚠️  Neo4j password not found in environment.")
        print("Please set NEO4J_PASSWORD environment variable:")
        print("export NEO4J_PASSWORD='your_password'")
        return
    
    importer = Neo4jImporter(neo4j_password=neo4j_password)
    await importer.import_all()


if __name__ == "__main__":
    asyncio.run(main())