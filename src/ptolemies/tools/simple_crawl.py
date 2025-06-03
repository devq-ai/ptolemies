#!/usr/bin/env python3
"""
Simple crawler for Ptolemies Knowledge Base

This script provides a simple crawler to crawl a specific URL
and add it to the Ptolemies Knowledge Base.
"""

import argparse
import httpx
import json
import logging
import os
import sys
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import trafilatura
from datetime import datetime
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ptolemies.simple_crawl")

async def crawl_url(url, depth=2, tags=None, category=None):
    """Crawl a URL and store in SurrealDB."""
    logger.info(f"Crawling {url} (depth: {depth}, category: {category})")
    
    # Create HTTP client for web crawling
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        html = response.text
        
        # Extract content with trafilatura
        extracted_text = trafilatura.extract(html, include_comments=False, 
                                            include_tables=True, 
                                            include_images=True,
                                            include_links=True)
        
        # Extract metadata
        soup = BeautifulSoup(html, 'html.parser')
        title = soup.title.string if soup.title else ""
        
        # Extract meta description
        description = ""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            description = meta_desc.get('content', '')
        
        # Generate ID from URL
        item_id = f"knowledge_item:{uuid.uuid4()}"
        
        # Create knowledge item
        knowledge_item = {
            "id": item_id,
            "title": title,
            "content": extracted_text,
            "source": url,
            "source_type": "web",
            "content_type": "text/html",
            "tags": tags or [],
            "category": category,
            "metadata": {
                "crawl_timestamp": datetime.now().isoformat(),
                "description": description
            },
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Connect to SurrealDB
        surrealdb_host = "localhost"
        surrealdb_port = 8000
        surrealdb_user = "root"
        surrealdb_pass = "root"
        surrealdb_ns = "ptolemies"
        surrealdb_db = "knowledge"
        
        logger.info(f"Storing knowledge item in SurrealDB")
        
        async with httpx.AsyncClient() as db_client:
            # Direct insert query
            insert_query = f"""
            INSERT INTO knowledge_item {json.dumps(knowledge_item)};
            """
            
            response = await db_client.post(
                f"http://{surrealdb_host}:{surrealdb_port}/sql",
                content=insert_query,
                headers={
                    "Accept": "application/json",
                    "NS": surrealdb_ns,
                    "DB": surrealdb_db,
                    "Content-Type": "application/json"
                },
                auth=(surrealdb_user, surrealdb_pass)
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to store knowledge item: {response.text}")
                return None
            
            result = response.json()
            logger.info(f"SurrealDB response: {result}")
            
            if result and len(result) > 0 and result[0].get("status") == "OK":
                logger.info(f"Created knowledge item: {item_id}")
                return item_id
            
            logger.error(f"Failed to create knowledge item: {result}")
            return None

def main():
    """Main entry point for the crawler."""
    parser = argparse.ArgumentParser(description="Simple crawler for Ptolemies Knowledge Base")
    parser.add_argument("url", help="URL to crawl")
    parser.add_argument("--depth", type=int, default=2, help="Crawl depth")
    parser.add_argument("--tags", nargs="+", default=[], help="Tags to apply")
    parser.add_argument("--category", default="Uncategorized", help="Content category")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger("ptolemies").setLevel(logging.DEBUG)
    
    import asyncio
    item_id = asyncio.run(crawl_url(
        url=args.url,
        depth=args.depth,
        tags=args.tags,
        category=args.category
    ))
    
    if item_id:
        print(f"Successfully crawled and stored: {args.url}")
        print(f"Knowledge item ID: {item_id}")
        return 0
    else:
        print(f"Failed to crawl and store: {args.url}")
        return 1

if __name__ == "__main__":
    sys.exit(main())