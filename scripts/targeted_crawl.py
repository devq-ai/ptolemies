#!/usr/bin/env python3
"""
Targeted Knowledge Base Crawler
===============================

This script runs a targeted crawl for a specific list of new documentation
sources without performing a full database rebuild. It is designed to
incrementally add new knowledge to the existing Ptolemies database.
"""

import asyncio
import os
import sys

# Ensure the 'src' directory is in the Python path to allow for module imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from production_crawler_hybrid import ProductionCrawler
except ImportError:
    print("Error: Could not import ProductionCrawler.")
    print("Please ensure this script is run from the project root directory,")
    print("or that the 'src' directory is in your PYTHONPATH.")
    sys.exit(1)

# Define the specific new sources to be crawled. This list can be modified
# to target any subset of documentation sources.
NEW_SOURCES = [
    {"name": "Redis Docs", "url": "https://redis.io/docs/latest/", "priority": "medium"},
]

async def main():
    """
    Main function to initialize and run the targeted crawl.
    """
    print("🚀 STARTING TARGETED KNOWLEDGE BASE CRAWL")
    print("=" * 60)

    # Instantiate the main crawler class to access its methods
    crawler = ProductionCrawler()

    try:
        # Initialize the crawler's components like HTTP clients, database
        # connections, and the OpenAI client. This does NOT delete data.
        print("🔧 Initializing crawler components...")
        if not await crawler.initialize():
            print("❌ Crawler initialization failed. Please check database connections and API keys.")
            return 1

        print(f"✅ Crawler initialized successfully.")
        print(f"🎯 Found {len(NEW_SOURCES)} new sources to process.")

        # Sequentially crawl each new source
        for i, source in enumerate(NEW_SOURCES, 1):
            print("-" * 60)
            print(f"({i}/{len(NEW_SOURCES)}) Crawling source: {source['name']}")
            print(f"URL: {source['url']}")

            # The crawl_source method handles the entire process for one source:
            # fetching, parsing, chunking, embedding, and storing.
            chunks_created = await crawler.crawl_source(source)

            print(f"✅ Finished crawling {source['name']}. Found and stored {chunks_created} new chunks.")

        print("=" * 60)
        print("🎉 TARGETED CRAWL COMPLETE!")
        print("All specified sources have been processed and added to the knowledge base.")
        return 0

    except Exception as e:
        print(f"\n❌ An unexpected error occurred during the crawl: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Ensure all client connections are closed gracefully
        print("🧹 Cleaning up resources...")
        await crawler.cleanup()
        print("✅ Cleanup complete.")

if __name__ == "__main__":
    # This block allows the async main function to be run from the command line.
    # The exit code from main() will be used to terminate the script.
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
