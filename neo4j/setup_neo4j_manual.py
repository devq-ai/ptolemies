#!/usr/bin/env python3
"""
Manual Neo4j Setup Script
Use this if the automated import fails due to authentication issues
"""

import subprocess
import json

def test_neo4j_connection():
    """Test various Neo4j connection methods."""
    print("🔍 Testing Neo4j Connection Methods...")
    
    # Test different ports and credentials
    configs = [
        ("bolt://localhost:7690", "neo4j", "ptolemies"),
        ("bolt://localhost:7687", "neo4j", "ptolemies"),
        ("bolt://localhost:7690", "neo4j", "password"),
        ("bolt://localhost:7687", "neo4j", "password"),
        ("bolt://localhost:7690", "neo4j", "neo4j"),
        ("bolt://localhost:7687", "neo4j", "neo4j"),
    ]
    
    for uri, user, password in configs:
        print(f"\nTesting: {uri} with {user}:{password}")
        
        cmd = [
            'cypher-shell',
            '-a', uri,
            '-u', user,
            '-p', password
        ]
        
        try:
            result = subprocess.run(
                cmd,
                input="RETURN 'connected' as status;",
                text=True,
                capture_output=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print(f"✅ SUCCESS: Connected with {uri}, {user}:{password}")
                print(f"Response: {result.stdout}")
                return uri, user, password
            else:
                print(f"❌ Failed: {result.stderr.strip()}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n❌ No working connection found")
    return None, None, None

def test_http_connection():
    """Test Neo4j HTTP endpoint."""
    print("\n🌐 Testing HTTP Connection...")
    
    import requests
    
    # Test HTTP endpoint
    try:
        response = requests.get("http://localhost:7475")
        print(f"✅ HTTP Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"❌ HTTP Error: {e}")
    
    # Test with different credentials
    credentials = [
        ("neo4j", "ptolemies"),
        ("neo4j", "password"),
        ("neo4j", "neo4j"),
    ]
    
    for user, password in credentials:
        try:
            response = requests.post(
                "http://localhost:7475/db/neo4j/query/v2",
                auth=(user, password),
                headers={"Content-Type": "application/json"},
                json={"statement": "RETURN 'test' as result"}
            )
            
            if response.status_code == 200:
                print(f"✅ HTTP Auth Success: {user}:{password}")
                print(f"Response: {response.json()}")
                return user, password
            else:
                print(f"❌ HTTP Auth Failed: {user}:{password} - {response.status_code}")
                
        except Exception as e:
            print(f"❌ HTTP Request Error: {e}")
    
    return None, None

def manual_setup_instructions():
    """Provide manual setup instructions."""
    print("""
🔧 MANUAL SETUP INSTRUCTIONS
============================

Since automated connection failed, please follow these steps:

1. Open Neo4j Browser:
   http://localhost:7475

2. If prompted for first-time setup:
   - Username: neo4j
   - Password: (set a new password)
   - Remember the password you set!

3. Once connected, run these setup queries manually:

   -- Create constraints
   CREATE CONSTRAINT source_name_unique IF NOT EXISTS 
   FOR (s:Source) REQUIRE s.name IS UNIQUE;
   
   CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS 
   FOR (c:Chunk) REQUIRE c.id IS UNIQUE;
   
   -- Create sample data
   CREATE (s:Source {name: "FastAPI", chunk_count: 8, priority: "high"});
   CREATE (c:Chunk {id: "test_chunk", title: "Test Chunk", content: "Test content"});
   
   -- Verify setup
   MATCH (n) RETURN labels(n), count(n);

4. Update the password in the import script:
   export NEO4J_PASSWORD='your_actual_password'

5. Re-run the import:
   python3 neo4j_import_from_surrealdb.py

🚨 IMPORTANT: The script fetched 292 chunks from SurrealDB successfully!
The only issue is Neo4j authentication.
""")

def check_surrealdb():
    """Verify SurrealDB is working."""
    print("\n📊 Checking SurrealDB Connection...")
    
    cmd = [
        'surreal', 'sql',
        '--conn', 'ws://localhost:8000/rpc',
        '--user', 'root',
        '--pass', 'root',
        '--ns', 'ptolemies',
        '--db', 'knowledge',
        '--pretty'
    ]
    
    try:
        result = subprocess.run(
            cmd,
            input="SELECT COUNT() FROM document_chunks;",
            text=True,
            capture_output=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("✅ SurrealDB Connected Successfully")
            print(f"Response: {result.stdout}")
        else:
            print(f"❌ SurrealDB Error: {result.stderr}")
            
    except Exception as e:
        print(f"❌ SurrealDB Connection Error: {e}")

def main():
    """Main diagnostic function."""
    print("🚀 Neo4j Setup Diagnostics")
    print("=" * 50)
    
    # Check SurrealDB first
    check_surrealdb()
    
    # Test Neo4j connections
    bolt_uri, user, password = test_neo4j_connection()
    
    if bolt_uri:
        print(f"\n🎉 Found working connection: {bolt_uri}")
        print(f"Credentials: {user}:{password}")
        print("\nYou can now run the import with:")
        print(f"export NEO4J_PASSWORD='{password}'")
        print("python3 neo4j_import_from_surrealdb.py")
    else:
        # Test HTTP
        http_user, http_pass = test_http_connection()
        
        if http_user:
            print(f"\n🎉 Found working HTTP credentials: {http_user}:{http_pass}")
        else:
            manual_setup_instructions()

if __name__ == "__main__":
    main()