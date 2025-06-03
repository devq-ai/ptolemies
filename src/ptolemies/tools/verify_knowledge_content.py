#!/usr/bin/env python3
"""
Verify that knowledge items have been updated with proper content
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
logger = logging.getLogger("verify-knowledge-content")

async def main():
    """Main function to verify knowledge item content."""
    # Connect to SurrealDB
    db = Surreal("http://localhost:8000")
    await db.connect()
    await db.signin({"user": "root", "pass": "root"})
    await db.use("ptolemies", "knowledge")
    
    logger.info("Connected to SurrealDB")
    
    # Get a sample of knowledge items
    query = """
    SELECT id, title, source, content, content_type 
    FROM type::table(knowledge_item) 
    LIMIT 5;
    """
    
    result = await db.query(query)
    
    if result and len(result) > 0 and "result" in result[0]:
        items = result[0]["result"]
        logger.info(f"Found {len(items)} knowledge items")
        
        for item in items:
            item_id = item.get("id")
            title = item.get("title")
            source = item.get("source")
            content = item.get("content")
            content_type = item.get("content_type")
            
            content_preview = content[:200] + "..." if content and len(content) > 200 else content
            
            logger.info(f"Item: {item_id}")
            logger.info(f"Title: {title}")
            logger.info(f"Source: {source}")
            logger.info(f"Content Type: {content_type}")
            logger.info(f"Content Preview: {content_preview}")
            logger.info("-" * 80)
    
    # Get total count
    total_query = "SELECT count() FROM type::table(knowledge_item);"
    total_result = await db.query(total_query)
    
    if total_result and len(total_result) > 0 and "result" in total_result[0]:
        total = total_result[0]["result"][0]["count"]
        logger.info(f"Total knowledge items: {total}")
    
    # Check content directly
    sample_query = """
    SELECT id, title, content FROM type::table(knowledge_item) LIMIT 20;
    """
    
    sample_result = await db.query(sample_query)
    
    if sample_result and len(sample_result) > 0 and "result" in sample_result[0]:
        items = sample_result[0]["result"]
        
        placeholder_count = 0
        proper_count = 0
        binary_count = 0
        failed_count = 0
        
        for item in items:
            content = item.get("content", "")
            
            if not content:
                continue
                
            if "Content from URL:" in content and len(content) < 100:
                placeholder_count += 1
            elif "Binary content from URL:" in content:
                binary_count += 1
            elif "Failed to extract content" in content:
                failed_count += 1
            else:
                proper_count += 1
        
        logger.info(f"Sample analysis (from 20 items):")
        logger.info(f"  - With placeholder content: {placeholder_count}")
        logger.info(f"  - With binary content: {binary_count}")
        logger.info(f"  - With failed content: {failed_count}")
        logger.info(f"  - With proper content: {proper_count}")
    
    # Examine some updated items in detail
    updated_query = """
    SELECT id, title, source, content, content_type 
    FROM type::table(knowledge_item) 
    WHERE content != NULL AND content != 'None' AND NOT (content CONTAINS 'Content from URL:')
    LIMIT 3;
    """
    
    updated_result = await db.query(updated_query)
    
    if updated_result and len(updated_result) > 0 and "result" in updated_result[0]:
        items = updated_result[0]["result"]
        logger.info(f"\nFound {len(items)} updated knowledge items to examine:")
        
        for item in items:
            item_id = item.get("id")
            title = item.get("title")
            source = item.get("source")
            content = item.get("content")
            
            content_preview = content[:200] + "..." if content and len(content) > 200 else content
            
            logger.info(f"\nItem: {item_id}")
            logger.info(f"Title: {title}")
            logger.info(f"Source: {source}")
            logger.info(f"Content Preview: {content_preview}")
    else:
        logger.info("No updated items found with proper content")
    
    # Close the connection
    await db.close()

if __name__ == "__main__":
    asyncio.run(main())