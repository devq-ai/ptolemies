#!/usr/bin/env python3
"""Get crawl statistics from SurrealDB."""

import subprocess
import json
import sys

def run_surreal_query(query):
    """Execute SurrealDB query using CLI."""
    cmd = [
        'surreal', 'sql',
        '--conn', 'ws://localhost:8000/rpc',
        '--user', 'root',
        '--pass', 'root',
        '--ns', 'ptolemies',
        '--db', 'knowledge',
        '--pretty'
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
            return result.stdout
        else:
            print(f"Error: {result.stderr}")
            return None
    except Exception as e:
        print(f"Failed to execute query: {e}")
        return None

# Query 1: Get per-source statistics
query1 = """
SELECT source_name, count() as chunks FROM document_chunks GROUP BY source_name ORDER BY chunks DESC;
"""

# Query 2: Get overall statistics
query2 = """
SELECT count() as total_chunks FROM document_chunks;
"""

# Query 3: Get unique pages count
query3 = """
SELECT count(array::distinct(source_url)) as unique_pages FROM document_chunks;
"""

# Query 4: Get quality scores
query4 = """
SELECT source_name, math::mean(quality_score) as avg_quality FROM document_chunks GROUP BY source_name;
"""

print("=== PTOLEMIES KNOWLEDGE BASE CRAWL STATISTICS ===\n")

print("1. CHUNKS PER SOURCE:")
print("-" * 40)
result1 = run_surreal_query(query1)
if result1:
    print(result1)

print("\n2. TOTAL STATISTICS:")
print("-" * 40)
result2 = run_surreal_query(query2)
if result2:
    print(result2)

print("\n3. UNIQUE PAGES:")
print("-" * 40)
result3 = run_surreal_query(query3)
if result3:
    print(result3)

print("\n4. AVERAGE QUALITY SCORES:")
print("-" * 40)
result4 = run_surreal_query(query4)
if result4:
    print(result4)