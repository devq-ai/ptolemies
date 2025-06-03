#!/usr/bin/env python3
"""
Bulk Migration to Graphiti

Processes content files and feeds them to Graphiti to create a massive temporal knowledge graph.
This will automatically extract entities, relationships, and facts from your content.

Usage:
    python bulk_migrate_to_graphiti.py --directory /path/to/content
    python bulk_migrate_to_graphiti.py --file single_file.txt
    python bulk_migrate_to_graphiti.py --sample 10  # Process only 10 files for testing
"""

import asyncio
import logging
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import httpx
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("bulk_migration")

# Configuration
GRAPHITI_API_URL = "http://localhost:8001"

class GraphitiMigrator:
    """Bulk migrator for feeding content to Graphiti"""
    
    def __init__(self, base_url: str = GRAPHITI_API_URL):
        self.base_url = base_url
        self.session = None
        self.processed_count = 0
        self.failed_count = 0
        self.entities_created = 0
        self.relationships_created = 0
    
    async def connect(self):
        """Initialize HTTP client"""
        self.session = httpx.AsyncClient(timeout=120.0)  # Longer timeout for processing
    
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
    
    async def process_content(self, content: str, metadata: Dict[str, Any], group_id: str = "bulk_import") -> Optional[Dict[str, Any]]:
        """Process content through Graphiti"""
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
                result = response.json()
                self.processed_count += 1
                self.entities_created += len(result.get('entities', []))
                self.relationships_created += len(result.get('relationships', []))
                return result
            else:
                logger.error(f"Episode creation failed: {response.status_code} - {response.text}")
                self.failed_count += 1
                return None
                
        except Exception as e:
            logger.error(f"Error processing content: {str(e)}")
            self.failed_count += 1
            return None
    
    def extract_content_from_file(self, file_path: Path) -> Dict[str, Any]:
        """Extract content and metadata from a file"""
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Skip empty files
            if not content.strip():
                return None
            
            # Create metadata
            metadata = {
                "source": "file_migration",
                "file_path": str(file_path),
                "file_name": file_path.name,
                "file_extension": file_path.suffix,
                "file_size": len(content),
                "migrated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Determine group_id based on file path/name
            group_id = "bulk_import"
            if "docs" in str(file_path).lower():
                group_id = "documentation"
            elif any(ext in file_path.suffix.lower() for ext in ['.md', '.txt']):
                group_id = "documents"
            elif "config" in file_path.name.lower():
                group_id = "configuration"
            elif any(keyword in str(file_path).lower() for keyword in ['api', 'code', 'src']):
                group_id = "technical"
            
            return {
                "content": content,
                "metadata": metadata,
                "group_id": group_id
            }
            
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            return None
    
    async def migrate_directory(self, directory: Path, pattern: str = "*", max_files: Optional[int] = None) -> None:
        """Migrate all files in a directory"""
        logger.info(f"Scanning directory: {directory}")
        
        # Find all files matching pattern
        if directory.is_file():
            files = [directory]
        else:
            files = list(directory.rglob(pattern))
            # Filter to actual files (not directories)
            files = [f for f in files if f.is_file()]
        
        if max_files:
            files = files[:max_files]
            logger.info(f"Limited to first {max_files} files")
        
        logger.info(f"Found {len(files)} files to process")
        
        # Process each file
        for i, file_path in enumerate(files, 1):
            try:
                logger.info(f"Processing {i}/{len(files)}: {file_path.name}")
                
                # Extract content
                file_data = self.extract_content_from_file(file_path)
                if not file_data:
                    logger.warning(f"Skipping {file_path.name} - no content")
                    continue
                
                # Add title to content if filename is meaningful
                title = file_path.stem.replace('_', ' ').replace('-', ' ').title()
                enhanced_content = f"# {title}\n\n{file_data['content']}"
                
                # Process through Graphiti
                result = await self.process_content(
                    enhanced_content,
                    file_data['metadata'],
                    file_data['group_id']
                )
                
                if result:
                    entities = len(result.get('entities', []))
                    relationships = len(result.get('relationships', []))
                    processing_time = result.get('processing_time', 0)
                    
                    logger.info(f"✅ {file_path.name}: {entities} entities, {relationships} relationships ({processing_time:.1f}s)")
                else:
                    logger.error(f"❌ Failed: {file_path.name}")
                
                # Add small delay to avoid overwhelming services
                await asyncio.sleep(0.5)
                
                # Progress report every 10 files
                if i % 10 == 0:
                    logger.info(f"Progress: {i}/{len(files)} files, {self.processed_count} successful, {self.failed_count} failed")
                    logger.info(f"Created: {self.entities_created} entities, {self.relationships_created} relationships")
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {str(e)}")
                self.failed_count += 1
        
        # Final summary
        logger.info("Migration completed!")
        logger.info(f"📊 Final Statistics:")
        logger.info(f"   Files processed: {self.processed_count}")
        logger.info(f"   Files failed: {self.failed_count}")
        logger.info(f"   Entities created: {self.entities_created}")
        logger.info(f"   Relationships created: {self.relationships_created}")
        logger.info(f"   Success rate: {(self.processed_count / (self.processed_count + self.failed_count) * 100):.1f}%")

async def main():
    parser = argparse.ArgumentParser(description="Bulk migrate content to Graphiti temporal knowledge graph")
    parser.add_argument("--directory", "-d", type=str, help="Directory to process")
    parser.add_argument("--file", "-f", type=str, help="Single file to process")
    parser.add_argument("--pattern", "-p", type=str, default="*", help="File pattern to match (default: *)")
    parser.add_argument("--sample", "-s", type=int, help="Process only N files for testing")
    parser.add_argument("--group", "-g", type=str, default="bulk_import", help="Group ID for episodes")
    
    args = parser.parse_args()
    
    if not args.directory and not args.file:
        logger.error("Must specify either --directory or --file")
        sys.exit(1)
    
    # Initialize migrator
    migrator = GraphitiMigrator()
    
    try:
        await migrator.connect()
        
        # Health check
        if not await migrator.health_check():
            logger.error("Graphiti service is not healthy. Please start it first.")
            sys.exit(1)
        
        logger.info("✅ Graphiti service is healthy")
        
        # Process content
        if args.file:
            file_path = Path(args.file)
            await migrator.migrate_directory(file_path, max_files=1)
        else:
            directory = Path(args.directory)
            await migrator.migrate_directory(directory, args.pattern, args.sample)
        
    except KeyboardInterrupt:
        logger.info("Migration interrupted by user")
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        sys.exit(1)
    finally:
        await migrator.close()

if __name__ == "__main__":
    # Create some sample content for testing if no args provided
    if len(sys.argv) == 1:
        print("Bulk Migration to Graphiti")
        print("Usage examples:")
        print("  python bulk_migrate_to_graphiti.py --directory ~/Documents --sample 10")
        print("  python bulk_migrate_to_graphiti.py --file important_doc.txt")
        print("  python bulk_migrate_to_graphiti.py --directory /path/to/docs --pattern '*.md'")
        
        # Create sample content
        print("\nCreating sample content for testing...")
        
        sample_content = [
            {
                "title": "Artificial Intelligence Overview",
                "content": """
                Artificial Intelligence (AI) is a branch of computer science that aims to create intelligent machines. 
                Machine Learning is a subset of AI that enables computers to learn without being explicitly programmed.
                Deep Learning uses neural networks with multiple layers to model complex patterns.
                Companies like OpenAI, Google, and Microsoft are leading AI research.
                """,
                "group": "ai_research"
            },
            {
                "title": "Technology Companies",
                "content": """
                Meta (formerly Facebook) was founded by Mark Zuckerberg in 2004 and focuses on social media and virtual reality.
                Netflix revolutionized streaming entertainment and was founded by Reed Hastings and Marc Randolph.
                Spotify is a music streaming platform founded by Daniel Ek and Martin Lorentzon in Sweden.
                """,
                "group": "tech_companies"
            },
            {
                "title": "Programming Languages",
                "content": """
                Python is a high-level programming language created by Guido van Rossum.
                JavaScript was developed by Brendan Eich at Netscape Communications.
                TypeScript is a superset of JavaScript developed by Microsoft.
                React is a JavaScript library for building user interfaces, created by Facebook.
                """,
                "group": "programming"
            }
        ]
        
        # Run sample migration
        async def run_sample():
            migrator = GraphitiMigrator()
            try:
                await migrator.connect()
                
                if not await migrator.health_check():
                    print("❌ Graphiti service not available")
                    return
                
                print("✅ Processing sample content...")
                
                for item in sample_content:
                    result = await migrator.process_content(
                        f"# {item['title']}\n\n{item['content']}",
                        {"source": "sample_data", "title": item['title']},
                        item['group']
                    )
                    
                    if result:
                        entities = len(result.get('entities', []))
                        relationships = len(result.get('relationships', []))
                        print(f"✅ {item['title']}: {entities} entities, {relationships} relationships")
                
                print(f"\n📊 Sample Migration Complete:")
                print(f"   Entities created: {migrator.entities_created}")
                print(f"   Relationships created: {migrator.relationships_created}")
                
            finally:
                await migrator.close()
        
        asyncio.run(run_sample())
    else:
        asyncio.run(main())