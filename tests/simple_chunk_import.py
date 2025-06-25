#!/usr/bin/env python3
"""
Simple Chunk Import - Test with just a few chunks first
"""

import subprocess
import json

def get_sample_chunks():
    """Get first 10 chunks from SurrealDB for testing."""
    cmd = [
        'surreal', 'sql',
        '--conn', 'ws://localhost:8000/rpc',
        '--user', 'root',
        '--pass', 'root',
        '--ns', 'ptolemies',
        '--db', 'knowledge',
        '--json'
    ]
    
    query = """
    SELECT 
        id,
        source_name,
        title,
        content,
        chunk_index,
        total_chunks,
        quality_score,
        topics
    FROM document_chunks
    ORDER BY quality_score DESC
    LIMIT 10;
    """
    
    try:
        result = subprocess.run(
            cmd,
            input=query,
            text=True,
            capture_output=True,
            timeout=30
        )
        
        if result.returncode == 0:
            output = result.stdout.strip()
            if output:
                data = json.loads(output)
                if isinstance(data, list) and len(data) > 0:
                    result_data = data[0]
                    if isinstance(result_data, dict):
                        return result_data.get('result', [])
        return []
        
    except Exception as e:
        print(f"Error: {e}")
        return []

def clean_text(text):
    """Clean text for Cypher queries."""
    if not text:
        return ""
    # Escape single quotes and limit length
    text = str(text).replace("'", "''").replace("\\", "\\\\")
    return text[:500] if len(text) > 500 else text

def main():
    print("Fetching sample chunks from SurrealDB...")
    chunks = get_sample_chunks()
    
    if not chunks:
        print("No chunks found!")
        return
    
    print(f"Found {len(chunks)} chunks")
    
    # Generate individual CREATE statements for Neo4j Browser
    print("\n" + "="*60)
    print("COPY THESE STATEMENTS TO NEO4J BROWSER (one at a time):")
    print("="*60)
    
    for i, chunk in enumerate(chunks[:5]):  # Just first 5 for testing
        chunk_id = clean_text(chunk['id'])
        source_name = clean_text(chunk.get('source_name', ''))
        title = clean_text(chunk.get('title', ''))
        content = clean_text(chunk.get('content', ''))
        
        print(f"\n// Chunk {i+1}: {source_name} - {title[:50]}...")
        print(f"CREATE (c{i+1}:Chunk {{")
        print(f"  id: '{chunk_id}',")
        print(f"  source_name: '{source_name}',")
        print(f"  title: '{title}',")
        print(f"  content: '{content}',")
        print(f"  chunk_index: {chunk.get('chunk_index', 0)},")
        print(f"  quality_score: {chunk.get('quality_score', 0.5)}")
        print(f"}}) RETURN c{i+1}.id;")
    
    print("\n" + "="*60)
    print("After creating chunks, run this to link to sources:")
    print("="*60)
    
    for i, chunk in enumerate(chunks[:5]):
        source_name = clean_text(chunk.get('source_name', ''))
        print(f"MATCH (s:Source {{name: '{source_name}'}}), (c:Chunk {{id: '{clean_text(chunk['id'])}'}}) CREATE (s)-[:HAS_CHUNK]->(c);")

if __name__ == "__main__":
    main()