#!/usr/bin/env python3
"""
Simple Completion Status Check
============================

Quick check of crawling completion status.
"""

import subprocess
from datetime import datetime

def check_current_status():
    """Check current crawling status."""
    
    print(f"🔍 Crawl Status Check - {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 50)
    
    # Check SurrealDB total
    try:
        cmd = [
            'surreal', 'sql',
            '--conn', 'ws://localhost:8000/rpc',
            '--user', 'root',
            '--pass', 'root',
            '--ns', 'ptolemies',
            '--db', 'knowledge',
            '--pretty'
        ]
        
        # Total chunks
        result = subprocess.run(
            cmd, 
            input="SELECT count() as total_chunks FROM document_chunks GROUP ALL;",
            text=True, capture_output=True, timeout=10
        )
        
        if "total_chunks:" in result.stdout:
            total = result.stdout.split("total_chunks: ")[1].split("\n")[0].strip()
            print(f"📦 SurrealDB Total Chunks: {total}")
        
        # By source
        result2 = subprocess.run(
            cmd,
            input="SELECT source_name, count() as chunks FROM document_chunks GROUP BY source_name ORDER BY chunks DESC;",
            text=True, capture_output=True, timeout=10
        )
        
        print("\n📊 Chunks by Source:")
        lines = result2.stdout.split('\n')
        sources_found = 0
        for line in lines:
            if 'chunks:' in line and 'source_name:' in line:
                # Extract source and chunks
                if 'source_name:' in line:
                    source_part = line.split("source_name: '")[1].split("'")[0]
                    chunks_part = line.split("chunks: ")[1].split(",")[0]
                    print(f"  {source_part}: {chunks_part} chunks")
                    sources_found += 1
        
        print(f"\n📈 Sources Covered: {sources_found}/17")
        
        # Check Neo4j
        neo_cmd = [
            'cypher-shell',
            '-a', 'bolt://localhost:7687',
            '-u', 'neo4j',
            '-p', 'ptolemies',
            '-d', 'neo4j',
            '--format', 'plain'
        ]
        
        neo_result = subprocess.run(
            neo_cmd,
            input="MATCH (n) WHERE n:Framework OR n:Class OR n:Method RETURN count(*) as total;",
            text=True, capture_output=True, timeout=10
        )
        
        if neo_result.returncode == 0:
            neo_lines = neo_result.stdout.strip().split('\n')
            if len(neo_lines) > 1:
                total_nodes = neo_lines[1].strip('"')
                print(f"🔗 Neo4j Total Nodes: {total_nodes}")
        
        # Completion assessment
        total_chunks = int(total) if total.isdigit() else 0
        
        print(f"\n🎯 Completion Assessment:")
        if total_chunks >= 1000 and sources_found >= 17:
            print("✅ CRAWLING APPEARS COMPLETE!")
            print("   - Target chunk count reached")
            print("   - All sources covered")
        elif total_chunks >= 800:
            print("⏳ Nearly complete - good progress")
            print(f"   - Need ~{1000 - total_chunks} more chunks for target")
        elif total_chunks >= 500:
            print("📈 Good progress - about halfway")
        else:
            print("🚀 Crawling in progress")
        
        return {
            "total_chunks": total_chunks,
            "sources_covered": sources_found,
            "is_complete": total_chunks >= 1000 and sources_found >= 17
        }
        
    except Exception as e:
        print(f"❌ Error checking status: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    status = check_current_status()
    
    if status.get("is_complete"):
        print("\n🎉 READY TO NOTIFY USER OF COMPLETION!")
    else:
        print(f"\n⏰ Continue monitoring - will check again in a few minutes")