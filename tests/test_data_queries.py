#!/usr/bin/env python3
"""
Test actual data queries from COMPLETE_QUERY_RESULTS.md
Verify that data is accessible with the corrected configuration
"""

import asyncio
import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add src to path for imports
sys.path.insert(0, 'src')

try:
    from surrealdb_integration import SurrealDBVectorStore
    from neo4j_integration import Neo4jGraphStore
    from redis_cache_layer import RedisCacheLayer
    from hybrid_query_engine import HybridQueryEngine, QueryType
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the ptolemies directory")
    sys.exit(1)

class DataQueryTester:
    """Test queries against the Ptolemies knowledge base."""
    
    def __init__(self):
        self.vector_store = None
        self.graph_store = None
        self.cache_layer = None
        self.hybrid_engine = None
        
    async def initialize_connections(self):
        """Initialize all database connections."""
        print("🔌 Initializing database connections...")
        
        try:
            # Initialize SurrealDB Vector Store
            self.vector_store = SurrealDBVectorStore()
            connected = await self.vector_store.connect()
            if connected:
                print("   ✅ SurrealDB connected")
            else:
                print("   ❌ SurrealDB connection failed")
                return False
                
        except Exception as e:
            print(f"   ❌ SurrealDB error: {e}")
            return False
            
        try:
            # Initialize Neo4j Graph Store
            self.graph_store = Neo4jGraphStore()
            await self.graph_store.connect()
            print("   ✅ Neo4j connected")
            
        except Exception as e:
            print(f"   ❌ Neo4j error: {e}")
            # Continue without Neo4j for now
            
        try:
            # Initialize Redis Cache
            self.cache_layer = RedisCacheLayer()
            await self.cache_layer.connect()
            print("   ✅ Redis connected")
            
        except Exception as e:
            print(f"   ❌ Redis error: {e}")
            # Continue without Redis for now
            
        return True
        
    async def test_surrealdb_queries(self):
        """Test SurrealDB vector search queries."""
        print("\n🔍 Testing SurrealDB Vector Search Queries")
        print("=" * 50)
        
        if not self.vector_store or not self.vector_store.db:
            print("❌ SurrealDB not available")
            return
            
        try:
            # Query 1: Basic data existence check
            print("\n1. Checking for document chunks...")
            result = await self.vector_store.db.query("SELECT count() FROM document_chunks GROUP ALL;")
            
            if result and len(result) > 0 and len(result[0]) > 0:
                count = result[0][0].get('count', 0)
                print(f"   📊 Found {count} document chunks")
                
                if count == 0:
                    print("   ⚠️  No document chunks found - database may be empty")
                    return
            else:
                print("   ❌ Could not get document count")
                return
                
            # Query 2: Sample document retrieval
            print("\n2. Retrieving sample documents...")
            sample_result = await self.vector_store.db.query("""
                SELECT id, title, source_name, quality_score, topics
                FROM document_chunks
                LIMIT 5;
            """)
            
            if sample_result and len(sample_result) > 0:
                documents = sample_result[0]
                print(f"   📄 Retrieved {len(documents)} sample documents:")
                
                for i, doc in enumerate(documents[:3], 1):
                    print(f"      {i}. {doc.get('title', 'No title')[:50]}...")
                    print(f"         Source: {doc.get('source_name', 'Unknown')}")
                    print(f"         Quality: {doc.get('quality_score', 0):.2f}")
                    print(f"         Topics: {doc.get('topics', [])[:3]}")
                    print()
                    
            # Query 3: Source statistics
            print("\n3. Analyzing sources...")
            sources_result = await self.vector_store.db.query("""
                SELECT source_name, count() AS doc_count
                FROM document_chunks
                GROUP BY source_name
                ORDER BY doc_count DESC;
            """)
            
            if sources_result and len(sources_result) > 0:
                sources = sources_result[0]
                print(f"   📚 Found {len(sources)} unique sources:")
                
                for source in sources[:5]:
                    name = source.get('source_name', 'Unknown')
                    count = source.get('doc_count', 0)
                    print(f"      • {name}: {count} documents")
                    
            # Query 4: Quality analysis
            print("\n4. Quality score analysis...")
            quality_result = await self.vector_store.db.query("""
                SELECT 
                    avg(quality_score) AS avg_quality,
                    min(quality_score) AS min_quality,
                    max(quality_score) AS max_quality,
                    count() AS total_docs
                FROM document_chunks
                GROUP ALL;
            """)
            
            if quality_result and len(quality_result) > 0 and len(quality_result[0]) > 0:
                stats = quality_result[0][0]
                print(f"   📈 Quality Statistics:")
                print(f"      Average: {stats.get('avg_quality', 0):.3f}")
                print(f"      Range: {stats.get('min_quality', 0):.3f} - {stats.get('max_quality', 0):.3f}")
                print(f"      Total docs: {stats.get('total_docs', 0)}")
                
        except Exception as e:
            print(f"❌ SurrealDB query error: {e}")
            
    async def test_neo4j_queries(self):
        """Test Neo4j graph queries."""
        print("\n🕸️  Testing Neo4j Graph Queries")
        print("=" * 50)
        
        if not self.graph_store:
            print("❌ Neo4j not available")
            return
            
        try:
            # Query 1: Node count
            print("\n1. Checking graph data...")
            node_result = await self.graph_store.execute_query("MATCH (n) RETURN count(n) AS node_count")
            
            if node_result:
                node_count = node_result[0].get('node_count', 0)
                print(f"   🔗 Found {node_count} total nodes")
                
                if node_count == 0:
                    print("   ⚠️  No nodes found - graph may be empty")
                    return
                    
            # Query 2: Node types
            print("\n2. Analyzing node types...")
            types_result = await self.graph_store.execute_query("""
                MATCH (n)
                RETURN labels(n) AS node_labels, count(n) AS count
                ORDER BY count DESC
                LIMIT 10
            """)
            
            if types_result:
                print(f"   📊 Node type distribution:")
                for result in types_result[:5]:
                    labels = result.get('node_labels', [])
                    count = result.get('count', 0)
                    label_str = ', '.join(labels) if labels else 'No labels'
                    print(f"      • {label_str}: {count} nodes")
                    
            # Query 3: Concept analysis
            print("\n3. Top concepts...")
            concepts_result = await self.graph_store.execute_query("""
                MATCH (c:Concept)
                RETURN c.name AS concept, c.frequency AS frequency
                ORDER BY c.frequency DESC
                LIMIT 5
            """)
            
            if concepts_result:
                print(f"   🧠 Top concepts by frequency:")
                for result in concepts_result:
                    concept = result.get('concept', 'Unknown')
                    frequency = result.get('frequency', 0)
                    print(f"      • {concept}: {frequency}")
                    
        except Exception as e:
            print(f"❌ Neo4j query error: {e}")
            
    async def test_redis_cache(self):
        """Test Redis cache functionality."""
        print("\n🔄 Testing Redis Cache")
        print("=" * 50)
        
        if not self.cache_layer:
            print("❌ Redis not available")
            return
            
        try:
            # Test cache operations
            test_key = "ptolemies:test:query_verification"
            test_data = {"timestamp": datetime.now().isoformat(), "test": "data_migration_verification"}
            
            # Set cache
            await self.cache_layer.set(test_key, test_data, ttl=60)
            print("   ✅ Cache write successful")
            
            # Get cache
            cached_data = await self.cache_layer.get(test_key)
            if cached_data:
                print("   ✅ Cache read successful")
                print(f"      Data: {cached_data}")
            else:
                print("   ❌ Cache read failed")
                
            # Check cache stats
            stats = await self.cache_layer.get_stats()
            if stats:
                print(f"   📊 Cache stats: {stats}")
                
        except Exception as e:
            print(f"❌ Redis cache error: {e}")
            
    async def test_hybrid_queries(self):
        """Test hybrid query engine if available."""
        print("\n🔀 Testing Hybrid Query Engine")
        print("=" * 50)
        
        try:
            # Initialize hybrid engine
            self.hybrid_engine = HybridQueryEngine(
                vector_store=self.vector_store,
                graph_store=self.graph_store,
                cache_layer=self.cache_layer
            )
            
            # Test query
            test_query = "authentication security"
            print(f"\n   Query: '{test_query}'")
            
            if self.vector_store and self.vector_store.db:
                results, metrics = await self.hybrid_engine.search(
                    query=test_query,
                    query_type=QueryType.SEMANTIC_ONLY,
                    limit=3
                )
                
                print(f"   📊 Found {len(results)} results in {metrics.get('total_time_ms', 0):.1f}ms")
                
                for i, result in enumerate(results[:2], 1):
                    print(f"      {i}. {result.title[:50]}...")
                    print(f"         Score: {result.combined_score:.3f}")
                    
            else:
                print("   ⚠️  Vector store not available for hybrid queries")
                
        except Exception as e:
            print(f"❌ Hybrid query error: {e}")
            
    async def run_all_tests(self):
        """Run all data verification tests."""
        print("🧪 Ptolemies Data Query Verification")
        print("Testing data accessibility with corrected configuration")
        print("=" * 60)
        
        # Initialize connections
        connected = await self.initialize_connections()
        if not connected:
            print("❌ Failed to establish database connections")
            return False
            
        # Run tests
        await self.test_surrealdb_queries()
        await self.test_neo4j_queries()
        await self.test_redis_cache()
        await self.test_hybrid_queries()
        
        print("\n" + "=" * 60)
        print("🎉 Query verification completed!")
        
        return True
        
    async def cleanup(self):
        """Clean up connections."""
        try:
            if self.vector_store:
                await self.vector_store.disconnect()
            if self.graph_store:
                await self.graph_store.disconnect()
            if self.cache_layer:
                await self.cache_layer.disconnect()
        except:
            pass

async def main():
    """Main test execution."""
    tester = DataQueryTester()
    
    try:
        success = await tester.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    exit_code = asyncio.run(main())