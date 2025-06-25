#!/usr/bin/env python3
"""
Ptolemies Database Configuration Migration Script

Migrates data from incorrect SurrealDB configuration to the correct configuration
specified in .env file:
- Correct: namespace=ptolemies, database=knowledge
- Previous: namespace=knowledge, database=ptolemies
"""

import asyncio
import logging
import os
from surrealdb import Surreal
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from .env
SURREALDB_URL = os.getenv("SURREALDB_URL", "ws://localhost:8000/rpc")
SURREALDB_USERNAME = os.getenv("SURREALDB_USERNAME", "root")
SURREALDB_PASSWORD = os.getenv("SURREALDB_PASSWORD", "root")
CORRECT_NAMESPACE = os.getenv("SURREALDB_NAMESPACE", "ptolemies")
CORRECT_DATABASE = os.getenv("SURREALDB_DATABASE", "knowledge")

# Previous incorrect configuration
INCORRECT_NAMESPACE = "knowledge"
INCORRECT_DATABASE = "ptolemies"

async def check_data_exists(db, namespace, database):
    """Check if data exists in a specific namespace/database."""
    try:
        await db.use(namespace, database)
        result = await db.query("SELECT count() FROM document_chunks GROUP ALL;")
        if result and len(result) > 0 and len(result[0]) > 0:
            return result[0][0].get('count', 0)
        return 0
    except Exception as e:
        logger.warning(f"Could not check data in {namespace}/{database}: {e}")
        return 0

async def export_data(db, namespace, database):
    """Export all data from a specific namespace/database."""
    await db.use(namespace, database)
    
    # Export document chunks
    chunks_result = await db.query("SELECT * FROM document_chunks;")
    chunks = chunks_result[0] if chunks_result and len(chunks_result) > 0 else []
    
    logger.info(f"Found {len(chunks)} document chunks in {namespace}/{database}")
    
    return {
        'document_chunks': chunks
    }

async def import_data(db, namespace, database, data):
    """Import data into a specific namespace/database."""
    await db.use(namespace, database)
    
    # Import document chunks
    if data.get('document_chunks'):
        logger.info(f"Importing {len(data['document_chunks'])} document chunks...")
        
        for chunk in data['document_chunks']:
            try:
                # Remove the id field if it exists to avoid conflicts
                chunk_data = {k: v for k, v in chunk.items() if k != 'id'}
                
                # Create new record
                await db.create("document_chunks", chunk_data)
                
            except Exception as e:
                logger.error(f"Error importing chunk: {e}")
                continue
        
        logger.info("Document chunks import completed")

async def migrate_database_config():
    """Main migration function."""
    logger.info("🔄 Starting Ptolemies Database Configuration Migration")
    logger.info(f"Source: {INCORRECT_NAMESPACE}/{INCORRECT_DATABASE}")
    logger.info(f"Target: {CORRECT_NAMESPACE}/{CORRECT_DATABASE}")
    
    # Connect to SurrealDB
    db = Surreal()
    try:
        await db.connect(SURREALDB_URL)
        await db.signin({"user": SURREALDB_USERNAME, "pass": SURREALDB_PASSWORD})
        logger.info(f"✅ Connected to SurrealDB at {SURREALDB_URL}")
        
        # Check data in incorrect location
        incorrect_count = await check_data_exists(db, INCORRECT_NAMESPACE, INCORRECT_DATABASE)
        logger.info(f"📊 Data in incorrect location ({INCORRECT_NAMESPACE}/{INCORRECT_DATABASE}): {incorrect_count} chunks")
        
        # Check data in correct location
        correct_count = await check_data_exists(db, CORRECT_NAMESPACE, CORRECT_DATABASE)
        logger.info(f"📊 Data in correct location ({CORRECT_NAMESPACE}/{CORRECT_DATABASE}): {correct_count} chunks")
        
        if incorrect_count == 0:
            if correct_count > 0:
                logger.info("✅ No migration needed - data already in correct location")
            else:
                logger.info("ℹ️  No data found in either location - nothing to migrate")
            return
        
        if correct_count > 0:
            logger.warning(f"⚠️  Data already exists in target location ({correct_count} chunks)")
            response = input("Do you want to proceed? This will duplicate data. (y/N): ")
            if response.lower() != 'y':
                logger.info("Migration cancelled by user")
                return
        
        # Export data from incorrect location
        logger.info("📦 Exporting data from incorrect location...")
        exported_data = await export_data(db, INCORRECT_NAMESPACE, INCORRECT_DATABASE)
        
        if not exported_data.get('document_chunks'):
            logger.info("ℹ️  No document chunks found to migrate")
            return
        
        # Import data to correct location
        logger.info("📥 Importing data to correct location...")
        await import_data(db, CORRECT_NAMESPACE, CORRECT_DATABASE, exported_data)
        
        # Verify migration
        final_count = await check_data_exists(db, CORRECT_NAMESPACE, CORRECT_DATABASE)
        logger.info(f"✅ Migration completed - {final_count} chunks now in correct location")
        
        # Offer to clean up old data
        if incorrect_count > 0:
            response = input(f"Migration successful! Do you want to delete the old data from {INCORRECT_NAMESPACE}/{INCORRECT_DATABASE}? (y/N): ")
            if response.lower() == 'y':
                await db.use(INCORRECT_NAMESPACE, INCORRECT_DATABASE)
                await db.query("DELETE document_chunks;")
                logger.info("🗑️  Old data cleaned up")
            else:
                logger.info("ℹ️  Old data preserved - you can manually clean it up later")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise
    finally:
        await db.close()

async def verify_configuration():
    """Verify the current configuration matches .env file."""
    logger.info("🔍 Verifying database configuration...")
    
    db = Surreal()
    try:
        await db.connect(SURREALDB_URL)
        await db.signin({"user": SURREALDB_USERNAME, "pass": SURREALDB_PASSWORD})
        await db.use(CORRECT_NAMESPACE, CORRECT_DATABASE)
        
        # Test query
        result = await db.query("SELECT count() FROM document_chunks GROUP ALL;")
        count = 0
        if result and len(result) > 0 and len(result[0]) > 0:
            count = result[0][0].get('count', 0)
        
        logger.info(f"✅ Configuration verified: {count} chunks in {CORRECT_NAMESPACE}/{CORRECT_DATABASE}")
        
        # Show configuration summary
        logger.info("📋 Current Configuration:")
        logger.info(f"   URL: {SURREALDB_URL}")
        logger.info(f"   Namespace: {CORRECT_NAMESPACE}")
        logger.info(f"   Database: {CORRECT_DATABASE}")
        logger.info(f"   Username: {SURREALDB_USERNAME}")
        
        return count
        
    except Exception as e:
        logger.error(f"❌ Configuration verification failed: {e}")
        return None
    finally:
        await db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate Ptolemies database configuration")
    parser.add_argument("--verify-only", action="store_true", help="Only verify configuration, don't migrate")
    parser.add_argument("--force", action="store_true", help="Force migration without prompts")
    
    args = parser.parse_args()
    
    if args.verify_only:
        asyncio.run(verify_configuration())
    else:
        asyncio.run(migrate_database_config())