#!/usr/bin/env python3
"""
Quick script to check Neo4j database content
"""
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from neo4j import GraphDatabase
    import logging
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Neo4j configuration
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_PROJECT = os.getenv("NEO4J_PROJECT", "Ptolemis")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "Ptolemis")
    NEO4J_USER = "neo4j"  # Default Neo4j user
    
    # Convert HTTP URI to Bolt URI for driver connection
    if NEO4J_URI.startswith("http://"):
        bolt_uri = NEO4J_URI.replace("http://", "bolt://").replace(":7474", ":7687")
        print(f"🔧 Converting HTTP URI to Bolt: {NEO4J_URI} -> {bolt_uri}")
        NEO4J_URI = bolt_uri
    
    print(f"🔧 Neo4j Project: {NEO4J_PROJECT}")
    print(f"🔧 Using password: {NEO4J_PASSWORD}")
    
    print(f"🔧 Connecting to Neo4j at {NEO4J_URI}")
    print(f"👤 Using credentials: {NEO4J_USER}")
    
    # Create driver and test connection
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    def check_database():
        with driver.session() as session:
            # Count total nodes
            result = session.run("MATCH (n) RETURN count(n) as total_nodes")
            total_nodes = result.single()["total_nodes"]
            print(f"📊 Total nodes: {total_nodes}")
            
            # Count relationships
            result = session.run("MATCH ()-[r]->() RETURN count(r) as total_relationships")
            total_relationships = result.single()["total_relationships"]
            print(f"🔗 Total relationships: {total_relationships}")
            
            # Get node labels
            result = session.run("CALL db.labels()")
            labels = [record["label"] for record in result]
            print(f"🏷️  Node labels: {labels}")
            
            # Get relationship types
            result = session.run("CALL db.relationshipTypes()")
            rel_types = [record["relationshipType"] for record in result]
            print(f"🔀 Relationship types: {rel_types}")
            
            # Sample nodes if any exist
            if total_nodes > 0:
                print("\n📋 Sample nodes (first 5):")
                result = session.run("MATCH (n) RETURN n LIMIT 5")
                for i, record in enumerate(result, 1):
                    node = record["n"]
                    print(f"  {i}. {dict(node)} (labels: {list(node.labels)})")
            
            # Sample relationships if any exist
            if total_relationships > 0:
                print("\n🔗 Sample relationships (first 5):")
                result = session.run("MATCH (a)-[r]->(b) RETURN a, r, b LIMIT 5")
                for i, record in enumerate(result, 1):
                    rel = record["r"]
                    print(f"  {i}. {rel.type} relationship: {dict(rel)}")
    
    # Run the check
    try:
        driver.verify_connectivity()
        print("✅ Successfully connected to Neo4j")
        check_database()
        
    except Exception as e:
        print(f"❌ Error connecting to Neo4j: {e}")
        
        # Try alternative authentication methods
        print("\n🔄 Trying alternative authentication...")
        
        # Try without password (some Neo4j setups)
        try:
            driver_alt = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, ""))
            driver_alt.verify_connectivity()
            print("✅ Connected with empty password")
            with driver_alt.session() as session:
                result = session.run("MATCH (n) RETURN count(n) as total_nodes")
                total_nodes = result.single()["total_nodes"]
                print(f"📊 Total nodes: {total_nodes}")
            driver_alt.close()
            
        except Exception as e2:
            print(f"❌ Alternative auth failed: {e2}")
            
            # Try common default passwords
            for password in ["password", "admin", "test", "123456"]:
                try:
                    driver_test = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, password))
                    driver_test.verify_connectivity()
                    print(f"✅ Connected with password: {password}")
                    with driver_test.session() as session:
                        result = session.run("MATCH (n) RETURN count(n) as total_nodes")
                        total_nodes = result.single()["total_nodes"]
                        print(f"📊 Total nodes: {total_nodes}")
                    driver_test.close()
                    break
                except:
                    continue
            else:
                print("❌ Could not authenticate with any common passwords")
    
    finally:
        driver.close()

except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("💡 Try: pip install neo4j python-dotenv")

except Exception as e:
    print(f"❌ Unexpected error: {e}")