#!/usr/bin/env python3
"""
Simple SurrealDB to Neo4j Episode Migration Script

This script reads knowledge items from SurrealDB (via existing stored files)
and creates episodes in Neo4j using the Graphiti service.

Based on:
- https://help.getzep.com/graphiti/graphiti/adding-episodes
- https://help.getzep.com/graphiti/graphiti/custom-entity-types

Usage:
    python3 migrate_surrealdb_to_neo4j.py
"""

import os
import sys
import asyncio
import json
import logging
import httpx
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class SurrealDBToGraphitiMigrator:
    """Migrates SurrealDB knowledge items to Graphiti episodes."""
    
    def __init__(self, graphiti_url: str = "http://localhost:8001"):
        self.graphiti_url = graphiti_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.processed = 0
        self.successful = 0
        self.failed = 0
    
    async def check_graphiti_health(self) -> bool:
        """Check if Graphiti service is running."""
        try:
            response = await self.client.get(f"{self.graphiti_url}/health")
            if response.status_code == 200:
                health_data = response.json()
                logger.info(f"Graphiti service status: {health_data.get('status')}")
                return health_data.get('graphiti_ready', False)
            return False
        except Exception as e:
            logger.error(f"Failed to check Graphiti health: {e}")
            return False
    
    def find_knowledge_files(self) -> List[Path]:
        """Find existing knowledge files from crawl operations."""
        data_dir = Path("data/files")
        knowledge_files = []
        
        if data_dir.exists():
            # Find JSON files that might contain knowledge items
            for file_path in data_dir.rglob("*.json"):
                knowledge_files.append(file_path)
            
            # Find markdown files
            for file_path in data_dir.rglob("*.md"):
                knowledge_files.append(file_path)
            
            # Find text files
            for file_path in data_dir.rglob("*.txt"):
                knowledge_files.append(file_path)
        
        logger.info(f"Found {len(knowledge_files)} potential knowledge files")
        return knowledge_files
    
    def extract_content_from_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Extract content from a file for episode creation."""
        try:
            content = ""
            metadata = {}
            
            if file_path.suffix == ".json":
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Handle different JSON structures
                if isinstance(data, dict):
                    content = data.get('content', '') or data.get('text', '') or str(data)
                    metadata = {k: v for k, v in data.items() if k not in ['content', 'text']}
                elif isinstance(data, list) and data:
                    # Take first item if it's a list
                    content = str(data[0]) if data else ""
                else:
                    content = str(data)
            
            elif file_path.suffix in [".md", ".txt"]:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            
            else:
                # Try to read as text
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            
            if not content.strip():
                return None
            
            # Create episode data
            episode_data = {
                "title": file_path.stem,
                "content": content,
                "source": str(file_path),
                "metadata": {
                    **metadata,
                    "file_type": file_path.suffix,
                    "file_size": file_path.stat().st_size,
                    "modified_time": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                }
            }
            
            return episode_data
            
        except Exception as e:
            logger.error(f"Failed to extract content from {file_path}: {e}")
            return None
    
    async def create_graphiti_episode(self, episode_data: Dict[str, Any]) -> bool:
        """Create an episode in Graphiti."""
        try:
            # Prepare episode request based on Graphiti API
            request_data = {
                "content": episode_data["content"],
                "metadata": {
                    "title": episode_data["title"],
                    "source": episode_data["source"],
                    **episode_data.get("metadata", {})
                },
                "group_id": "migration_batch"
            }
            
            logger.info(f"Creating episode for: {episode_data['title']}")
            
            response = await self.client.post(
                f"{self.graphiti_url}/episodes",
                json=request_data
            )
            
            if response.status_code == 200:
                result = response.json()
                entities = len(result.get("entities", []))
                relationships = len(result.get("relationships", []))
                
                logger.info(
                    f"✅ Created episode {result.get('episode_id')}: "
                    f"{entities} entities, {relationships} relationships"
                )
                self.successful += 1
                return True
            else:
                logger.error(f"Failed to create episode: {response.status_code} - {response.text}")
                self.failed += 1
                return False
                
        except Exception as e:
            logger.error(f"Error creating episode for {episode_data['title']}: {e}")
            self.failed += 1
            return False
    
    async def migrate_file(self, file_path: Path) -> bool:
        """Migrate a single file to Graphiti."""
        self.processed += 1
        
        # Extract content
        episode_data = self.extract_content_from_file(file_path)
        if not episode_data:
            logger.warning(f"Skipping {file_path}: no content extracted")
            return False
        
        # Create episode
        return await self.create_graphiti_episode(episode_data)
    
    async def run_migration(self, max_files: int = 50) -> bool:
        """Run the complete migration process."""
        try:
            logger.info("🚀 Starting SurrealDB to Graphiti migration")
            
            # Check Graphiti service
            if not await self.check_graphiti_health():
                logger.error("Graphiti service is not ready")
                return False
            
            # Find knowledge files
            knowledge_files = self.find_knowledge_files()
            
            if not knowledge_files:
                logger.warning("No knowledge files found to migrate")
                return True
            
            # Limit files for initial migration
            files_to_process = knowledge_files[:max_files]
            logger.info(f"Processing {len(files_to_process)} files (limited from {len(knowledge_files)})")
            
            # Process files sequentially to avoid overwhelming the service
            for i, file_path in enumerate(files_to_process, 1):
                logger.info(f"Processing file {i}/{len(files_to_process)}: {file_path.name}")
                
                await self.migrate_file(file_path)
                
                # Brief pause between files
                await asyncio.sleep(0.5)
            
            # Print summary
            logger.info("📊 Migration Summary:")
            logger.info(f"  Processed: {self.processed}")
            logger.info(f"  Successful: {self.successful}")
            logger.info(f"  Failed: {self.failed}")
            
            success_rate = (self.successful / self.processed * 100) if self.processed > 0 else 0
            logger.info(f"  Success Rate: {success_rate:.1f}%")
            
            return self.failed == 0
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

async def main():
    """Main function."""
    # Load environment
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    # Create migrator
    migrator = SurrealDBToGraphitiMigrator()
    
    try:
        # Run migration
        success = await migrator.run_migration(max_files=20)  # Start with 20 files
        
        if success:
            logger.info("✅ Migration completed successfully!")
            return 0
        else:
            logger.error("❌ Migration completed with errors")
            return 1
            
    except KeyboardInterrupt:
        logger.info("Migration interrupted by user")
        return 1
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return 1
        
    finally:
        await migrator.close()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)