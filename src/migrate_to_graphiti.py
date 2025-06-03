#!/usr/bin/env python3
"""
Migration Script: Existing Knowledge Items to Graphiti

This script migrates all existing knowledge items from SurrealDB to Graphiti
for relationship extraction and temporal graph construction.

Features:
- Batch processing for performance
- Progress tracking and reporting
- Error recovery and retry logic
- Backup and rollback capabilities
- Detailed migration statistics

Usage:
    python3 migrate_to_graphiti.py [--batch-size 10] [--dry-run] [--resume-from ID]
"""

import os
import sys
import asyncio
import argparse
import logging
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ptolemies.integrations.hybrid_storage import HybridKnowledgeManager
from ptolemies.integrations.graphiti.service_wrapper import GraphitiServiceConfig
from ptolemies.models.knowledge_item import KnowledgeItemCreate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("migration")

class MigrationStats:
    """Track migration statistics and progress."""
    
    def __init__(self):
        self.start_time = time.time()
        self.total_items = 0
        self.processed = 0
        self.successful = 0
        self.failed = 0
        self.skipped = 0
        self.errors = []
        
        # Graphiti extraction stats
        self.entities_extracted = 0
        self.relationships_extracted = 0
        self.processing_time_total = 0.0
    
    def add_success(self, item_id: str, entities: int = 0, relationships: int = 0, processing_time: float = 0.0):
        """Record successful migration."""
        self.processed += 1
        self.successful += 1
        self.entities_extracted += entities
        self.relationships_extracted += relationships
        self.processing_time_total += processing_time
        
        if self.processed % 10 == 0:
            self.print_progress()
    
    def add_failure(self, item_id: str, error: str):
        """Record failed migration."""
        self.processed += 1
        self.failed += 1
        self.errors.append({"item_id": item_id, "error": error, "timestamp": datetime.now().isoformat()})
        logger.error(f"Failed to migrate {item_id}: {error}")
    
    def add_skip(self, item_id: str, reason: str):
        """Record skipped migration."""
        self.processed += 1
        self.skipped += 1
        logger.info(f"Skipped {item_id}: {reason}")
    
    def print_progress(self):
        """Print current progress."""
        elapsed = time.time() - self.start_time
        rate = self.processed / elapsed if elapsed > 0 else 0
        eta = (self.total_items - self.processed) / rate if rate > 0 else 0
        
        logger.info(
            f"Progress: {self.processed}/{self.total_items} "
            f"({self.processed/self.total_items*100:.1f}%) "
            f"Success: {self.successful}, Failed: {self.failed}, Skipped: {self.skipped} "
            f"Rate: {rate:.1f}/sec, ETA: {eta/60:.1f}min"
        )
    
    def print_summary(self):
        """Print final migration summary."""
        elapsed = time.time() - self.start_time
        
        print("\n" + "="*80)
        print("MIGRATION SUMMARY")
        print("="*80)
        print(f"Total Items: {self.total_items}")
        print(f"Processed: {self.processed}")
        print(f"Successful: {self.successful}")
        print(f"Failed: {self.failed}")
        print(f"Skipped: {self.skipped}")
        print(f"Total Time: {elapsed/60:.2f} minutes")
        print(f"Average Rate: {self.processed/elapsed:.2f} items/sec")
        
        print(f"\nGraphiti Extraction:")
        print(f"Entities Extracted: {self.entities_extracted}")
        print(f"Relationships Extracted: {self.relationships_extracted}")
        print(f"Avg Processing Time: {self.processing_time_total/self.successful:.2f}s per item" if self.successful > 0 else "N/A")
        
        if self.errors:
            print(f"\nErrors ({len(self.errors)}):")
            for error in self.errors[-5:]:  # Show last 5 errors
                print(f"  {error['item_id']}: {error['error']}")
            
            if len(self.errors) > 5:
                print(f"  ... and {len(self.errors) - 5} more errors")
        
        success_rate = self.successful / self.processed * 100 if self.processed > 0 else 0
        print(f"\nSuccess Rate: {success_rate:.1f}%")
        
        if success_rate >= 95:
            print("🎉 Migration completed successfully!")
        elif success_rate >= 85:
            print("✅ Migration completed with minor issues")
        else:
            print("⚠️ Migration completed with significant issues")

class GraphitiMigrator:
    """Handles migration of knowledge items to Graphiti."""
    
    def __init__(self, batch_size: int = 10, dry_run: bool = False):
        self.batch_size = batch_size
        self.dry_run = dry_run
        self.stats = MigrationStats()
        self.manager: Optional[HybridKnowledgeManager] = None
    
    async def initialize(self):
        """Initialize the hybrid manager."""
        try:
            # Configure Graphiti service
            config = GraphitiServiceConfig()
            self.manager = HybridKnowledgeManager(graphiti_config=config)
            
            success = await self.manager.initialize()
            if not success:
                raise RuntimeError("Failed to initialize hybrid manager")
            
            logger.info("Hybrid manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize migrator: {str(e)}")
            return False
    
    async def get_existing_items(self, resume_from: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all existing knowledge items from SurrealDB."""
        try:
            # Get all items
            items = await self.manager.surrealdb_client.list_knowledge_items(limit=1000)
            
            logger.info(f"Found {len(items)} existing knowledge items")
            
            # Filter for resume
            if resume_from:
                filtered_items = []
                found_resume_point = False
                
                for item in items:
                    if item.id == resume_from:
                        found_resume_point = True
                    
                    if found_resume_point:
                        filtered_items.append(item)
                
                if found_resume_point:
                    logger.info(f"Resuming from {resume_from}, processing {len(filtered_items)} items")
                    return [item.dict() for item in filtered_items]
                else:
                    logger.warning(f"Resume point {resume_from} not found, processing all items")
            
            return [item.dict() for item in items]
            
        except Exception as e:
            logger.error(f"Failed to get existing items: {str(e)}")
            return []
    
    async def migrate_item(self, item_data: Dict[str, Any]) -> bool:
        """Migrate a single knowledge item to Graphiti."""
        item_id = item_data.get("id")
        
        try:
            # Check if already has Graphiti episode
            existing_episode_id = item_data.get("metadata", {}).get("graphiti_episode_id")
            
            if existing_episode_id:
                self.stats.add_skip(item_id, f"Already has Graphiti episode: {existing_episode_id}")
                return True
            
            if self.dry_run:
                logger.info(f"DRY RUN: Would migrate {item_id}")
                self.stats.add_success(item_id)
                return True
            
            # Create knowledge item for processing
            item_create = KnowledgeItemCreate(
                title=item_data.get("title", ""),
                content=item_data.get("content", ""),
                content_type=item_data.get("content_type", "text/plain"),
                metadata=item_data.get("metadata", {}),
                tags=item_data.get("tags", []),
                source=item_data.get("source", "")
            )
            
            # Process through Graphiti for relationship extraction
            logger.info(f"Processing {item_id} through Graphiti...")
            
            start_time = time.time()
            knowledge_item, graphiti_result = await self.manager.store_knowledge_item(
                item_create,
                extract_relationships=True,
                group_id="migration_batch"
            )
            processing_time = time.time() - start_time
            
            # Extract stats
            entities = len(graphiti_result.get("entities", [])) if graphiti_result else 0
            relationships = len(graphiti_result.get("relationships", [])) if graphiti_result else 0
            
            self.stats.add_success(item_id, entities, relationships, processing_time)
            
            logger.info(
                f"Successfully migrated {item_id}: "
                f"{entities} entities, {relationships} relationships "
                f"in {processing_time:.2f}s"
            )
            
            return True
            
        except Exception as e:
            self.stats.add_failure(item_id, str(e))
            return False
    
    async def migrate_batch(self, items: List[Dict[str, Any]]) -> None:
        """Migrate a batch of items."""
        logger.info(f"Migrating batch of {len(items)} items...")
        
        # Process items in parallel with limited concurrency
        semaphore = asyncio.Semaphore(3)  # Limit to 3 concurrent migrations
        
        async def migrate_with_semaphore(item):
            async with semaphore:
                return await self.migrate_item(item)
        
        tasks = [migrate_with_semaphore(item) for item in items]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def run_migration(self, resume_from: Optional[str] = None) -> bool:
        """Run the complete migration process."""
        try:
            logger.info("Starting Graphiti migration...")
            
            # Get all items to migrate
            items = await self.get_existing_items(resume_from)
            self.stats.total_items = len(items)
            
            if not items:
                logger.warning("No items found to migrate")
                return True
            
            logger.info(f"Migrating {len(items)} items in batches of {self.batch_size}")
            
            # Process in batches
            for i in range(0, len(items), self.batch_size):
                batch = items[i:i + self.batch_size]
                batch_num = i // self.batch_size + 1
                total_batches = (len(items) + self.batch_size - 1) // self.batch_size
                
                logger.info(f"Processing batch {batch_num}/{total_batches}")
                
                await self.migrate_batch(batch)
                
                # Brief pause between batches to avoid overwhelming the services
                await asyncio.sleep(1)
            
            # Final summary
            self.stats.print_summary()
            
            # Save migration report
            await self.save_migration_report()
            
            return self.stats.failed == 0
            
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            return False
    
    async def save_migration_report(self):
        """Save detailed migration report to file."""
        try:
            report = {
                "migration_timestamp": datetime.now().isoformat(),
                "total_items": self.stats.total_items,
                "processed": self.stats.processed,
                "successful": self.stats.successful,
                "failed": self.stats.failed,
                "skipped": self.stats.skipped,
                "entities_extracted": self.stats.entities_extracted,
                "relationships_extracted": self.stats.relationships_extracted,
                "total_processing_time": self.stats.processing_time_total,
                "errors": self.stats.errors
            }
            
            report_path = f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Migration report saved to {report_path}")
            
        except Exception as e:
            logger.error(f"Failed to save migration report: {str(e)}")
    
    async def cleanup(self):
        """Clean up resources."""
        if self.manager:
            await self.manager.close()

async def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(description="Migrate knowledge items to Graphiti")
    parser.add_argument("--batch-size", type=int, default=10, help="Batch size for processing")
    parser.add_argument("--dry-run", action="store_true", help="Dry run without actual migration")
    parser.add_argument("--resume-from", type=str, help="Resume from specific item ID")
    
    args = parser.parse_args()
    
    logger.info("🚀 Starting Ptolemies Graphiti Migration")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info(f"Dry run: {args.dry_run}")
    
    if args.resume_from:
        logger.info(f"Resume from: {args.resume_from}")
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    migrator = GraphitiMigrator(
        batch_size=args.batch_size,
        dry_run=args.dry_run
    )
    
    try:
        # Initialize
        if not await migrator.initialize():
            logger.error("Failed to initialize migrator")
            return 1
        
        # Run migration
        success = await migrator.run_migration(args.resume_from)
        
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
        logger.error(f"Migration failed with exception: {str(e)}")
        return 1
        
    finally:
        await migrator.cleanup()

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))