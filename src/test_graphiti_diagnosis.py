#!/usr/bin/env python3
"""
Comprehensive Graphiti Integration Diagnosis
This script will test all aspects of the Graphiti integration to identify issues.
"""

import os
import sys
import json
import requests
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

def test_graphiti_service():
    """Test the Graphiti service endpoints"""
    base_url = "http://localhost:8001"
    
    print("🔍 Testing Graphiti Service Endpoints")
    print("=" * 50)
    
    # Test health check
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        print(f"✅ Health check: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False
    
    # Test entity search with Apple
    try:
        response = requests.get(f"{base_url}/entities/search", 
                               params={"query": "Apple", "limit": 5}, 
                               timeout=10)
        print(f"🔍 Entity search for 'Apple': {response.status_code}")
        search_result = response.json()
        print(f"   Search results: {json.dumps(search_result, indent=2)}")
        
        if not search_result or len(search_result) == 0:
            print("❌ No search results returned for 'Apple'")
        else:
            print(f"✅ Found {len(search_result)} results")
            
    except Exception as e:
        print(f"❌ Entity search failed: {e}")
    
    # Test visualization endpoint
    try:
        response = requests.get(f"{base_url}/graph/visualize", 
                               params={"query": "companies", "depth": 2}, 
                               timeout=10)
        print(f"🎨 Visualization endpoint: {response.status_code}")
        viz_result = response.json()
        
        # Check if it's real data or mock data
        if "nodes" in viz_result and "edges" in viz_result:
            print(f"   Nodes: {len(viz_result['nodes'])}, Edges: {len(viz_result['edges'])}")
            if viz_result['nodes']:
                first_node = viz_result['nodes'][0]
                if 'id' in first_node and 'sample' in str(first_node.get('id', '')).lower():
                    print("❌ Visualization is returning mock/sample data")
                else:
                    print("✅ Visualization appears to be returning real data")
                    print(f"   Sample node: {json.dumps(first_node, indent=2)}")
        else:
            print("❌ Visualization returned unexpected format")
            
    except Exception as e:
        print(f"❌ Visualization failed: {e}")
    
    return True

def test_neo4j_schema():
    """Test Neo4j database schema and indexes"""
    try:
        from neo4j import GraphDatabase
        from dotenv import load_dotenv
        
        load_dotenv()
        
        NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "Ptolemis")
        NEO4J_USER = "neo4j"
        
        if NEO4J_URI.startswith("http://"):
            NEO4J_URI = NEO4J_URI.replace("http://", "bolt://").replace(":7474", ":7687")
        
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        
        print("\n🔍 Testing Neo4j Schema")
        print("=" * 50)
        
        with driver.session() as session:
            # Check indexes
            print("📊 Checking indexes...")
            result = session.run("SHOW INDEXES")
            indexes = list(result)
            print(f"   Found {len(indexes)} indexes:")
            for idx in indexes:
                print(f"   - {idx['name']}: {idx['type']} on {idx.get('labelsOrTypes', [])} ({idx.get('properties', [])})")
            
            # Check constraints
            print("\n🔒 Checking constraints...")
            result = session.run("SHOW CONSTRAINTS")
            constraints = list(result)
            print(f"   Found {len(constraints)} constraints:")
            for constraint in constraints:
                print(f"   - {constraint['name']}: {constraint['type']}")
            
            # Check if fulltext index exists
            fulltext_exists = any('fulltext' in idx.get('type', '').lower() for idx in indexes)
            if not fulltext_exists:
                print("❌ No fulltext indexes found - this explains search failures")
            
            # Test specific queries that are failing
            print("\n🔍 Testing specific failing queries...")
            
            # Test Community nodes
            try:
                result = session.run("MATCH (c:Community) RETURN count(c) as count")
                count = result.single()["count"]
                print(f"   Community nodes: {count}")
                if count == 0:
                    print("❌ No Community nodes found - Graphiti expects these")
            except Exception as e:
                print(f"❌ Community query failed: {e}")
            
            # Test Entity properties
            try:
                result = session.run("""
                    MATCH (e:Entity) 
                    RETURN keys(e) as properties 
                    LIMIT 1
                """)
                if result.peek():
                    properties = result.single()["properties"]
                    print(f"   Entity properties: {properties}")
                    
                    expected_props = ['expired_at', 'invalid_at', 'valid_at']
                    missing_props = [prop for prop in expected_props if prop not in properties]
                    if missing_props:
                        print(f"❌ Missing expected properties: {missing_props}")
                    else:
                        print("✅ All expected properties present")
                else:
                    print("❌ No Entity nodes found")
                    
            except Exception as e:
                print(f"❌ Entity properties query failed: {e}")
            
            # Test relationship properties
            try:
                result = session.run("""
                    MATCH ()-[r:RELATES_TO]->() 
                    RETURN keys(r) as properties 
                    LIMIT 1
                """)
                if result.peek():
                    properties = result.single()["properties"]
                    print(f"   RELATES_TO properties: {properties}")
                    
                    expected_props = ['expired_at', 'invalid_at', 'valid_at']
                    missing_props = [prop for prop in expected_props if prop not in properties]
                    if missing_props:
                        print(f"❌ Missing expected relationship properties: {missing_props}")
                    else:
                        print("✅ All expected relationship properties present")
                else:
                    print("❌ No RELATES_TO relationships found")
                    
            except Exception as e:
                print(f"❌ Relationship properties query failed: {e}")
                
        driver.close()
        return True
        
    except Exception as e:
        print(f"❌ Neo4j schema test failed: {e}")
        return False

def test_graphiti_client():
    """Test the actual Graphiti client functionality"""
    print("\n🔍 Testing Graphiti Client")
    print("=" * 50)
    
    try:
        # Import the Graphiti service components
        sys.path.insert(0, str(Path(__file__).parent / "ptolemies" / "integrations" / "graphiti"))
        from graphiti_service import GraphitiService
        
        # Initialize the service
        service = GraphitiService()
        
        # Test search functionality
        print("🔍 Testing Graphiti search...")
        try:
            # This should use the actual Graphiti search methods
            search_results = service.search_entities("Apple", limit=5)
            print(f"   Search results: {search_results}")
            
            if not search_results:
                print("❌ Graphiti search returned empty results")
            else:
                print(f"✅ Graphiti search returned {len(search_results)} results")
                
        except Exception as e:
            print(f"❌ Graphiti search failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Graphiti client test failed: {e}")
        return False

def test_episode_creation():
    """Test creating a new episode and see if it works properly"""
    print("\n🔍 Testing Episode Creation")
    print("=" * 50)
    
    base_url = "http://localhost:8001"
    
    test_episode = {
        "name": "diagnostic_test_episode",
        "content": "This is a diagnostic test episode. Apple produces innovative technology products like the iPhone and iPad. Microsoft develops software solutions.",
        "source": "diagnostic_test",
        "source_description": "Episode created for diagnostic testing",
        "group_id": "diagnostic_test_group"
    }
    
    try:
        response = requests.post(f"{base_url}/episodes", 
                               json=test_episode, 
                               timeout=30)
        print(f"📝 Episode creation: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   Episode result: {json.dumps(result, indent=2)}")
            
            # Now try to search for entities from this episode
            print("\n🔍 Testing search after episode creation...")
            search_response = requests.get(f"{base_url}/entities/search", 
                                         params={"query": "Apple", "limit": 5}, 
                                         timeout=10)
            search_result = search_response.json()
            print(f"   Post-creation search results: {json.dumps(search_result, indent=2)}")
            
            return True
        else:
            print(f"❌ Episode creation failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Episode creation test failed: {e}")
        return False

def main():
    """Run all diagnostic tests"""
    print("🚀 Starting Graphiti Integration Diagnosis")
    print("=" * 70)
    
    # Test service endpoints
    service_ok = test_graphiti_service()
    
    # Test Neo4j schema
    schema_ok = test_neo4j_schema()
    
    # Test Graphiti client
    client_ok = test_graphiti_client()
    
    # Test episode creation
    episode_ok = test_episode_creation()
    
    print("\n📋 Diagnosis Summary")
    print("=" * 50)
    print(f"Service Endpoints: {'✅' if service_ok else '❌'}")
    print(f"Neo4j Schema: {'✅' if schema_ok else '❌'}")
    print(f"Graphiti Client: {'✅' if client_ok else '❌'}")
    print(f"Episode Creation: {'✅' if episode_ok else '❌'}")
    
    if not all([service_ok, schema_ok, client_ok, episode_ok]):
        print("\n🔧 Issues Found - Graphiti integration needs fixes")
        return False
    else:
        print("\n✅ All tests passed - Graphiti integration is working properly")
        return True

if __name__ == "__main__":
    main()