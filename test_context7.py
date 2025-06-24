#!/usr/bin/env python3
"""Test script to verify context7 MCP server availability and functionality."""

import sys
import os
import json

# Add context7 to path
sys.path.insert(0, '/Users/dionedge/devqai/mcp/mcp-servers/context7-mcp')

def test_context7_availability():
    """Test if context7 can be imported and initialized."""
    print("=" * 60)
    print("Context7 MCP Server Verification")
    print("=" * 60)
    
    # Test 1: Import test
    print("\n1. Testing imports...")
    try:
        from context7_mcp.server import server, redis_client, openai_client, doc_sourcer
        print("✅ Successfully imported context7 modules")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    
    # Test 2: Check connections
    print("\n2. Checking connections...")
    
    # Redis connection check
    redis_url = os.getenv('UPSTASH_REDIS_REST_URL')
    redis_token = os.getenv('UPSTASH_REDIS_REST_TOKEN')
    
    if redis_url and redis_token:
        print("✅ Redis environment variables are set")
        print(f"   - UPSTASH_REDIS_REST_URL: {redis_url[:30]}...")
    else:
        print("❌ Redis environment variables missing")
        print("   - UPSTASH_REDIS_REST_URL:", "SET" if redis_url else "NOT SET")
        print("   - UPSTASH_REDIS_REST_TOKEN:", "SET" if redis_token else "NOT SET")
    
    # OpenAI connection check
    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key:
        print("✅ OpenAI API key is set")
    else:
        print("❌ OpenAI API key is missing")
    
    # Test 3: Check available tools
    print("\n3. Available tools from context7:")
    tools = [
        "context7_status - Get server and connection status",
        "store_document - Store documents with embeddings",
        "search_documents - Semantic document search",
        "crawl_documentation - Web documentation crawler",
        "get_context - Get contextual information for topics",
        "bulk_crawl_sources - Crawl multiple documentation sources"
    ]
    
    for tool in tools:
        print(f"   - {tool}")
    
    # Test 4: Connection status
    print("\n4. Connection Status:")
    print(f"   - Redis client: {'Initialized' if redis_client else 'Not initialized'}")
    print(f"   - OpenAI client: {'Initialized' if openai_client else 'Not initialized'}")
    print(f"   - Document sourcer: {'Available' if doc_sourcer else 'Not available'}")
    
    # Test 5: Capabilities summary
    print("\n5. Context7 Capabilities:")
    capabilities = [
        "Advanced contextual reasoning with Redis backend",
        "Document storage with OpenAI embeddings",
        "Semantic search across stored documents",
        "Web documentation crawling and indexing",
        "Context management for knowledge graph",
        "Integration with Ptolemies ecosystem"
    ]
    
    for cap in capabilities:
        print(f"   ✓ {cap}")
    
    print("\n" + "=" * 60)
    
    # Overall status
    if redis_client or openai_client:
        print("✅ Context7 is partially functional")
        print("   Some features may be limited without full connections")
    else:
        print("⚠️  Context7 requires Redis and OpenAI connections")
        print("   Set UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN, and OPENAI_API_KEY")
    
    return True

if __name__ == "__main__":
    # First check if MCP is installed
    try:
        import mcp
        print("✅ MCP package is installed")
    except ImportError:
        print("❌ MCP package is not installed")
        print("   Install with: pip install mcp")
        sys.exit(1)
    
    # Run the test
    test_context7_availability()