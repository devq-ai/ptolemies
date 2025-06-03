#!/usr/bin/env python3
"""
Check a specific knowledge item in the database
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
logger = logging.getLogger("check-specific-item")

async def main():
    """Main function to check a specific knowledge item."""
    # Connect to SurrealDB
    db = Surreal("http://localhost:8000")
    await db.connect()
    await db.signin({"user": "root", "pass": "root"})
    await db.use("ptolemies", "knowledge")
    
    logger.info("Connected to SurrealDB")
    
    # Check specific item
    item_id = "knowledge_item:url_https___www_pymc_io__sources_welcome_md_txt"
    
    # Try direct selection first
    result = await db.select(item_id)
    
    if result and len(result) > 0:
        logger.info(f"Direct select result: {result}")
    else:
        logger.info(f"No result from direct select")
    
    # Try query
    query = """
    SELECT * FROM type::table(knowledge_item) 
    WHERE id = $id;
    """
    
    query_result = await db.query(query, {"id": item_id})
    
    if query_result and len(query_result) > 0 and "result" in query_result[0]:
        items = query_result[0]["result"]
        logger.info(f"Query result: {items}")
    else:
        logger.info(f"No result from query")
    
    # Update the item directly
    test_content = f"Test direct update: {asyncio.get_event_loop().time()}"
    
    update_query = """
    UPDATE $id SET 
        content = $content,
        content_type = 'text/plain',
        updated_at = time::now()
    RETURN AFTER;
    """
    
    update_result = await db.query(update_query, {
        "id": item_id,
        "content": test_content
    })
    
    logger.info(f"Update result: {update_result}")
    
    # Check if update was successful
    check_result = await db.select(item_id)
    logger.info(f"Check after update: {check_result}")
    
    # Close the connection
    await db.close()

if __name__ == "__main__":
    asyncio.run(main())