#!/usr/bin/env python3
"""
Create Sample Episodes for Graphiti Testing

This script creates sample episodes based on the crawl targets to test 
the Graphiti service and entity/relationship extraction.
"""

import os
import sys
import asyncio
import json
import logging
import httpx
from datetime import datetime
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class SampleEpisodeCreator:
    """Creates sample episodes for testing Graphiti."""
    
    def __init__(self, graphiti_url: str = "http://localhost:8001"):
        self.graphiti_url = graphiti_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.created_episodes = []
    
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
    
    def load_crawl_targets(self) -> List[Dict[str, Any]]:
        """Load crawl targets as sample content."""
        try:
            with open("data/crawl_targets.json", "r") as f:
                data = json.load(f)
                return data.get("targets", [])
        except Exception as e:
            logger.error(f"Failed to load crawl targets: {e}")
            return []
    
    def create_sample_content(self, target: Dict[str, Any]) -> str:
        """Create sample content based on crawl target."""
        content = f"""
# {target['name']}

## Overview
{target['name']} is a {target['category'].lower()} resource available at {target['url']}.

## Key Technologies
This resource focuses on: {', '.join(target.get('tags', []))}.

## Priority Level
This resource has been marked as {target.get('priority', 'unknown')} priority for the Ptolemies knowledge base.

## Integration Context
The {target['name']} documentation and resources will be crawled to depth {target.get('depth', 2)} levels to gather comprehensive information about {', '.join(target.get('tags', []))}.

## Relevance to DevQ.ai
As part of the DevQ.ai technology stack, {target['name']} provides capabilities for {target['category'].lower()} that align with our goals of building comprehensive AI-powered development tools.

## Related Technologies
Technologies in the same category ({target['category']}) include other frameworks and libraries that work together to create robust development environments.
        """.strip()
        
        return content
    
    async def create_episode(self, target: Dict[str, Any]) -> bool:
        """Create an episode from a crawl target."""
        try:
            content = self.create_sample_content(target)
            
            request_data = {
                "content": content,
                "metadata": {
                    "title": target['name'],
                    "source_url": target['url'],
                    "category": target['category'],
                    "tags": target.get('tags', []),
                    "priority": target.get('priority', 'unknown'),
                    "created_at": datetime.now().isoformat(),
                    "content_type": "knowledge_documentation"
                },
                "group_id": "sample_episodes"
            }
            
            logger.info(f"Creating episode for: {target['name']}")
            
            response = await self.client.post(
                f"{self.graphiti_url}/episodes",
                json=request_data
            )
            
            if response.status_code == 200:
                result = response.json()
                entities = len(result.get("entities", []))
                relationships = len(result.get("relationships", []))
                
                episode_info = {
                    "name": target['name'],
                    "episode_id": result.get('episode_id'),
                    "entities": entities,
                    "relationships": relationships,
                    "processing_time": result.get('processing_time', 0)
                }
                
                self.created_episodes.append(episode_info)
                
                logger.info(
                    f"✅ Created episode {result.get('episode_id')}: "
                    f"{entities} entities, {relationships} relationships "
                    f"in {result.get('processing_time', 0):.2f}s"
                )
                return True
            else:
                logger.error(f"Failed to create episode: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating episode for {target['name']}: {e}")
            return False
    
    async def search_entities(self, query: str) -> List[Dict[str, Any]]:
        """Search for entities in the knowledge graph."""
        try:
            response = await self.client.get(
                f"{self.graphiti_url}/entities/search",
                params={"query": query, "limit": 10}
            )
            
            if response.status_code == 200:
                return response.json().get("results", [])
            else:
                logger.error(f"Entity search failed: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error searching entities: {e}")
            return []
    
    async def search_relationships(self, query: str) -> List[Dict[str, Any]]:
        """Search for relationships in the knowledge graph."""
        try:
            response = await self.client.get(
                f"{self.graphiti_url}/relationships/search",
                params={"query": query, "limit": 10}
            )
            
            if response.status_code == 200:
                return response.json().get("results", [])
            else:
                logger.error(f"Relationship search failed: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error searching relationships: {e}")
            return []
    
    async def run_sample_creation(self) -> bool:
        """Create sample episodes and test the system."""
        try:
            logger.info("🚀 Creating sample episodes for Graphiti testing")
            
            # Check Graphiti service
            if not await self.check_graphiti_health():
                logger.error("Graphiti service is not ready")
                return False
            
            # Load crawl targets
            targets = self.load_crawl_targets()
            if not targets:
                logger.error("No crawl targets found")
                return False
            
            logger.info(f"Creating episodes for {len(targets)} targets")
            
            # Create episodes
            successful = 0
            for i, target in enumerate(targets, 1):
                logger.info(f"Processing target {i}/{len(targets)}: {target['name']}")
                
                if await self.create_episode(target):
                    successful += 1
                
                # Brief pause between episodes
                await asyncio.sleep(1)
            
            logger.info(f"📊 Created {successful}/{len(targets)} episodes successfully")
            
            # Test searches after creating episodes
            if successful > 0:
                logger.info("🔍 Testing entity and relationship searches...")
                
                # Search for common entities
                test_queries = ["AI", "Python", "database", "framework", "pydantic"]
                
                for query in test_queries:
                    entities = await self.search_entities(query)
                    relationships = await self.search_relationships(query)
                    
                    logger.info(f"Query '{query}': {len(entities)} entities, {len(relationships)} relationships")
            
            # Print summary
            logger.info("📋 Episode Creation Summary:")
            for episode in self.created_episodes:
                logger.info(
                    f"  {episode['name']}: {episode['entities']} entities, "
                    f"{episode['relationships']} relationships "
                    f"({episode['processing_time']:.2f}s)"
                )
            
            return successful > 0
            
        except Exception as e:
            logger.error(f"Sample creation failed: {e}")
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
    
    # Create sample episode creator
    creator = SampleEpisodeCreator()
    
    try:
        # Run sample creation
        success = await creator.run_sample_creation()
        
        if success:
            logger.info("✅ Sample episode creation completed successfully!")
            return 0
        else:
            logger.error("❌ Sample episode creation failed")
            return 1
            
    except KeyboardInterrupt:
        logger.info("Sample creation interrupted by user")
        return 1
        
    except Exception as e:
        logger.error(f"Sample creation failed: {e}")
        return 1
        
    finally:
        await creator.close()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)