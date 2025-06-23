#!/usr/bin/env python3
"""
Neo4j MCP Server Test Script

Test the Neo4j MCP server functionality without MCP client.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from neo4j_mcp_server import Neo4jDatabase


def test_connection():
    """Test Neo4j database connection."""
    print("🔌 Testing Neo4j connection...")
    
    # Get environment variables
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    database = os.getenv("NEO4J_DATABASE", "neo4j")
    
    print(f"   URI: {uri}")
    print(f"   Username: {username}")
    print(f"   Database: {database}")
    
    try:
        db = Neo4jDatabase(uri, username, password, database)
        print("✅ Connection successful!")
        
        # Test basic query
        print("\n🔍 Testing basic query...")
        result = db.execute_query("RETURN 'Hello, Neo4j!' as greeting")
        
        if "error" in result:
            print(f"❌ Query failed: {result['error']}")
        else:
            print(f"✅ Query successful: {result['records']}")
        
        # Test schema retrieval
        print("\n📊 Testing schema retrieval...")
        schema = db.get_schema()
        
        if "error" in schema:
            print(f"❌ Schema retrieval failed: {schema['error']}")
        else:
            print("✅ Schema retrieved successfully:")
            print(f"   Labels: {len(schema.get('labels', []))}")
            print(f"   Relationship types: {len(schema.get('relationship_types', []))}")
            print(f"   Property keys: {len(schema.get('property_keys', []))}")
        
        # Clean up
        db.close()
        print("\n🔒 Connection closed successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


def test_sample_operations():
    """Test sample Neo4j operations."""
    print("\n🧪 Testing sample operations...")
    
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    database = os.getenv("NEO4J_DATABASE", "neo4j")
    
    try:
        db = Neo4jDatabase(uri, username, password, database)
        
        # Create a test node
        print("   Creating test node...")
        create_result = db.execute_query(
            "CREATE (p:TestPerson {name: 'Test User', created_at: datetime()}) RETURN p"
        )
        
        if "error" in create_result:
            print(f"   ❌ Node creation failed: {create_result['error']}")
        else:
            print(f"   ✅ Node created: {create_result['summary']['counters']['nodes_created']} nodes")
        
        # Query the test node
        print("   Querying test node...")
        query_result = db.execute_query(
            "MATCH (p:TestPerson {name: 'Test User'}) RETURN p.name as name, p.created_at as created"
        )
        
        if "error" in query_result:
            print(f"   ❌ Query failed: {query_result['error']}")
        else:
            print(f"   ✅ Query successful: {len(query_result['records'])} records found")
        
        # Clean up test data
        print("   Cleaning up test data...")
        cleanup_result = db.execute_query(
            "MATCH (p:TestPerson {name: 'Test User'}) DELETE p"
        )
        
        if "error" in cleanup_result:
            print(f"   ❌ Cleanup failed: {cleanup_result['error']}")
        else:
            print(f"   ✅ Cleanup successful: {cleanup_result['summary']['counters']['nodes_deleted']} nodes deleted")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Sample operations failed: {e}")
        return False


def main():
    """Main test function."""
    print("🚀 Neo4j MCP Server Test Suite")
    print("=" * 40)
    
    # Check environment variables
    print("🔍 Checking environment variables...")
    required_vars = ["NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD"]
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"   ✅ {var}: {'*' * len(value) if 'PASSWORD' in var else value}")
        else:
            missing_vars.append(var)
            print(f"   ❌ {var}: Not set")
    
    if missing_vars:
        print(f"\n⚠️  Missing environment variables: {', '.join(missing_vars)}")
        print("   Please set these variables and try again.")
        print("\n   Example:")
        print("   export NEO4J_URI='bolt://localhost:7687'")
        print("   export NEO4J_USERNAME='neo4j'")
        print("   export NEO4J_PASSWORD='your_password'")
        return False
    
    print("\n" + "=" * 40)
    
    # Test connection
    if not test_connection():
        print("\n❌ Connection test failed. Please check your Neo4j setup.")
        return False
    
    # Test sample operations
    if not test_sample_operations():
        print("\n❌ Sample operations test failed.")
        return False
    
    print("\n" + "=" * 40)
    print("🎉 All tests passed! Neo4j MCP Server is ready to use.")
    print("\n📖 Next steps:")
    print("   1. Add the server to your Claude Code configuration")
    print("   2. Restart Claude Code")
    print("   3. Start using Neo4j commands in Claude Code!")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)