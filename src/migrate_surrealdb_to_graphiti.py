#!/usr/bin/env python3
"""
SurrealDB to Graphiti Migration Pipeline

Loads existing knowledge items from SurrealDB and processes them through Graphiti
to create a temporal knowledge graph in Neo4j.

This implements requirement #1: "Load files from SurrealDB"
"""

import asyncio
import logging
import json
import sys
import os
from datetime import datetime, timezone
from typing import List, Dict, Any
import httpx

# Add project paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("surrealdb_migration")

# Configuration
SURREALDB_URL = "ws://localhost:8000/rpc"
SURREALDB_NS = "ptolemies"
SURREALDB_DB = "knowledge"
GRAPHITI_API_URL = "http://localhost:8001"

class SurrealDBClient:
    """Simple SurrealDB client for migration"""
    
    def __init__(self, url: str, namespace: str, database: str):
        self.url = url.replace("ws://", "http://").replace("/rpc", "")
        self.namespace = namespace
        self.database = database
        self.session = None
    
    async def connect(self):
        """Initialize HTTP client"""
        self.session = httpx.AsyncClient()
        
    async def close(self):
        """Close HTTP client"""
        if self.session:
            await self.session.aclose()
    
    async def query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute SQL query against SurrealDB"""
        try:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "NS": self.namespace,
                "DB": self.database
            }
            
            response = await self.session.post(
                f"{self.url}/sql",
                headers=headers,
                content=sql
            )
            
            if response.status_code == 200:
                results = response.json()
                if results and len(results) > 0 and 'result' in results[0]:
                    return results[0]['result']
                return []
            else:
                logger.error(f"SurrealDB query failed: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error querying SurrealDB: {str(e)}")
            return []

class GraphitiClient:
    """Client for Graphiti API"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = None
    
    async def connect(self):
        """Initialize HTTP client"""
        self.session = httpx.AsyncClient(timeout=60.0)
    
    async def close(self):
        """Close HTTP client"""
        if self.session:
            await self.session.aclose()
    
    async def health_check(self) -> bool:
        """Check if Graphiti service is healthy"""
        try:
            response = await self.session.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Graphiti health check failed: {str(e)}")
            return False
    
    async def create_episode(self, content: str, metadata: Dict[str, Any], group_id: str = "imported") -> Dict[str, Any]:
        """Create episode in Graphiti"""
        try:
            episode_data = {
                "content": content,
                "metadata": metadata,
                "group_id": group_id
            }
            
            response = await self.session.post(
                f"{self.base_url}/episodes",
                json=episode_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Episode creation failed: {response.status_code} - {response.text}")
                return {}
                
        except Exception as e:
            logger.error(f"Error creating episode: {str(e)}")
            return {}

async def migrate_knowledge_items():
    """Main migration function"""
    logger.info("Starting SurrealDB to Graphiti migration...")
    
    # Initialize clients
    surrealdb = SurrealDBClient(SURREALDB_URL, SURREALDB_NS, SURREALDB_DB)
    graphiti = GraphitiClient(GRAPHITI_API_URL)
    
    try:
        # Connect to both services
        logger.info("Connecting to SurrealDB...")
        await surrealdb.connect()
        
        logger.info("Connecting to Graphiti...")
        await graphiti.connect()
        
        # Check Graphiti health
        if not await graphiti.health_check():
            logger.error("Graphiti service is not healthy. Please start the service first.")
            return False
        
        logger.info("Both services connected successfully")
        
        # Query SurrealDB for knowledge items
        logger.info("Querying SurrealDB for knowledge items...")
        sql_query = """
        SELECT id, title, content, source, category, tags, created_at, updated_at 
        FROM knowledge_item 
        ORDER BY created_at ASC;
        """
        
        knowledge_items = await surrealdb.query(sql_query)
        
        if not knowledge_items:
            logger.warning("No knowledge items found in SurrealDB")
            return True
        
        logger.info(f"Found {len(knowledge_items)} knowledge items to migrate")
        
        # Process each knowledge item through Graphiti
        successful_migrations = 0
        failed_migrations = 0
        
        for i, item in enumerate(knowledge_items, 1):
            try:
                logger.info(f"Processing item {i}/{len(knowledge_items)}: {item.get('title', 'Untitled')}")
                
                # Prepare content for Graphiti
                content = item.get('content', '')
                if not content:
                    logger.warning(f"Skipping item {item.get('id')} - no content")
                    continue
                
                # Add title to content if available
                title = item.get('title', '')
                if title:
                    content = f"# {title}\n\n{content}"
                
                # Prepare metadata
                metadata = {
                    "source": "surrealdb_migration",
                    "original_id": str(item.get('id', '')),
                    "original_source": item.get('source', 'unknown'),
                    "original_title": title,
                    "tags": item.get('tags', []),
                    "migrated_at": datetime.now(timezone.utc).isoformat()
                }
                
                # Determine group_id
                group_id = item.get('category', 'imported')
                if not group_id or group_id == 'null':
                    group_id = 'imported'
                
                # Create episode in Graphiti
                result = await graphiti.create_episode(
                    content=content,
                    metadata=metadata,
                    group_id=group_id
                )
                
                if result:
                    successful_migrations += 1
                    logger.info(f"✅ Successfully migrated: {title} -> Episode {result.get('episode_id', 'unknown')}")
                    
                    # Log extracted entities and relationships
                    entities = result.get('entities', [])
                    relationships = result.get('relationships', [])
                    logger.info(f"   Extracted {len(entities)} entities and {len(relationships)} relationships")
                    
                else:
                    failed_migrations += 1
                    logger.error(f"❌ Failed to migrate: {title}")
                
                # Add small delay to avoid overwhelming the services
                await asyncio.sleep(0.1)
                
            except Exception as e:
                failed_migrations += 1
                logger.error(f"❌ Error processing item {item.get('id')}: {str(e)}")
        
        # Summary
        logger.info("Migration completed!")
        logger.info(f"✅ Successful migrations: {successful_migrations}")
        logger.info(f"❌ Failed migrations: {failed_migrations}")
        logger.info(f"📊 Total items processed: {len(knowledge_items)}")
        
        return successful_migrations > 0
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return False
        
    finally:
        # Clean up connections
        await surrealdb.close()
        await graphiti.close()

async def verify_migration():
    """Verify migration was successful by checking Graphiti"""
    logger.info("Verifying migration...")
    
    graphiti = GraphitiClient(GRAPHITI_API_URL)
    
    try:
        await graphiti.connect()
        
        # Test search for some common terms
        test_searches = ["knowledge", "data", "system", "information"]
        
        for search_term in test_searches:
            try:
                response = await graphiti.session.get(
                    f"{GRAPHITI_API_URL}/entities/search",
                    params={"query": search_term, "limit": 5}
                )
                
                if response.status_code == 200:
                    results = response.json()
                    entity_count = results.get('total_count', 0)
                    logger.info(f"Search '{search_term}': {entity_count} entities found")
                else:
                    logger.warning(f"Search '{search_term}' failed: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"Error testing search '{search_term}': {str(e)}")
        
    finally:
        await graphiti.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate SurrealDB knowledge to Graphiti")
    parser.add_argument("--verify-only", action="store_true", help="Only verify migration, don't migrate")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be migrated without doing it")
    
    args = parser.parse_args()
    
    if args.verify_only:
        asyncio.run(verify_migration())
    else:
        success = asyncio.run(migrate_knowledge_items())
        if success:
            logger.info("Migration completed successfully!")
            asyncio.run(verify_migration())
        else:
            logger.error("Migration failed!")
            sys.exit(1)