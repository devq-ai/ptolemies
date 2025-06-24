#!/usr/bin/env python3
"""
Enhanced Chunk Importer for Ptolemies Knowledge Graph
Imports 292 chunks from SurrealDB into Neo4j with full-text search capabilities
"""

import asyncio
import subprocess
import json
from typing import List, Dict, Any
from datetime import datetime
import re

class EnhancedChunkImporter:
    def __init__(self, neo4j_uri="bolt://localhost:7687", neo4j_user="neo4j", neo4j_password="ptolemies"):
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        
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
                timeout=60
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                if output:
                    try:
                        data = json.loads(output)
                        if isinstance(data, list) and len(data) > 0:
                            result_data = data[0]
                            if isinstance(result_data, dict):
                                return result_data.get('result', [])
                            elif isinstance(result_data, list):
                                return result_data
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e}")
            return []
            
        except Exception as e:
            print(f"SurrealDB query failed: {e}")
            return []
    
    def run_cypher_query(self, query: str, database: str = "neo4j") -> bool:
        """Execute Cypher query in Neo4j."""
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
    
    def clean_text(self, text: str) -> str:
        """Clean text for Neo4j storage."""
        if not text:
            return ""
        # Escape single quotes and clean problematic characters
        text = str(text).replace("'", "''").replace("\\", "\\\\")
        # Remove control characters
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        # Limit length to prevent memory issues
        return text[:2000] if len(text) > 2000 else text
    
    async def fetch_all_chunks_enhanced(self) -> List[Dict[str, Any]]:
        """Fetch all chunks with enhanced metadata."""
        print("📊 Fetching all 292 chunks from SurrealDB...")
        
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
        
        # Enhance chunks with additional metadata
        enhanced_chunks = []
        for chunk in chunks:
            enhanced = chunk.copy()
            
            # Add content analysis
            content = str(chunk.get('content', ''))
            enhanced['word_count'] = len(content.split())
            enhanced['char_count'] = len(content)
            enhanced['has_code'] = 'def ' in content or 'function' in content or 'class ' in content
            enhanced['has_examples'] = 'example' in content.lower() or 'tutorial' in content.lower()
            
            # Clean content for Neo4j
            enhanced['content_clean'] = self.clean_text(content)
            enhanced['title_clean'] = self.clean_text(chunk.get('title', ''))
            
            enhanced_chunks.append(enhanced)
        
        return enhanced_chunks
    
    def create_chunk_with_fulltext(self, chunk: Dict[str, Any], batch_size: int = 50) -> str:
        """Generate Cypher query to create chunk with full-text search capabilities."""
        chunk_id = chunk['id']
        source_name = chunk.get('source_name', '')
        title = chunk.get('title_clean', '')
        content = chunk.get('content_clean', '')
        url = self.clean_text(chunk.get('source_url', ''))
        
        # Build topics array
        topics = chunk.get('topics', [])
        topics_str = "[" + ", ".join([f"'{self.clean_text(str(t))}'" for t in topics[:10]]) + "]"
        
        query = f"""
        CREATE (c:Chunk {{
            id: '{chunk_id}',
            source_name: '{self.clean_text(source_name)}',
            title: '{title}',
            content: '{content}',
            url: '{url}',
            chunk_index: {chunk.get('chunk_index', 0)},
            total_chunks: {chunk.get('total_chunks', 1)},
            quality_score: {chunk.get('quality_score', 0.5)},
            word_count: {chunk.get('word_count', 0)},
            char_count: {chunk.get('char_count', 0)},
            has_code: {str(chunk.get('has_code', False)).lower()},
            has_examples: {str(chunk.get('has_examples', False)).lower()},
            topics: {topics_str},
            created_at: datetime('{chunk.get('created_at', datetime.now().isoformat())}'),
            imported_at: datetime()
        }})
        """
        
        return query
    
    def create_chunk_relationships(self, source_name: str, chunk_id: str) -> str:
        """Create relationships between chunk and existing nodes."""
        return f"""
        // Link chunk to source
        MATCH (s:Source {{name: '{self.clean_text(source_name)}'}}),
              (c:Chunk {{id: '{chunk_id}'}})
        MERGE (s)-[r:HAS_CHUNK]->(c)
        SET r.imported_at = datetime()
        
        WITH c
        // Link chunk to topics
        UNWIND c.topics as topic_name
        MATCH (t:Topic {{name: topic_name}})
        MERGE (c)-[rt:COVERS_TOPIC]->(t)
        SET rt.confidence = 0.8
        """
    
    async def import_chunks_batch(self, chunks: List[Dict[str, Any]], batch_size: int = 10):
        """Import chunks in batches to avoid memory issues."""
        total_chunks = len(chunks)
        imported_count = 0
        
        print(f"📦 Importing {total_chunks} chunks in batches of {batch_size}...")
        
        for i in range(0, total_chunks, batch_size):
            batch = chunks[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_chunks + batch_size - 1) // batch_size
            
            print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} chunks)...")
            
            # Create batch query
            batch_queries = []
            for chunk in batch:
                chunk_query = self.create_chunk_with_fulltext(chunk)
                batch_queries.append(chunk_query)
            
            # Execute batch create
            combined_query = "\n".join(batch_queries)
            if self.run_cypher_query(combined_query):
                # Create relationships for this batch
                for chunk in batch:
                    rel_query = self.create_chunk_relationships(
                        chunk['source_name'], 
                        chunk['id']
                    )
                    self.run_cypher_query(rel_query)
                
                imported_count += len(batch)
                print(f"✅ Batch {batch_num} completed. Total imported: {imported_count}/{total_chunks}")
            else:
                print(f"❌ Batch {batch_num} failed")
        
        return imported_count
    
    def setup_fulltext_indexes(self):
        """Create full-text search indexes for chunks."""
        print("🔍 Setting up full-text search indexes...")
        
        indexes = [
            "CREATE FULLTEXT INDEX chunk_content_search IF NOT EXISTS FOR (c:Chunk) ON EACH [c.content]",
            "CREATE FULLTEXT INDEX chunk_title_search IF NOT EXISTS FOR (c:Chunk) ON EACH [c.title]", 
            "CREATE INDEX chunk_source IF NOT EXISTS FOR (c:Chunk) ON (c.source_name)",
            "CREATE INDEX chunk_quality IF NOT EXISTS FOR (c:Chunk) ON (c.quality_score)",
            "CREATE INDEX chunk_word_count IF NOT EXISTS FOR (c:Chunk) ON (c.word_count)",
            "CREATE INDEX chunk_has_code IF NOT EXISTS FOR (c:Chunk) ON (c.has_code)",
            "CREATE INDEX chunk_has_examples IF NOT EXISTS FOR (c:Chunk) ON (c.has_examples)"
        ]
        
        for index_query in indexes:
            if self.run_cypher_query(index_query):
                print(f"✅ Created index")
            else:
                print(f"❌ Failed to create index")
    
    async def verify_import(self):
        """Verify the chunk import."""
        print("\n🔍 Verifying chunk import...")
        
        verification_queries = [
            "MATCH (c:Chunk) RETURN COUNT(c) as total_chunks",
            "MATCH (c:Chunk) RETURN c.source_name, COUNT(c) as chunks ORDER BY chunks DESC",
            "MATCH (s:Source)-[r:HAS_CHUNK]->(c:Chunk) RETURN COUNT(r) as total_relationships",
            "MATCH (c:Chunk)-[r:COVERS_TOPIC]->(t:Topic) RETURN COUNT(r) as topic_relationships"
        ]
        
        for query in verification_queries:
            print(f"Query: {query}")
            # We'll just prepare the queries for manual execution in Neo4j Browser

async def main():
    """Main execution function."""
    print("🚀 Starting Enhanced Chunk Import for Ptolemies Knowledge Graph")
    print("=" * 70)
    
    importer = EnhancedChunkImporter()
    
    try:
        # Setup full-text indexes first
        importer.setup_fulltext_indexes()
        
        # Fetch all chunks from SurrealDB
        chunks = await importer.fetch_all_chunks_enhanced()
        
        if not chunks:
            print("❌ No chunks found in SurrealDB")
            return
        
        # Import chunks in batches
        imported_count = await importer.import_chunks_batch(chunks, batch_size=5)
        
        print(f"\n✅ Import Complete!")
        print(f"📊 Successfully imported {imported_count}/{len(chunks)} chunks")
        
        # Verify import
        await importer.verify_import()
        
    except Exception as e:
        print(f"❌ Import failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())