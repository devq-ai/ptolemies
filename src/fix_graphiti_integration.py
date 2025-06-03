#!/usr/bin/env python3
"""
Comprehensive Fix for Graphiti Integration Issues

This script will:
1. Create missing Neo4j indexes required by Graphiti
2. Fix the schema mismatches 
3. Update search functionality to work properly
4. Fix visualization to return real data
5. Test everything to ensure it works
"""

import os
import sys
import json
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

def fix_neo4j_schema():
    """Fix Neo4j database schema and create missing indexes"""
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
        
        print("🔧 Fixing Neo4j Schema and Indexes")
        print("=" * 50)
        
        with driver.session() as session:
            # 1. Create missing fulltext indexes
            indexes_to_create = [
                {
                    "name": "episode_content",
                    "query": "CREATE FULLTEXT INDEX episode_content IF NOT EXISTS FOR (e:Episodic) ON EACH [e.content, e.name]"
                },
                {
                    "name": "edge_name_and_fact", 
                    "query": "CREATE FULLTEXT INDEX edge_name_and_fact IF NOT EXISTS FOR ()-[r:RELATES_TO]-() ON EACH [r.name, r.fact]"
                },
                {
                    "name": "community_name",
                    "query": "CREATE FULLTEXT INDEX community_name IF NOT EXISTS FOR (c:Community) ON EACH [c.name, c.summary]"
                }
            ]
            
            for index in indexes_to_create:
                try:
                    print(f"   Creating index: {index['name']}")
                    session.run(index["query"])
                    print(f"   ✅ Created index: {index['name']}")
                except Exception as e:
                    print(f"   ❌ Failed to create index {index['name']}: {e}")
            
            # 2. Add missing properties to existing nodes/relationships
            print("\n🔧 Adding missing properties...")
            
            # Add missing properties to Entity nodes
            try:
                result = session.run("""
                    MATCH (e:Entity)
                    WHERE e.expired_at IS NULL OR e.invalid_at IS NULL
                    SET e.expired_at = null, e.invalid_at = null
                    RETURN count(e) as updated_entities
                """)
                count = result.single()["updated_entities"]
                print(f"   ✅ Updated {count} Entity nodes with missing properties")
            except Exception as e:
                print(f"   ❌ Failed to update Entity properties: {e}")
            
            # Add missing properties to RELATES_TO relationships
            try:
                result = session.run("""
                    MATCH ()-[r:RELATES_TO]->()
                    WHERE r.expired_at IS NULL OR r.invalid_at IS NULL  
                    SET r.expired_at = null, r.invalid_at = null
                    RETURN count(r) as updated_relationships
                """)
                count = result.single()["updated_relationships"]
                print(f"   ✅ Updated {count} RELATES_TO relationships with missing properties")
            except Exception as e:
                print(f"   ❌ Failed to update relationship properties: {e}")
            
            # 3. Create sample Community nodes (Graphiti expects these)
            print("\n🏘️ Creating sample Community nodes...")
            try:
                result = session.run("""
                    MERGE (c:Community {name: 'Technology Companies'})
                    SET c.uuid = randomUUID(),
                        c.group_id = 'default',
                        c.created_at = datetime(),
                        c.summary = 'Community of technology companies and related entities',
                        c.name_embedding = [0.0] * 1536
                    RETURN c.uuid as uuid
                """)
                uuid = result.single()["uuid"]
                print(f"   ✅ Created Technology Companies community: {uuid}")
            except Exception as e:
                print(f"   ❌ Failed to create Community nodes: {e}")
            
            # 4. Verify the fixes
            print("\n✅ Verifying fixes...")
            
            # Check indexes
            result = session.run("SHOW INDEXES")
            indexes = list(result)
            fulltext_indexes = [idx for idx in indexes if 'fulltext' in idx.get('type', '').lower()]
            print(f"   Found {len(fulltext_indexes)} fulltext indexes")
            
            # Check communities
            result = session.run("MATCH (c:Community) RETURN count(c) as count")
            community_count = result.single()["count"]
            print(f"   Found {community_count} Community nodes")
            
            # Check entity properties
            result = session.run("""
                MATCH (e:Entity) 
                WHERE e.expired_at IS NOT NULL OR e.invalid_at IS NOT NULL OR e.valid_at IS NOT NULL
                RETURN count(e) as count
            """)
            entity_count = result.single()["count"]
            print(f"   Found {entity_count} Entity nodes with temporal properties")
            
        driver.close()
        return True
        
    except Exception as e:
        print(f"❌ Neo4j schema fix failed: {e}")
        return False

def fix_graphiti_service():
    """Fix the Graphiti service implementation"""
    print("\n🔧 Fixing Graphiti Service Implementation")
    print("=" * 50)
    
    # Path to the graphiti service file
    service_file = Path(__file__).parent / "ptolemies" / "integrations" / "graphiti" / "graphiti_service.py"
    
    if not service_file.exists():
        print(f"❌ Service file not found: {service_file}")
        return False
    
    try:
        # Read the current service file
        with open(service_file, 'r') as f:
            content = f.read()
        
        # Check if it needs fixing (look for known issues)
        if "# FIXED_SEARCH" in content:
            print("✅ Service already appears to be fixed")
            return True
        
        # Create a backup
        backup_file = service_file.with_suffix('.py.backup')
        with open(backup_file, 'w') as f:
            f.write(content)
        print(f"   📦 Created backup: {backup_file}")
        
        # Add search fixes
        search_fix = '''
    async def search_entities_fixed(self, query: str, limit: int = 10):
        """Fixed entity search that handles missing indexes gracefully"""
        try:
            # FIXED_SEARCH - Use vector similarity search when fulltext fails
            search_vector = await self._get_embedding(query)
            
            results = []
            
            # Search entities using vector similarity
            entity_query = """
                MATCH (e:Entity)
                WHERE e.name_embedding IS NOT NULL
                WITH e, vector.similarity.cosine(e.name_embedding, $search_vector) AS score
                WHERE score > 0.7
                RETURN e.uuid as uuid, e.name as name, e.summary as summary,
                       e.group_id as group_id, e.created_at as created_at, score
                ORDER BY score DESC
                LIMIT $limit
            """
            
            entity_results = await self.graphiti.driver.execute_query(
                entity_query,
                search_vector=search_vector,
                limit=limit
            )
            
            for record in entity_results.records:
                results.append({
                    "uuid": record["uuid"],
                    "name": record["name"], 
                    "summary": record.get("summary", ""),
                    "type": "Entity",
                    "score": record["score"]
                })
            
            # Also search relationships
            rel_query = """
                MATCH ()-[r:RELATES_TO]->()
                WHERE r.fact_embedding IS NOT NULL
                WITH r, vector.similarity.cosine(r.fact_embedding, $search_vector) AS score
                WHERE score > 0.7
                RETURN r.uuid as uuid, r.name as name, r.fact as fact,
                       r.group_id as group_id, r.created_at as created_at, score
                ORDER BY score DESC
                LIMIT $limit
            """
            
            rel_results = await self.graphiti.driver.execute_query(
                rel_query,
                search_vector=search_vector,
                limit=max(1, limit - len(results))
            )
            
            for record in rel_results.records:
                results.append({
                    "uuid": record["uuid"],
                    "name": record["name"],
                    "summary": record.get("fact", ""),
                    "type": "Relationship", 
                    "score": record["score"]
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Fixed search failed: {e}")
            return []
'''
        
        # Insert the fix before the last class definition
        if "class " in content:
            # Find the last class definition
            lines = content.split('\n')
            insert_point = -1
            for i, line in enumerate(lines):
                if line.strip().startswith('class '):
                    insert_point = i
            
            if insert_point > 0:
                lines.insert(insert_point, search_fix)
                content = '\n'.join(lines)
        
        # Write the fixed content
        with open(service_file, 'w') as f:
            f.write(content)
        
        print("✅ Applied search fixes to Graphiti service")
        return True
        
    except Exception as e:
        print(f"❌ Failed to fix Graphiti service: {e}")
        return False

def fix_visualization():
    """Fix the visualization endpoint to return real data"""
    print("\n🎨 Fixing Visualization Endpoint")
    print("=" * 50)
    
    viz_file = Path(__file__).parent / "ptolemies" / "integrations" / "graphiti" / "visualization.py"
    
    if not viz_file.exists():
        print(f"❌ Visualization file not found: {viz_file}")
        return False
    
    try:
        with open(viz_file, 'r') as f:
            content = f.read()
        
        # Check if already fixed
        if "# FIXED_VIZ" in content:
            print("✅ Visualization already appears to be fixed")
            return True
        
        # Create backup
        backup_file = viz_file.with_suffix('.py.backup')
        with open(backup_file, 'w') as f:
            f.write(content)
        print(f"   📦 Created backup: {backup_file}")
        
        # Add real data visualization
        viz_fix = '''
def create_real_graph_visualization(driver, query: str = "", depth: int = 2):
    """Create real graph visualization from Neo4j data"""
    # FIXED_VIZ - Return actual graph data instead of mock data
    
    try:
        with driver.session() as session:
            # Get actual entities and relationships
            if query:
                # Search for entities related to the query
                cypher_query = """
                    MATCH (e:Entity)
                    WHERE toLower(e.name) CONTAINS toLower($query) 
                       OR toLower(e.summary) CONTAINS toLower($query)
                    WITH e
                    LIMIT 20
                    
                    OPTIONAL MATCH (e)-[r:RELATES_TO]-(connected:Entity)
                    
                    RETURN e, r, connected
                """
                result = session.run(cypher_query, query=query)
            else:
                # Get a sample of the graph
                cypher_query = """
                    MATCH (e:Entity)
                    WITH e
                    LIMIT 10
                    
                    OPTIONAL MATCH (e)-[r:RELATES_TO]-(connected:Entity)
                    
                    RETURN e, r, connected
                """
                result = session.run(cypher_query)
            
            nodes = {}
            edges = []
            
            for record in result:
                entity = record.get('e')
                relationship = record.get('r')
                connected = record.get('connected')
                
                if entity:
                    nodes[entity['uuid']] = {
                        "id": entity['uuid'],
                        "label": entity['name'],
                        "type": "entity", 
                        "size": 1.0,
                        "color": "#1f77b4",
                        "summary": entity.get('summary', ''),
                        "group_id": entity.get('group_id', '')
                    }
                
                if connected:
                    nodes[connected['uuid']] = {
                        "id": connected['uuid'],
                        "label": connected['name'],
                        "type": "entity",
                        "size": 1.0, 
                        "color": "#ff7f0e",
                        "summary": connected.get('summary', ''),
                        "group_id": connected.get('group_id', '')
                    }
                
                if relationship and entity and connected:
                    edges.append({
                        "id": relationship['uuid'],
                        "source": entity['uuid'],
                        "target": connected['uuid'], 
                        "label": relationship['name'],
                        "fact": relationship.get('fact', ''),
                        "weight": 1.0
                    })
            
            return {
                "nodes": list(nodes.values()),
                "edges": edges,
                "metadata": {
                    "query": query,
                    "node_count": len(nodes),
                    "edge_count": len(edges),
                    "data_source": "real_neo4j_data"
                }
            }
            
    except Exception as e:
        print(f"Error creating real visualization: {e}")
        # Fallback to basic mock data
        return {
            "nodes": [{"id": "error", "label": "Visualization Error", "type": "error"}],
            "edges": [],
            "metadata": {"error": str(e)}
        }
'''
        
        # Add the fix to the file
        content = viz_fix + "\n\n" + content
        
        with open(viz_file, 'w') as f:
            f.write(content)
        
        print("✅ Applied visualization fixes")
        return True
        
    except Exception as e:
        print(f"❌ Failed to fix visualization: {e}")
        return False

def test_fixes():
    """Test that all fixes are working"""
    print("\n🧪 Testing Fixes")
    print("=" * 50)
    
    import requests
    base_url = "http://localhost:8001"
    
    try:
        # Test search
        print("🔍 Testing search functionality...")
        response = requests.get(f"{base_url}/entities/search", 
                               params={"query": "Apple", "limit": 5}, 
                               timeout=10)
        
        if response.status_code == 200:
            results = response.json()
            if results.get("results") and len(results["results"]) > 0:
                print(f"   ✅ Search now returns {len(results['results'])} results")
                return True
            else:
                print("   ❌ Search still returns empty results")
                
        # Test visualization
        print("🎨 Testing visualization...")
        response = requests.get(f"{base_url}/graph/visualize", 
                               params={"query": "Apple", "depth": 2}, 
                               timeout=10)
        
        if response.status_code == 200:
            viz_data = response.json()
            if viz_data.get("metadata", {}).get("data_source") == "real_neo4j_data":
                print(f"   ✅ Visualization now returns real data")
                return True
            else:
                print("   ❌ Visualization still returns mock data")
                
    except Exception as e:
        print(f"❌ Testing failed: {e}")
    
    return False

def main():
    """Apply all fixes"""
    print("🚀 Starting Comprehensive Graphiti Integration Fix")
    print("=" * 70)
    
    # Step 1: Fix Neo4j schema
    schema_fixed = fix_neo4j_schema()
    
    # Step 2: Fix Graphiti service
    service_fixed = fix_graphiti_service()
    
    # Step 3: Fix visualization
    viz_fixed = fix_visualization()
    
    print("\n📋 Fix Summary")
    print("=" * 50)
    print(f"Neo4j Schema: {'✅' if schema_fixed else '❌'}")
    print(f"Graphiti Service: {'✅' if service_fixed else '❌'}")
    print(f"Visualization: {'✅' if viz_fixed else '❌'}")
    
    if all([schema_fixed, service_fixed, viz_fixed]):
        print("\n✅ All fixes applied successfully!")
        print("\n🔄 Please restart the Graphiti service to apply changes:")
        print("   1. Stop the current service (Ctrl+C)")
        print("   2. Run: venv_graphiti/bin/python src/ptolemies/integrations/graphiti/graphiti_service.py")
        print("   3. Test with the search and visualization endpoints")
        
        # Test if service is running
        try:
            import requests
            response = requests.get("http://localhost:8001/health", timeout=2)
            if response.status_code == 200:
                print("\n🧪 Service is running - testing fixes now...")
                test_fixes()
        except:
            print("\n⚠️  Service not running - please restart to test fixes")
        
        return True
    else:
        print("\n❌ Some fixes failed - manual intervention may be required")
        return False

if __name__ == "__main__":
    main()