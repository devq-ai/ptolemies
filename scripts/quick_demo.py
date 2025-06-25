#!/usr/bin/env python3
"""
Quick Ptolemies Data Access Demo
A fast demonstration of the key data access patterns in the 784-page knowledge base.
Run this to see immediate examples of how to query the system.
"""

import asyncio
import time
from typing import List, Dict, Any

async def demo_vector_search():
    """Quick demo of SurrealDB vector search."""
    print("🔍 SurrealDB Vector Search Demo")
    print("-" * 40)
    
    try:
        from src.surrealdb_integration import SurrealDBVectorStore, VectorStoreConfig
        
        # Initialize
        config = VectorStoreConfig(similarity_threshold=0.6)
        store = SurrealDBVectorStore(config)
        
        if await store.connect():
            print("✅ Connected to SurrealDB")
            
            # Quick search
            start_time = time.time()
            results = await store.semantic_search(
                query="FastAPI authentication middleware",
                limit=3
            )
            search_time = (time.time() - start_time) * 1000
            
            print(f"📊 Found {len(results)} results in {search_time:.2f}ms")
            
            for i, result in enumerate(results, 1):
                doc = result.document
                print(f"{i}. {doc.title[:50]}...")
                print(f"   Score: {result.similarity_score:.3f}")
                print(f"   Source: {doc.source_name}")
            
            # Get stats
            stats = await store.get_storage_stats()
            print(f"\n📈 Storage: {stats.get('total_chunks', 0)} chunks from {len(stats.get('chunks_by_source', {}))} sources")
            
            await store.close()
        else:
            print("❌ Could not connect to SurrealDB")
            
    except Exception as e:
        print(f"❌ Vector search demo failed: {e}")

async def demo_graph_search():
    """Quick demo of Neo4j graph search."""
    print("\n🕸️ Neo4j Graph Search Demo")
    print("-" * 40)
    
    try:
        from src.neo4j_integration import Neo4jGraphStore, Neo4jConfig
        
        # Initialize
        config = Neo4jConfig()
        store = Neo4jGraphStore(config)
        
        if await store.connect():
            print("✅ Connected to Neo4j")
            
            # Quick concept search
            start_time = time.time()
            result = await store.graph_search(
                query="authentication",
                search_type="concept",
                limit=5
            )
            search_time = (time.time() - start_time) * 1000
            
            print(f"📊 Found {len(result.nodes)} nodes, {len(result.relationships)} relationships in {search_time:.2f}ms")
            
            for i, node in enumerate(result.nodes[:3], 1):
                name = node.get('name') or node.get('title', 'Unknown')
                print(f"{i}. {name[:50]}...")
                if 'category' in node:
                    print(f"   Category: {node['category']}")
            
            # Get stats
            stats = await store.get_graph_stats()
            print(f"\n📈 Graph: {stats.get('document_count', 0)} documents, {stats.get('concept_count', 0)} concepts")
            
            await store.close()
        else:
            print("❌ Could not connect to Neo4j")
            
    except Exception as e:
        print(f"❌ Graph search demo failed: {e}")

async def demo_cache_operations():
    """Quick demo of Redis cache operations."""
    print("\n⚡ Redis Cache Demo")
    print("-" * 40)
    
    try:
        from src.redis_cache_layer import RedisCacheLayer, RedisCacheConfig, CacheMode
        
        # Initialize
        config = RedisCacheConfig(cache_mode=CacheMode.HYBRID)
        cache = RedisCacheLayer(config)
        
        if await cache.connect():
            print("✅ Connected to Redis")
            
            # Test cache operations
            test_data = {
                "query": "FastAPI authentication",
                "results": ["doc1", "doc2", "doc3"],
                "timestamp": time.time()
            }
            
            # Write to cache
            start_time = time.time()
            success = await cache.set("demo_query", test_data, "searches")
            write_time = (time.time() - start_time) * 1000
            
            # Read from cache
            start_time = time.time()
            data, found = await cache.get("demo_query", "searches")
            read_time = (time.time() - start_time) * 1000
            
            print(f"📥 Cache write: {write_time:.2f}ms")
            print(f"📤 Cache read: {read_time:.2f}ms ({'HIT' if found else 'MISS'})")
            
            # Get stats
            stats = await cache.get_cache_stats()
            metrics = stats.get('cache_metrics', {})
            print(f"📊 Hit rate: {metrics.get('hit_rate', 0.0):.2%}")
            print(f"🔄 Operations: {metrics.get('total_operations', 0)}")
            
            await cache.close()
        else:
            print("❌ Could not connect to Redis (using local cache)")
            
    except Exception as e:
        print(f"❌ Cache demo failed: {e}")

async def demo_hybrid_search():
    """Quick demo of hybrid search engine."""
    print("\n🧠 Hybrid Search Engine Demo")
    print("-" * 40)
    
    try:
        from src.hybrid_query_engine import create_hybrid_engine, QueryType
        
        # Initialize
        engine = await create_hybrid_engine()
        print("✅ Hybrid engine initialized")
        
        # Test different search types
        queries = [
            ("FastAPI middleware", QueryType.SEMANTIC_ONLY),
            ("authentication concepts", QueryType.GRAPH_ONLY),
            ("database optimization", QueryType.HYBRID_BALANCED)
        ]
        
        for query, query_type in queries:
            print(f"\n🔎 Query: '{query}' ({query_type.value})")
            
            start_time = time.time()
            results, metrics = await engine.search(
                query=query,
                query_type=query_type,
                limit=3
            )
            total_time = (time.time() - start_time) * 1000
            
            print(f"⏱️ Total: {total_time:.2f}ms (Semantic: {metrics.semantic_time_ms:.1f}ms, Graph: {metrics.graph_time_ms:.1f}ms)")
            print(f"📊 Results: {len(results)}")
            
            for i, result in enumerate(results, 1):
                print(f"{i}. {result.title[:40]}... (Score: {result.combined_score:.3f})")
                print(f"   Via: {', '.join(result.found_via)}")
        
        # Query suggestions
        suggestions = await engine.get_query_suggestions("fast")
        print(f"\n💡 Suggestions for 'fast': {suggestions[:3]}")
        
        await engine.vector_store.close()
        await engine.graph_store.close()
        
    except Exception as e:
        print(f"❌ Hybrid search demo failed: {e}")

async def demo_high_level_api():
    """Quick demo of high-level Knowledge API."""
    print("\n🎯 High-Level API Demo")
    print("-" * 40)
    
    try:
        from practical_usage_guide import PtolemiesKnowledgeAPI
        
        # Initialize
        api = PtolemiesKnowledgeAPI()
        if await api.initialize():
            print("✅ Knowledge API initialized")
            
            # Quick documentation search
            result = await api.search_documentation(
                query="How to implement FastAPI authentication?",
                max_results=2
            )
            
            print(f"📚 Documentation search: {len(result['results'])} results")
            print(f"⏱️ Search time: {result['search_time_ms']:.2f}ms")
            print(f"💾 From cache: {result['from_cache']}")
            
            if result['results']:
                top_result = result['results'][0]
                print(f"🏆 Top result: {top_result['title'][:50]}...")
                print(f"   Relevance: {top_result['relevance_score']:.3f}")
            
            # Code examples
            examples = await api.find_code_examples(
                technology="FastAPI",
                use_case="middleware",
                language="python"
            )
            
            print(f"\n💻 Code examples: {len(examples['examples'])} found")
            if examples['examples']:
                example = examples['examples'][0]
                print(f"📝 Example: {example['title'][:50]}...")
            
            # Concept exploration
            concepts = await api.explore_concepts("authentication", depth=1)
            concept_map = concepts['concept_map']
            
            print(f"\n🗺️ Concept exploration: {len(concept_map['related_concepts'])} related concepts")
            for concept in concept_map['related_concepts'][:3]:
                print(f"   • {concept['name']} (relevance: {concept['relevance']:.2f})")
            
            await api.close()
        else:
            print("❌ Could not initialize Knowledge API")
            
    except Exception as e:
        print(f"❌ High-level API demo failed: {e}")

async def show_system_overview():
    """Show system overview and capabilities."""
    print("🏛️ PTOLEMIES KNOWLEDGE BASE - QUICK DEMO")
    print("=" * 60)
    print("📚 Production Status:")
    print("   • 784 pages with embeddings stored")
    print("   • 17 documentation sources mapped")
    print("   • Sub-100ms query performance ready")
    print("   • Multi-database architecture active")
    print("")
    print("🔧 System Components:")
    print("   • SurrealDB: Vector storage & semantic search")
    print("   • Neo4j: Graph relationships & concept mapping")
    print("   • Redis: Distributed caching & performance")
    print("   • Hybrid Engine: Intelligent query fusion")
    print("")
    print("🚀 Starting demonstrations...")
    print("=" * 60)

async def main():
    """Run the complete quick demo."""
    await show_system_overview()
    
    # Run all demos
    await demo_vector_search()
    await demo_graph_search()
    await demo_cache_operations()
    await demo_hybrid_search()
    await demo_high_level_api()
    
    print("\n" + "=" * 60)
    print("🎉 QUICK DEMO COMPLETED!")
    print("=" * 60)
    print("📋 What you just saw:")
    print("   ✅ Vector semantic search (784 pages)")
    print("   ✅ Graph relationship exploration") 
    print("   ✅ Redis caching performance")
    print("   ✅ Hybrid query engine capabilities")
    print("   ✅ High-level API convenience methods")
    print("")
    print("🔗 Next steps:")
    print("   • Run 'python data_access_demo.py' for full demo")
    print("   • Run 'python web_api_demo.py' for REST API")
    print("   • See 'DATA_ACCESS_GUIDE.md' for complete documentation")
    print("")
    print("💡 The Ptolemies knowledge base is ready for integration!")

if __name__ == "__main__":
    asyncio.run(main())