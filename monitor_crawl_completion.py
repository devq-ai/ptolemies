#!/usr/bin/env python3
"""
Monitor Crawl Completion for All 17 Targets
==========================================

Monitors progress and notifies when all 17 targets are crawled 
with complete RAG in SurrealDB and graph in Neo4j.
"""

import time
import subprocess
import json
from datetime import datetime
from typing import Dict, List, Any

# Target sources
TARGET_SOURCES = [
    "FastAPI", "SurrealDB", "Pydantic AI", "Logfire", "NextJS", 
    "Claude Code", "Crawl4AI", "FastMCP", "Tailwind", "AnimeJS", 
    "Shadcn", "Panel", "bokeh", "PyMC", "Wildwood", "PyGAD", "circom"
]

# Minimum thresholds for completion
MIN_CHUNKS_PER_SOURCE = 20  # Minimum chunks to consider "complete"
TARGET_TOTAL_CHUNKS = 1000  # Target total chunks for comprehensive coverage

class CrawlMonitor:
    """Monitors crawling progress and completion."""
    
    def __init__(self):
        self.last_check = None
        self.last_total = 0
        
    def get_surrealdb_status(self) -> Dict[str, Any]:
        """Get current SurrealDB crawling status."""
        
        # Query for source status
        source_query = """
        SELECT source_name, count() as chunks 
        FROM document_chunks 
        GROUP BY source_name 
        ORDER BY chunks DESC;
        """
        
        # Query for total status
        total_query = """
        SELECT count() as total_chunks, 
               count(DISTINCT source_name) as sources_covered
        FROM document_chunks GROUP ALL;
        """
        
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
            # Get source breakdown
            result1 = subprocess.run(
                cmd, input=source_query, text=True, 
                capture_output=True, timeout=30
            )
            
            # Get totals
            result2 = subprocess.run(
                cmd, input=total_query, text=True,
                capture_output=True, timeout=30
            )
            
            # Parse results (simplified parsing)
            source_data = {}
            if result1.returncode == 0:
                # Extract chunks per source from output
                lines = result1.stdout.split('\n')
                for line in lines:
                    if 'chunks:' in line and 'source_name:' in line:
                        # Simple parsing for chunks and source
                        if 'chunks: ' in line:
                            chunks_part = line.split('chunks: ')[1].split(',')[0]
                            chunks = int(chunks_part.strip())
                        if 'source_name:' in line:
                            source_part = line.split("source_name: '")[1].split("'")[0]
                            source_data[source_part] = chunks
            
            # Get total from second query
            total_chunks = 0
            sources_covered = 0
            if result2.returncode == 0:
                if 'total_chunks:' in result2.stdout:
                    total_part = result2.stdout.split('total_chunks: ')[1].split(',')[0]
                    total_chunks = int(total_part.strip())
                if 'sources_covered:' in result2.stdout:
                    sources_part = result2.stdout.split('sources_covered: ')[1].split('\n')[0]
                    sources_covered = int(sources_part.strip())
            
            return {
                "source_breakdown": source_data,
                "total_chunks": total_chunks,
                "sources_covered": sources_covered,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error querying SurrealDB: {e}")
            return {"error": str(e)}
    
    def get_neo4j_status(self) -> Dict[str, Any]:
        """Get current Neo4j graph status."""
        
        # Query for graph completeness
        graph_query = """
        MATCH (n)
        WHERE n:Framework OR n:Class OR n:Method OR n:Function
        RETURN labels(n)[0] as type, count(*) as count
        ORDER BY type;
        """
        
        cmd = [
            'cypher-shell',
            '-a', 'bolt://localhost:7687',
            '-u', 'neo4j',
            '-p', 'ptolemies',
            '-d', 'neo4j',
            '--format', 'plain'
        ]
        
        try:
            result = subprocess.run(
                cmd, input=graph_query, text=True,
                capture_output=True, timeout=30
            )
            
            if result.returncode == 0:
                # Parse results
                lines = result.stdout.strip().split('\n')
                graph_data = {}
                if len(lines) > 1:  # Skip header
                    for line in lines[1:]:
                        if line.strip():
                            parts = line.split(', ')
                            if len(parts) == 2:
                                node_type = parts[0].strip('"')
                                count = int(parts[1].strip('"'))
                                graph_data[node_type] = count
                
                return {
                    "graph_breakdown": graph_data,
                    "total_nodes": sum(graph_data.values()),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {"error": f"Neo4j query failed: {result.stderr}"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def check_completion_status(self, surrealdb_status: Dict, neo4j_status: Dict) -> Dict[str, Any]:
        """Check if crawling is complete based on targets."""
        
        completion_status = {
            "is_complete": False,
            "surrealdb_complete": False,
            "neo4j_complete": False,
            "missing_sources": [],
            "low_coverage_sources": [],
            "recommendations": []
        }
        
        if "error" in surrealdb_status or "error" in neo4j_status:
            completion_status["error"] = "Database connection issues"
            return completion_status
        
        # Check SurrealDB completion
        source_breakdown = surrealdb_status.get("source_breakdown", {})
        total_chunks = surrealdb_status.get("total_chunks", 0)
        
        # Check for missing sources
        for target_source in TARGET_SOURCES:
            if target_source not in source_breakdown:
                completion_status["missing_sources"].append(target_source)
            elif source_breakdown[target_source] < MIN_CHUNKS_PER_SOURCE:
                completion_status["low_coverage_sources"].append({
                    "source": target_source,
                    "chunks": source_breakdown[target_source],
                    "target": MIN_CHUNKS_PER_SOURCE
                })
        
        # SurrealDB completion criteria
        surrealdb_complete = (
            len(completion_status["missing_sources"]) == 0 and
            len(completion_status["low_coverage_sources"]) == 0 and
            total_chunks >= TARGET_TOTAL_CHUNKS
        )
        completion_status["surrealdb_complete"] = surrealdb_complete
        
        # Check Neo4j completion
        graph_breakdown = neo4j_status.get("graph_breakdown", {})
        total_nodes = neo4j_status.get("total_nodes", 0)
        
        # Neo4j completion criteria (basic)
        neo4j_complete = (
            graph_breakdown.get("Framework", 0) >= 17 and  # All frameworks
            graph_breakdown.get("Class", 0) >= 50 and      # Substantial classes
            total_nodes >= 100                              # Overall completeness
        )
        completion_status["neo4j_complete"] = neo4j_complete
        
        # Overall completion
        completion_status["is_complete"] = surrealdb_complete and neo4j_complete
        
        # Generate recommendations
        if not surrealdb_complete:
            if completion_status["missing_sources"]:
                completion_status["recommendations"].append(
                    f"Continue crawling missing sources: {', '.join(completion_status['missing_sources'])}"
                )
            if completion_status["low_coverage_sources"]:
                completion_status["recommendations"].append(
                    f"Increase coverage for {len(completion_status['low_coverage_sources'])} sources"
                )
            if total_chunks < TARGET_TOTAL_CHUNKS:
                completion_status["recommendations"].append(
                    f"Need {TARGET_TOTAL_CHUNKS - total_chunks} more chunks for target coverage"
                )
        
        if not neo4j_complete:
            completion_status["recommendations"].append(
                "Populate Neo4j with more framework classes and methods"
            )
        
        return completion_status
    
    def monitor_and_report(self, check_interval: int = 60):
        """Continuously monitor and report progress."""
        
        print("🔍 Starting crawl completion monitoring...")
        print(f"📊 Targets: {len(TARGET_SOURCES)} sources, {TARGET_TOTAL_CHUNKS} total chunks")
        print(f"⏱️  Check interval: {check_interval} seconds")
        print("=" * 60)
        
        while True:
            try:
                current_time = datetime.now()
                print(f"\n⏰ Check at {current_time.strftime('%H:%M:%S')}")
                
                # Get current status
                surrealdb_status = self.get_surrealdb_status()
                neo4j_status = self.get_neo4j_status()
                
                # Check completion
                completion = self.check_completion_status(surrealdb_status, neo4j_status)
                
                # Report current status
                if "error" not in surrealdb_status:
                    total_chunks = surrealdb_status.get("total_chunks", 0)
                    sources_covered = surrealdb_status.get("sources_covered", 0)
                    
                    print(f"📦 SurrealDB: {total_chunks} chunks, {sources_covered}/17 sources")
                    
                    # Show progress since last check
                    if self.last_total > 0:
                        new_chunks = total_chunks - self.last_total
                        if new_chunks > 0:
                            print(f"📈 Progress: +{new_chunks} chunks since last check")
                    
                    self.last_total = total_chunks
                
                if "error" not in neo4j_status:
                    total_nodes = neo4j_status.get("total_nodes", 0)
                    print(f"🔗 Neo4j: {total_nodes} total nodes")
                
                # Report completion status
                if completion["is_complete"]:
                    print("\n🎉 CRAWLING COMPLETE!")
                    print("✅ All 17 targets crawled and pushed to SurrealDB")
                    print("✅ Complete RAG system ready")
                    print("✅ Complete Neo4j graph populated")
                    break
                else:
                    print(f"⏳ In progress...")
                    if completion["missing_sources"]:
                        print(f"❌ Missing: {', '.join(completion['missing_sources'])}")
                    if completion["low_coverage_sources"]:
                        low_sources = [s["source"] for s in completion["low_coverage_sources"]]
                        print(f"⚠️  Low coverage: {', '.join(low_sources)}")
                
                # Show recommendations
                if completion["recommendations"]:
                    print("💡 Recommendations:")
                    for rec in completion["recommendations"]:
                        print(f"  - {rec}")
                
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                print("\n⏹️  Monitoring stopped by user")
                break
            except Exception as e:
                print(f"❌ Monitoring error: {e}")
                time.sleep(check_interval)

def main():
    """Main monitoring function."""
    monitor = CrawlMonitor()
    
    # Get initial status
    print("🚀 Initial Status Check")
    surrealdb_status = monitor.get_surrealdb_status()
    neo4j_status = monitor.get_neo4j_status()
    
    if "error" not in surrealdb_status:
        print(f"📦 SurrealDB: {surrealdb_status.get('total_chunks', 0)} chunks")
        print(f"📊 Sources covered: {surrealdb_status.get('sources_covered', 0)}/17")
    
    if "error" not in neo4j_status:
        print(f"🔗 Neo4j: {neo4j_status.get('total_nodes', 0)} nodes")
    
    completion = monitor.check_completion_status(surrealdb_status, neo4j_status)
    
    if completion["is_complete"]:
        print("\n🎉 ALREADY COMPLETE!")
        print("All targets are crawled with complete RAG and Neo4j graph!")
    else:
        print("\n⏳ Crawling in progress, starting monitoring...")
        monitor.monitor_and_report(check_interval=120)  # Check every 2 minutes

if __name__ == "__main__":
    main()