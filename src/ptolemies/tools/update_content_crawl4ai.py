#!/usr/bin/env python3
"""
Update Ptolemies Knowledge Base with full content from URLs using Crawl4AI

This script:
1. Retrieves all knowledge items from the database
2. Uses Crawl4AI to fetch and process content for each URL
3. Updates the knowledge items with the processed content
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse

import httpx
import trafilatura
from bs4 import BeautifulSoup
from surrealdb import Surreal
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("update-content-crawl4ai")

# SurrealDB connection parameters
SURREALDB_URL = os.getenv("SURREALDB_URL", "http://localhost:8000")
SURREALDB_NAMESPACE = os.getenv("SURREALDB_NAMESPACE", "ptolemies")
SURREALDB_DATABASE = os.getenv("SURREALDB_DATABASE", "knowledge")
SURREALDB_USERNAME = os.getenv("SURREALDB_USERNAME", "root")
SURREALDB_PASSWORD = os.getenv("SURREALDB_PASSWORD", "root")

async def connect_to_db() -> Surreal:
    """Connect to SurrealDB."""
    db = Surreal(SURREALDB_URL)
    await db.connect()
    await db.signin({"user": SURREALDB_USERNAME, "pass": SURREALDB_PASSWORD})
    await db.use(SURREALDB_NAMESPACE, SURREALDB_DATABASE)
    logger.info(f"Connected to SurrealDB at {SURREALDB_URL}")
    return db

async def get_knowledge_items(db: Surreal) -> List[Dict[str, Any]]:
    """Retrieve knowledge items that need content update."""
    query = """
    SELECT id, title, source 
    FROM type::table(knowledge_item) 
    WHERE content = NULL OR content = 'None' OR content CONTAINS 'Content from URL:';
    """
    
    result = await db.query(query)
    
    if not result or not result[0].get("result"):
        logger.info("No knowledge items found that need content update")
        return []
    
    items = result[0].get("result", [])
    logger.info(f"Found {len(items)} knowledge items that need content update")
    return items

async def process_page(url: str, html: str) -> str:
    """Process a page using Crawl4AI techniques.
    
    Args:
        url: The URL of the page
        html: The HTML content of the page
        
    Returns:
        Processed content
    """
    # Check if this is an image or non-HTML content
    content_type = ""
    if len(html) < 50 or html.startswith('\x89PNG') or html.startswith('\xff\xd8\xff'):
        return f"Binary content from URL: {url} (likely an image or binary file)"
    
    # Use trafilatura for main content extraction (same as Crawl4AI)
    try:
        extracted_text = trafilatura.extract(
            html, 
            include_comments=False,
            include_tables=True,
            include_images=True,
            include_links=True
        )
    except Exception as e:
        logger.warning(f"Trafilatura extraction failed: {e}")
        extracted_text = None
    
    # Fallback to BeautifulSoup if trafilatura fails
    if not extracted_text:
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Try to get the article or main content
            main_content = None
            for selector in ['article', 'main', '.content', '#content', '.post', '.article']:
                main_content = soup.select_one(selector)
                if main_content:
                    break
            
            if main_content:
                extracted_text = main_content.get_text(separator='\n\n')
            else:
                # Fallback to body
                extracted_text = soup.body.get_text(separator='\n\n') if soup.body else ""
        except Exception as e:
            logger.warning(f"BeautifulSoup extraction failed: {e}")
            # Last resort - just save the raw content (limited to first 1000 chars if it's very large)
            if len(html) > 1000:
                extracted_text = f"Raw content (truncated): {html[:1000]}..."
            else:
                extracted_text = f"Raw content: {html}"
    
    if not extracted_text:
        return f"Failed to extract content from URL: {url}"
        
    return extracted_text

async def fetch_and_process_url(url: str) -> Optional[str]:
    """Fetch a URL and process its content using Crawl4AI techniques."""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            logger.info(f"Fetching URL: {url}")
            response = await client.get(url)
            response.raise_for_status()
            
            # Process the HTML content
            content = await process_page(url, response.text)
            return content
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        return None

async def update_knowledge_item(db: Surreal, item_id: str, content: str) -> bool:
    """Update a knowledge item with processed content."""
    try:
        # Add debug logging
        logger.debug(f"Updating {item_id} with content length: {len(content)}")
        
        # Create update query - with proper escaping
        query = """
        UPDATE $id SET 
            content = $content,
            content_type = 'text/html',
            updated_at = time::now()
        RETURN AFTER;
        """
        
        # Execute query
        result = await db.query(query, {
            "id": item_id,
            "content": content
        })
        
        # Debug the result
        logger.debug(f"Update result: {result}")
        
        if result and len(result) > 0 and "result" in result[0] and result[0]["result"]:
            logger.info(f"Updated content for {item_id}")
            return True
        else:
            logger.warning(f"Failed to update content for {item_id}")
            logger.warning(f"Result: {result}")
            return False
    except Exception as e:
        logger.error(f"Error updating knowledge item: {e}")
        logger.error(f"Exception details: {type(e).__name__}: {e}")
        return False

async def process_batch(db: Surreal, items: List[Dict[str, Any]], batch_size: int = 20) -> int:
    """Process a batch of items."""
    success_count = 0
    batch = items[:batch_size]
    
    logger.info(f"Processing batch of {len(batch)} items")
    
    # Process each item in the batch
    for item in batch:
        item_id = item.get("id")
        url = item.get("source")
        
        if not url:
            logger.warning(f"No source URL for {item_id}")
            continue
        
        # Fetch and process content
        content = await fetch_and_process_url(url)
        if not content:
            logger.warning(f"Failed to fetch content for {url}")
            continue
        
        # Update the knowledge item
        if await update_knowledge_item(db, item_id, content):
            success_count += 1
    
    return success_count

async def main():
    """Main entry point."""
    try:
        # Connect to database
        db = await connect_to_db()
        
        # Get knowledge items that need content update
        items = await get_knowledge_items(db)
        
        if not items:
            logger.info("No items to update")
            await db.close()
            return
        
        # Process in batches of 20
        batch_size = 20
        total_items = len(items)
        success_count = 0
        
        # Calculate number of batches
        max_batches = (total_items + batch_size - 1) // batch_size
        process_batches = max_batches  # Process all batches
        
        logger.info(f"Found {total_items} items to update, which will take {max_batches} batches")
        logger.info(f"Processing all batches ({total_items} items total)")
        
        # Process the specified number of batches
        for batch_num in range(process_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, total_items)
            
            if start_idx >= total_items:
                break
                
            batch_items = items[start_idx:end_idx]
            batch_success = await process_batch(db, batch_items, batch_size)
            success_count += batch_success
            
            logger.info(f"Completed batch {batch_num+1}/{process_batches}: {batch_success} successes")
        
        # Report results
        logger.info(f"Successfully updated {success_count} out of {total_items} items")
        logger.info(f"Knowledge base update complete")
        
        # Close database connection
        await db.close()
    except Exception as e:
        logger.error(f"Error in main function: {e}")

if __name__ == "__main__":
    asyncio.run(main())