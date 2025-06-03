#!/usr/bin/env python3
"""
Check the count of knowledge items in the database
"""

import asyncio
import logging
from surrealdb import Surreal
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("check-count")

async def main():
    """Main function to check knowledge item counts."""
    # Connect to SurrealDB
    db = Surreal("http://localhost:8000")
    await db.connect()
    await db.signin({"user": "root", "pass": "root"})
    await db.use("ptolemies", "knowledge")
    
    logger.info("Connected to SurrealDB")
    
    # Get all knowledge items count
    total_query = "SELECT count() FROM type::table(knowledge_item);"
    total_result = await db.query(total_query)
    
    if total_result and len(total_result) > 0 and "result" in total_result[0]:
        total = total_result[0]["result"][0]["count"]
        logger.info(f"Total knowledge items: {total}")
    
    # Count items with proper content
    content_query = """
    SELECT count() FROM type::table(knowledge_item) 
    WHERE content != NULL AND content != 'None' AND NOT (content CONTAINS 'Content from URL:');
    """
    content_result = await db.query(content_query)
    
    if content_result and len(content_result) > 0 and "result" in content_result[0]:
        content_count = content_result[0]["result"][0]["count"]
        logger.info(f"Knowledge items with proper content: {content_count}")
    
    # Count items that need updating
    needs_update_query = """
    SELECT count() FROM type::table(knowledge_item) 
    WHERE content = NULL OR content = 'None' OR content CONTAINS 'Content from URL:';
    """
    needs_update_result = await db.query(needs_update_query)
    
    if needs_update_result and len(needs_update_result) > 0 and "result" in needs_update_result[0]:
        result_data = needs_update_result[0]["result"]
        if result_data and len(result_data) > 0:
            needs_update_count = result_data[0]["count"]
            logger.info(f"Knowledge items that need updating: {needs_update_count}")
        else:
            logger.info("No items need updating")
    
    # Show a few items that need updating
    sample_query = """
    SELECT id, title, source, content 
    FROM type::table(knowledge_item) 
    WHERE content = NULL OR content = 'None' OR content CONTAINS 'Content from URL:'
    LIMIT 3;
    """
    
    sample_result = await db.query(sample_query)
    
    if sample_result and len(sample_result) > 0 and "result" in sample_result[0]:
        items = sample_result[0]["result"]
        
        if items:
            logger.info(f"\nSample of {len(items)} items that need updating:")
            
            for item in items:
                item_id = item.get("id")
                title = item.get("title")
                source = item.get("source")
                content = item.get("content")
                
                content_preview = content[:50] + "..." if content and len(content) > 50 else content
                
                logger.info(f"Item: {item_id}")
                logger.info(f"Title: {title}")
                logger.info(f"Source: {source}")
                logger.info(f"Content Preview: {content_preview}")
                logger.info("-" * 80)
        else:
            logger.info("No items found that need updating")
    
    # Close the connection
    await db.close()

if __name__ == "__main__":
    asyncio.run(main())