#!/usr/bin/env python3
"""
Neo4j Data Verification via Graphiti Service
This script checks what data exists in Neo4j through the Graphiti service API
"""
import requests
import json
from datetime import datetime

def check_graphiti_service():
    """Check if Graphiti service is running and connected to Neo4j"""
    try:
        response = requests.get("http://localhost:8001/health", timeout=5)
        if response.status_code == 200:
            health = response.json()
            print("✅ Graphiti Service Status:")
            print(f"   - Status: {health.get('status', 'unknown')}")
            print(f"   - Graphiti Ready: {health.get('graphiti_ready', False)}")
            print(f"   - Neo4j Connected: {health.get('neo4j_connected', False)}")
            print(f"   - Timestamp: {health.get('timestamp', 'unknown')}")
            return health.get('neo4j_connected', False)
        else:
            print(f"❌ Graphiti service returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to Graphiti service: {e}")
        return False

def get_entity_stats():
    """Get statistics about entities in Neo4j"""
    try:
        # Get total entity count with a broad search
        response = requests.get("http://localhost:8001/entities/search?query=all&limit=100", timeout=10)
        if response.status_code == 200:
            data = response.json()
            total_entities = data.get('total_count', 0)
            entities = data.get('results', [])
            
            print(f"\n📊 Entity Statistics:")
            print(f"   - Total Entities: {total_entities}")
            
            if entities:
                # Analyze entity types
                entity_types = {}
                for entity in entities:
                    entity_type = entity.get('type', 'unknown')
                    entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
                
                print(f"   - Entity Types: {dict(entity_types)}")
                
                # Show sample entities
                print(f"   - Sample Entities (first 5):")
                for i, entity in enumerate(entities[:5], 1):
                    print(f"     {i}. ID: {entity.get('id')}, Name: {entity.get('name')}, Type: {entity.get('type')}")
            
            return total_entities
        else:
            print(f"❌ Failed to get entity stats: {response.status_code}")
            return 0
    except requests.exceptions.RequestException as e:
        print(f"❌ Error getting entity stats: {e}")
        return 0

def get_relationship_stats():
    """Get statistics about relationships in Neo4j"""
    try:
        response = requests.get("http://localhost:8001/relationships/search?query=all&limit=100", timeout=10)
        if response.status_code == 200:
            data = response.json()
            total_relationships = data.get('total_count', 0)
            relationships = data.get('results', [])
            
            print(f"\n🔗 Relationship Statistics:")
            print(f"   - Total Relationships: {total_relationships}")
            
            if relationships:
                # Analyze relationship types
                rel_types = {}
                for rel in relationships:
                    rel_type = rel.get('type', 'unknown')
                    rel_types[rel_type] = rel_types.get(rel_type, 0) + 1
                
                print(f"   - Relationship Types: {dict(rel_types)}")
                
                # Show sample relationships
                print(f"   - Sample Relationships (first 5):")
                for i, rel in enumerate(relationships[:5], 1):
                    print(f"     {i}. {rel.get('source')} --[{rel.get('type')}]-> {rel.get('target')} (weight: {rel.get('weight', 'N/A')})")
            
            return total_relationships
        else:
            print(f"❌ Failed to get relationship stats: {response.status_code}")
            return 0
    except requests.exceptions.RequestException as e:
        print(f"❌ Error getting relationship stats: {e}")
        return 0

def get_graph_visualization():
    """Get graph visualization data"""
    try:
        response = requests.get("http://localhost:8001/graph/visualize?query=all&depth=3", timeout=10)
        if response.status_code == 200:
            data = response.json()
            nodes = data.get('nodes', [])
            edges = data.get('edges', [])
            metadata = data.get('metadata', {})
            
            print(f"\n🌐 Graph Visualization Data:")
            print(f"   - Nodes in visualization: {len(nodes)}")
            print(f"   - Edges in visualization: {len(edges)}")
            print(f"   - Query: {metadata.get('query', 'unknown')}")
            print(f"   - Depth: {metadata.get('depth', 'unknown')}")
            print(f"   - Generated at: {metadata.get('generated_at', 'unknown')}")
            
            return len(nodes), len(edges)
        else:
            print(f"❌ Failed to get graph visualization: {response.status_code}")
            return 0, 0
    except requests.exceptions.RequestException as e:
        print(f"❌ Error getting graph visualization: {e}")
        return 0, 0

def search_specific_terms():
    """Search for specific knowledge base terms"""
    search_terms = ['knowledge', 'ptolemies', 'AI', 'machine learning', 'data', 'document']
    
    print(f"\n🔍 Searching for specific terms:")
    for term in search_terms:
        try:
            response = requests.get(f"http://localhost:8001/entities/search?query={term}&limit=10", timeout=5)
            if response.status_code == 200:
                data = response.json()
                count = data.get('total_count', 0)
                print(f"   - '{term}': {count} entities")
            else:
                print(f"   - '{term}': search failed")
        except:
            print(f"   - '{term}': search error")

def main():
    print("🔍 Neo4j Data Verification via Graphiti Service")
    print("=" * 50)
    
    # Check service connectivity
    if not check_graphiti_service():
        print("\n❌ Cannot proceed - Graphiti service is not available or not connected to Neo4j")
        return
    
    # Get data statistics
    entity_count = get_entity_stats()
    relationship_count = get_relationship_stats()
    
    # Get visualization data
    viz_nodes, viz_edges = get_graph_visualization()
    
    # Search for specific terms
    search_specific_terms()
    
    # Summary
    print(f"\n📋 Summary:")
    print(f"   - Neo4j is accessible via Graphiti service: ✅")
    print(f"   - Total entities: {entity_count}")
    print(f"   - Total relationships: {relationship_count}")
    print(f"   - Visualization nodes: {viz_nodes}")
    print(f"   - Visualization edges: {viz_edges}")
    
    if entity_count > 0 or relationship_count > 0:
        print(f"   - Status: ✅ Neo4j contains data")
        print(f"   - Note: Data appears to be test/sample data from Graphiti service")
    else:
        print(f"   - Status: ⚠️  Neo4j appears to be empty or not yet populated with real data")
    
    print(f"\n💡 Next steps:")
    if entity_count == 5 and relationship_count == 3:  # Likely test data
        print(f"   - The data appears to be sample/test data from the Graphiti service")
        print(f"   - Run migration script to populate with real Ptolemies knowledge base data:")
        print(f"     python migrate_to_graphiti.py")
    else:
        print(f"   - Data is present - you can explore it via the web interface at http://localhost:8080")
    
    print(f"   - Access Neo4j browser at http://localhost:7474 (if credentials are configured)")
    print(f"   - Use Graphiti service API at http://localhost:8001 for programmatic access")

if __name__ == "__main__":
    main()