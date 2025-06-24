#!/usr/bin/env python3
"""
Simple data check using direct SurrealDB connection
Verify data accessibility with corrected configuration
"""

import asyncio
import os
import sys

def load_env_file(filepath=".env"):
    """Load environment variables from .env file."""
    env_vars = {}
    if not os.path.exists(filepath):
        return env_vars
    
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key] = value
    
    return env_vars

async def test_surrealdb_connection():
    """Test SurrealDB connection and basic queries."""
    print("🔍 Testing SurrealDB Connection and Data")
    print("=" * 50)
    
    # Load configuration
    env_vars = load_env_file()
    
    url = env_vars.get('SURREALDB_URL', 'ws://localhost:8000/rpc')
    username = env_vars.get('SURREALDB_USERNAME', 'root')
    password = env_vars.get('SURREALDB_PASSWORD', 'root')
    namespace = env_vars.get('SURREALDB_NAMESPACE', 'ptolemies')
    database = env_vars.get('SURREALDB_DATABASE', 'knowledge')
    
    print(f"📋 Configuration:")
    print(f"   URL: {url}")
    print(f"   Namespace: {namespace}")
    print(f"   Database: {database}")
    print(f"   Username: {username}")
    
    try:
        # Try to import surrealdb
        try:
            from surrealdb import Surreal
            print("   ✅ SurrealDB module available")
        except ImportError:
            print("   ❌ SurrealDB module not installed")
            print("   💡 Run: pip3 install surrealdb --break-system-packages")
            return False
        
        # Connect to database
        print("\n🔌 Connecting to SurrealDB...")
        db = Surreal()
        await db.connect(url)
        await db.signin({"user": username, "pass": password})
        await db.use(namespace, database)
        print("   ✅ Connected successfully")
        
        # Test basic queries
        print("\n📊 Running data verification queries...")
        
        # Query 1: Document count
        print("1. Checking document chunks count...")
        try:
            result = await db.query("SELECT count() FROM document_chunks GROUP ALL;")
            if result and len(result) > 0 and len(result[0]) > 0:
                count = result[0][0].get('count', 0)
                print(f"   📄 Found {count} document chunks")
                
                if count == 0:
                    print("   ⚠️  Database appears to be empty")
                    print("   💡 You may need to run data ingestion/migration")
                    
                    # Check if data exists in the old configuration
                    print("\n2. Checking old configuration (knowledge/ptolemies)...")
                    try:
                        await db.use("knowledge", "ptolemies")
                        old_result = await db.query("SELECT count() FROM document_chunks GROUP ALL;")
                        if old_result and len(old_result) > 0 and len(old_result[0]) > 0:
                            old_count = old_result[0][0].get('count', 0)
                            print(f"   📄 Found {old_count} chunks in old configuration")
                            
                            if old_count > 0:
                                print("   🔄 Data migration needed!")
                                print("   💡 Run: python3 migrate_database_config.py")
                        else:
                            print("   📄 No data in old configuration either")
                            
                        # Switch back to correct configuration
                        await db.use(namespace, database)
                        
                    except Exception as e:
                        print(f"   ❌ Could not check old configuration: {e}")
                        
                else:
                    print("   ✅ Data found in correct configuration")
                    
                    # Get sample data
                    print("\n2. Retrieving sample documents...")
                    sample_result = await db.query("""
                        SELECT id, title, source_name, quality_score
                        FROM document_chunks
                        LIMIT 3;
                    """)
                    
                    if sample_result and len(sample_result) > 0:
                        documents = sample_result[0]
                        for i, doc in enumerate(documents, 1):
                            title = doc.get('title', 'No title')
                            source = doc.get('source_name', 'Unknown')
                            quality = doc.get('quality_score', 0)
                            print(f"   {i}. {title[:40]}...")
                            print(f"      Source: {source}, Quality: {quality:.2f}")
                            
                    # Get source statistics
                    print("\n3. Source distribution...")
                    sources_result = await db.query("""
                        SELECT source_name, count() AS doc_count
                        FROM document_chunks
                        GROUP BY source_name
                        ORDER BY doc_count DESC
                        LIMIT 5;
                    """)
                    
                    if sources_result and len(sources_result) > 0:
                        sources = sources_result[0]
                        for source in sources:
                            name = source.get('source_name', 'Unknown')
                            count = source.get('doc_count', 0)
                            print(f"   • {name}: {count} documents")
                            
            else:
                print("   ❌ Could not retrieve document count")
                
        except Exception as e:
            print(f"   ❌ Query error: {e}")
            
        # Close connection
        await db.close()
        return True
        
    except Exception as e:
        print(f"❌ Connection error: {e}")
        
        if "Connection refused" in str(e) or "connect" in str(e).lower():
            print("\n💡 Troubleshooting:")
            print("   1. Ensure SurrealDB is running: surreal start --bind 0.0.0.0:8000")
            print("   2. Check if the server is accessible on localhost:8000")
            print("   3. Verify firewall settings")
            
        return False

def print_next_steps(data_found: bool, old_config_has_data: bool = False):
    """Print recommended next steps."""
    print("\n" + "=" * 50)
    print("📋 NEXT STEPS:")
    
    if data_found:
        print("✅ SUCCESS: Data is accessible with corrected configuration")
        print("   • Your 784-page knowledge base is ready to use")
        print("   • All queries should work as expected")
        print("   • You can run your applications normally")
        
    elif old_config_has_data:
        print("🔄 MIGRATION NEEDED: Data found in old configuration")
        print("   • Run: python3 migrate_database_config.py")
        print("   • This will move data to the correct namespace/database")
        print("   • After migration, re-run this test to verify")
        
    else:
        print("📥 DATA INGESTION NEEDED: No data found in either configuration")
        print("   • The database schema exists but is empty")
        print("   • You need to run data ingestion scripts")
        print("   • Check for crawling/indexing scripts in the project")
        
    print("\n🔧 For detailed verification:")
    print("   • Run: python3 verify_db_config.py")
    print("   • Check: COMPLETE_QUERY_RESULTS.md for query examples")

async def main():
    """Main execution."""
    try:
        data_accessible = await test_surrealdb_connection()
        print_next_steps(data_accessible)
        return 0 if data_accessible else 1
        
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())