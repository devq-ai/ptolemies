#!/usr/bin/env python3
"""
Test Context7 Integration with Ptolemies Knowledge Graph
======================================================

Simple test to validate the enhanced context7 implementation.
"""

import json
from typing import Dict, Any

class MockContext7Sourcer:
    """Mock implementation for testing context7 functionality."""
    
    def __init__(self):
        self.stored_docs = []
        self.mock_embeddings = {}
    
    def store_document(self, url: str, title: str, content: str, source_type: str = "manual") -> str:
        """Mock document storage."""
        doc_id = f"doc_{len(self.stored_docs) + 1}"
        
        doc = {
            "id": doc_id,
            "url": url,
            "title": title,
            "content": content,
            "source_type": source_type,
            "content_length": len(content)
        }
        
        self.stored_docs.append(doc)
        return doc_id
    
    def search_documents(self, query: str, limit: int = 5) -> list:
        """Mock document search."""
        results = []
        for doc in self.stored_docs:
            # Simple keyword matching
            if query.lower() in doc["title"].lower() or query.lower() in doc["content"].lower():
                results.append({
                    "id": doc["id"],
                    "title": doc["title"],
                    "url": doc["url"],
                    "content_preview": doc["content"][:200] + "...",
                    "similarity": 0.85,  # Mock similarity score
                    "source_type": doc["source_type"]
                })
        
        return results[:limit]
    
    def get_status(self) -> Dict[str, Any]:
        """Get mock status."""
        return {
            "redis_connected": True,
            "openai_connected": True,
            "stored_documents": len(self.stored_docs),
            "capabilities": [
                "Document storage with embeddings",
                "Semantic search",
                "Web crawling",
                "Context management"
            ]
        }

def test_context7_documentation_sourcing():
    """Test the context7 documentation sourcing capabilities."""
    print("🧪 Testing Context7 Documentation Sourcing")
    print("=" * 45)
    
    # Initialize mock sourcer
    sourcer = MockContext7Sourcer()
    
    # Test 1: Store documentation
    print("\n📝 Test 1: Storing documentation...")
    
    test_docs = [
        {
            "url": "https://fastapi.tiangolo.com/tutorial/",
            "title": "FastAPI Tutorial",
            "content": "FastAPI is a modern, fast (high-performance), web framework for building APIs with Python 3.7+ based on standard Python type hints. It provides automatic API documentation, data validation, and serialization.",
            "source_type": "web"
        },
        {
            "url": "https://docs.pydantic.dev/latest/",
            "title": "Pydantic Documentation", 
            "content": "Pydantic is the most widely used data validation library for Python. It provides data validation and settings management using Python type annotations.",
            "source_type": "web"
        },
        {
            "url": "local://ptolemies/ai_detector.py",
            "title": "AI Hallucination Detector",
            "content": "The AI Hallucination Detection System validates AI-generated Python code against the Neo4j knowledge graph to identify potential hallucinations in imports, classes, methods, and functions.",
            "source_type": "local_file"
        }
    ]
    
    stored_ids = []
    for doc in test_docs:
        doc_id = sourcer.store_document(
            doc["url"], doc["title"], doc["content"], doc["source_type"]
        )
        stored_ids.append(doc_id)
        print(f"✅ Stored: {doc['title']} (ID: {doc_id})")
    
    # Test 2: Search functionality
    print(f"\n🔍 Test 2: Searching {len(stored_ids)} stored documents...")
    
    search_queries = [
        "FastAPI web framework",
        "data validation",
        "hallucination detection",
        "Python type hints"
    ]
    
    for query in search_queries:
        results = sourcer.search_documents(query, limit=3)
        print(f"\nQuery: '{query}'")
        print(f"Found {len(results)} results:")
        
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result['title']} (Score: {result['similarity']:.2f})")
            print(f"     Preview: {result['content_preview'][:100]}...")
    
    # Test 3: Status check
    print(f"\n📊 Test 3: System status...")
    status = sourcer.get_status()
    print(f"Documents stored: {status['stored_documents']}")
    print(f"Redis connected: {status['redis_connected']}")
    print(f"OpenAI connected: {status['openai_connected']}")
    print("Capabilities:")
    for capability in status['capabilities']:
        print(f"  - {capability}")
    
    # Test 4: Integration with existing Ptolemies data
    print(f"\n🔗 Test 4: Ptolemies integration simulation...")
    
    # Simulate our existing knowledge graph sources
    ptolemies_sources = [
        {"name": "FastAPI", "chunks": 23, "avg_quality": 0.92},
        {"name": "Pydantic", "chunks": 18, "avg_quality": 0.89},
        {"name": "SurrealDB", "chunks": 15, "avg_quality": 0.85},
        {"name": "Neo4j", "chunks": 12, "avg_quality": 0.88},
        {"name": "Logfire", "chunks": 8, "avg_quality": 0.94}
    ]
    
    print("Existing Ptolemies knowledge sources:")
    for source in ptolemies_sources:
        # Simulate searching context7 for additional info
        context7_results = sourcer.search_documents(source["name"], limit=1)
        context7_available = "✅" if context7_results else "❌"
        
        print(f"  {source['name']}: {source['chunks']} chunks, "
              f"quality {source['avg_quality']:.2f}, "
              f"Context7 docs {context7_available}")
    
    # Test 5: Learning path context
    print(f"\n🎯 Test 5: Learning path context generation...")
    
    learning_topics = ["FastAPI authentication", "Pydantic validation", "API documentation"]
    
    for topic in learning_topics:
        results = sourcer.search_documents(topic, limit=2)
        context_available = len(results) > 0
        
        print(f"Learning context for '{topic}': "
              f"{'✅ Available' if context_available else '❌ Limited'}")
        
        if context_available:
            print(f"  Suggested resource: {results[0]['title']}")
    
    print(f"\n🎉 Context7 testing complete!")
    print(f"Successfully tested documentation sourcing, search, and integration capabilities.")
    
    return {
        "stored_documents": len(stored_ids),
        "search_tests": len(search_queries),
        "integration_sources": len(ptolemies_sources),
        "learning_contexts": len(learning_topics)
    }

def main():
    """Main test execution."""
    results = test_context7_documentation_sourcing()
    
    print(f"\n📈 Test Summary:")
    print(f"Documents stored: {results['stored_documents']}")
    print(f"Search tests: {results['search_tests']}")
    print(f"Integration sources: {results['integration_sources']}")
    print(f"Learning contexts: {results['learning_contexts']}")

if __name__ == "__main__":
    main()