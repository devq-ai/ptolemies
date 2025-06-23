#!/usr/bin/env python3
"""
Example Usage: Enhanced Ptolemies Documentation Crawler
Demonstrates how to use the enhanced infrastructure to crawl all 17 documentation sources.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from crawl4ai_integration import PtolemiesCrawler, CrawlConfig, DOCUMENTATION_SOURCES

async def main():
    """Example of crawling all documentation sources."""
    
    print("🚀 Ptolemies Enhanced Documentation Crawler")
    print(f"📚 Ready to crawl {len(DOCUMENTATION_SOURCES)} documentation sources")
    print()
    
    # Set a dummy OpenAI key for demo (embeddings will be disabled)
    os.environ['OPENAI_API_KEY'] = 'demo-key-embeddings-disabled'
    
    # Create crawler with standard configuration
    config = CrawlConfig(
        max_depth=2,        # Standard depth limit
        max_pages=10,       # Reduced for demo (use 250 for production)
        delay_ms=1000,      # Respectful 1-second delay
        timeout=30
    )
    
    crawler = PtolemiesCrawler(config)
    
    try:
        print(f"⚙️  Crawler Configuration:")
        print(f"   • Max pages per source: {config.max_pages}")
        print(f"   • Max crawl depth: {config.max_depth}")
        print(f"   • Delay between requests: {config.delay_ms}ms")
        print()
        
        # Example 1: Crawl a single source
        print("📖 Example 1: Crawling a single source (Crawl4AI docs)")
        result = await crawler.crawl_documentation_source(
            "https://docs.crawl4ai.com/",
            "Crawl4AI"
        )
        
        if result["success"]:
            print(f"✅ Success! Crawled {result['pages_crawled']} pages in {result['processing_time']:.2f} seconds")
            print(f"   • Pages stored: {result['pages_stored']}")
            print(f"   • Processing time: {result['processing_time']:.2f}s")
        else:
            print(f"❌ Failed: {result.get('error', 'Unknown error')}")
        
        print()
        
        # Example 2: Show all available sources
        print("📋 Example 2: All available documentation sources:")
        for i, source in enumerate(DOCUMENTATION_SOURCES, 1):
            print(f"   {i:2d}. {source['name']:12} → {source['url']}")
        
        print()
        print("🎯 Ready for Production Use!")
        print()
        print("To crawl all sources in production:")
        print("1. Start the FastAPI server: python src/main.py")
        print("2. Use the /crawl/all endpoint to crawl all 17 sources")
        print("3. Monitor progress with /crawl/metrics endpoint")
        print()
        print("Enhanced Features Available:")
        print("• SurrealDB vector storage for semantic search")
        print("• Neo4j graph relationships for concept mapping")
        print("• Redis caching for performance optimization")
        print("• Hybrid query engine for unified search")
        print("• Sub-100ms query performance with optimization")
        
    finally:
        await crawler.close()

if __name__ == "__main__":
    # Set environment variable to suppress logfire warnings in demo
    os.environ['LOGFIRE_IGNORE_NO_CONFIG'] = '1'
    asyncio.run(main())