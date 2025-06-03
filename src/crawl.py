#!/usr/bin/env python3
"""
Crawl web content and store in SurrealDB
"""

import asyncio
import sys
import httpx
from bs4 import BeautifulSoup
import trafilatura
from surrealdb import Surreal

async def crawl_url(url, tags=None, category=None):
    """Crawl a URL and store in SurrealDB."""
    print(f"Crawling {url}")
    
    # Create HTTP client for web crawling
    async with httpx.AsyncClient(follow_redirects=True) as client:
        # Fetch the page content
        response = await client.get(url)
        response.raise_for_status()
        html = response.text
        
        # Extract content with trafilatura
        extracted_text = trafilatura.extract(html, include_comments=False, 
                                            include_tables=True, 
                                            include_images=True,
                                            include_links=True)
        
        # If trafilatura fails, fall back to BeautifulSoup
        if not extracted_text:
            soup = BeautifulSoup(html, 'html.parser')
            extracted_text = ""
            for p in soup.find_all('p'):
                extracted_text += p.get_text() + "\n\n"
        
        # Extract metadata
        soup = BeautifulSoup(html, 'html.parser')
        title = soup.title.string if soup.title else ""
        
        # Extract meta description
        description = ""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            description = meta_desc.get('content', '')
        
        # Connect to SurrealDB
        print("Connecting to SurrealDB...")
        db = Surreal("http://localhost:8000")
        await db.connect()
        
        # Sign in
        await db.signin({"user": "root", "pass": "root"})
        
        # Select namespace and database
        await db.use("ptolemies", "knowledge")
        
        # Create a knowledge item
        knowledge_item = {
            "title": title,
            "content": extracted_text,
            "description": description,
            "source": url,
            "tags": tags or [],
            "category": category or "Uncategorized"
        }
        
        # Store in SurrealDB
        print("Storing in SurrealDB...")
        result = await db.create("knowledge_item", knowledge_item)
        
        if result:
            item_id = result.get("id")
            print(f"Successfully stored: {url}")
            print(f"Knowledge item ID: {item_id}")
            return item_id
        else:
            print("Failed to store knowledge item")
            return None

async def crawl_from_file(targets_file):
    """Crawl targets from a JSON file."""
    import json
    
    print(f"Crawling targets from {targets_file}")
    
    with open(targets_file, "r") as f:
        data = json.load(f)
    
    targets = data.get("targets", [])
    
    if not targets:
        print("No targets found in file")
        return
    
    print(f"Found {len(targets)} targets")
    
    for target in targets:
        url = target.get("url")
        name = target.get("name", url)
        category = target.get("category", "Uncategorized")
        tags = target.get("tags", [])
        
        print(f"\nProcessing {name} ({url})")
        await crawl_url(url, tags, category)

async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python crawl.py url <url> [--tags tag1,tag2,...] [--category Category]")
        print("  python crawl.py file <targets.json>")
        return 1
    
    command = sys.argv[1]
    
    if command == "url" and len(sys.argv) > 2:
        url = sys.argv[2]
        tags = []
        category = None
        
        # Parse command line arguments
        for i in range(3, len(sys.argv)):
            if sys.argv[i] == "--tags" and i + 1 < len(sys.argv):
                tags = sys.argv[i + 1].split(",")
            elif sys.argv[i] == "--category" and i + 1 < len(sys.argv):
                category = sys.argv[i + 1]
        
        await crawl_url(url, tags, category)
    
    elif command == "file" and len(sys.argv) > 2:
        targets_file = sys.argv[2]
        await crawl_from_file(targets_file)
    
    else:
        print("Invalid command or missing arguments")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))