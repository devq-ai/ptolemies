#!/usr/bin/env python3
"""
Set up the SurrealDB schema for Ptolemies Knowledge Base
"""

import asyncio
from surrealdb import Surreal

async def main():
    """Set up the SurrealDB schema."""
    print("Setting up SurrealDB schema...")
    
    # Connect to SurrealDB
    db = Surreal("http://localhost:8000")
    await db.connect()
    
    # Sign in
    await db.signin({"user": "root", "pass": "root"})
    
    # Create namespace and database
    print("Creating namespace and database...")
    await db.query("DEFINE NAMESPACE IF NOT EXISTS ptolemies;")
    await db.query("USE NS ptolemies;")
    await db.query("DEFINE DATABASE IF NOT EXISTS knowledge;")
    await db.query("USE DB knowledge;")
    
    # Use the namespace and database
    await db.use("ptolemies", "knowledge")
    
    # Define schema - Make it schemaless to avoid datetime issues
    print("Defining tables...")
    await db.query("""
        DEFINE TABLE knowledge_item SCHEMALESS;
    """)
    
    # Create a simple index for searching
    print("Creating indexes...")
    await db.query("""
        DEFINE INDEX knowledge_item_title ON TABLE knowledge_item COLUMNS title;
        DEFINE INDEX knowledge_item_source ON TABLE knowledge_item COLUMNS source;
        DEFINE INDEX knowledge_item_category ON TABLE knowledge_item COLUMNS category;
    """)
    
    print("Schema setup complete!")

if __name__ == "__main__":
    asyncio.run(main())