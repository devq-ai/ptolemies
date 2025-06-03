#!/usr/bin/env python3
"""
Test script to verify visualization fix works
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

def test_visualization_function():
    """Test the visualization function directly"""
    try:
        from neo4j import GraphDatabase
        from dotenv import load_dotenv
        import os
        
        load_dotenv()
        
        NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "Ptolemis")
        NEO4J_USER = "neo4j"
        
        if NEO4J_URI.startswith("http://"):
            NEO4J_URI = NEO4J_URI.replace("http://", "bolt://").replace(":7474", ":7687")
        
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        
        # Import the fixed visualization function
        from ptolemies.integrations.graphiti.visualization import create_real_graph_visualization
        
        print("🧪 Testing visualization function directly...")
        
        # Test with Apple query
        result = create_real_graph_visualization(driver, "Apple", 2)
        
        print(f"Result type: {type(result)}")
        print(f"Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        
        if isinstance(result, dict):
            nodes = result.get("nodes", [])
            edges = result.get("edges", [])
            metadata = result.get("metadata", {})
            
            print(f"Nodes: {len(nodes)}")
            print(f"Edges: {len(edges)}")
            print(f"Data source: {metadata.get('data_source', 'unknown')}")
            
            if nodes:
                print(f"Sample node: {nodes[0]}")
                
            if nodes and nodes[0].get("label") != "Node 0":
                print("✅ Visualization function returns real data!")
                return True
            else:
                print("❌ Visualization function still returns mock data")
                return False
        else:
            print("❌ Visualization function returned unexpected format")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    print("🔍 Testing Visualization Fix")
    print("=" * 40)
    
    success = test_visualization_function()
    
    print("\n📋 Test Summary")
    print("=" * 40)
    if success:
        print("✅ Visualization fix is working properly")
        print("\n🔄 Restart the Graphiti service to apply changes:")
        print("   1. Stop the current service (Ctrl+C)")
        print("   2. Run: venv_graphiti/bin/python src/ptolemies/integrations/graphiti/graphiti_service.py")
        print("   3. Test the visualization endpoint again")
    else:
        print("❌ Visualization fix needs more work")
    
    return success

if __name__ == "__main__":
    main()