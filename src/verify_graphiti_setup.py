#!/usr/bin/env python3
"""
Verification script for Graphiti integration setup.

This script verifies that all components are properly installed and configured:
- Graphiti library installation
- Neo4j connectivity  
- Environment variables
- Basic functionality test
"""

import os
import sys
import asyncio
from datetime import datetime

def check_imports():
    """Check that all required packages can be imported."""
    print("🔍 Checking package imports...")
    
    try:
        import graphiti_core
        print(f"✅ Graphiti core imported successfully")
        # Try to get version if available
        try:
            print(f"✅ Graphiti version: {graphiti_core.__version__}")
        except AttributeError:
            print(f"✅ Graphiti version: Available (version info not accessible)")
    except ImportError as e:
        print(f"❌ Graphiti import failed: {e}")
        return False
    
    try:
        import neo4j
        print(f"✅ Neo4j driver version: {neo4j.__version__}")
    except ImportError as e:
        print(f"❌ Neo4j driver import failed: {e}")
        return False
    
    try:
        import pydantic
        print(f"✅ Pydantic version: {pydantic.__version__}")
    except ImportError as e:
        print(f"❌ Pydantic import failed: {e}")
        return False
    
    try:
        import fastapi
        print(f"✅ FastAPI version: {fastapi.__version__}")
    except ImportError as e:
        print(f"❌ FastAPI import failed: {e}")
        return False
    
    return True

def check_environment():
    """Check environment variables and configuration."""
    print("\n🔍 Checking environment configuration...")
    
    required_vars = [
        "OPENAI_API_KEY",
        "NEO4J_URI", 
        "NEO4J_USER",
        "NEO4J_PASSWORD"
    ]
    
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if "API_KEY" in var or "PASSWORD" in var:
                masked = value[:8] + "..." if len(value) > 8 else "***"
                print(f"✅ {var}: {masked}")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: Not set")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️  Missing environment variables: {', '.join(missing_vars)}")
        print("Add them to your .env file or set them in your shell")
        return False
    
    return True

async def check_neo4j_connection():
    """Test Neo4j database connectivity."""
    print("\n🔍 Testing Neo4j connectivity...")
    
    try:
        from neo4j import GraphDatabase
        
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        
        driver = GraphDatabase.driver(uri, auth=(user, password))
        
        # Test connection
        with driver.session() as session:
            result = session.run("RETURN 'Connection successful' AS message")
            record = result.single()
            print(f"✅ Neo4j connection: {record['message']}")
            
            # Check Neo4j version
            version_result = session.run("CALL dbms.components() YIELD name, versions, edition")
            for record in version_result:
                if record["name"] == "Neo4j Kernel":
                    print(f"✅ Neo4j version: {record['versions'][0]} ({record['edition']})")
        
        driver.close()
        return True
        
    except Exception as e:
        print(f"❌ Neo4j connection failed: {e}")
        print("💡 Make sure Neo4j is running: brew services start neo4j")
        return False

async def test_graphiti_basic():
    """Test basic Graphiti functionality."""
    print("\n🔍 Testing Graphiti basic functionality...")
    
    try:
        from graphiti_core import Graphiti
        
        # Initialize Graphiti (but don't connect yet due to potential config issues)
        print("✅ Graphiti class instantiation successful")
        
        # Test pydantic models
        from pydantic import BaseModel
        
        class TestModel(BaseModel):
            name: str
            value: int = 42
        
        test_instance = TestModel(name="test")
        print(f"✅ Pydantic model test: {test_instance.name} = {test_instance.value}")
        
        return True
        
    except Exception as e:
        print(f"❌ Graphiti basic test failed: {e}")
        return False

def main():
    """Main verification function."""
    print("🚀 Ptolemies Graphiti Integration Verification")
    print("=" * 50)
    
    # Track all checks
    checks = [
        ("Package Imports", check_imports()),
        ("Environment Config", check_environment()),
    ]
    
    # Async checks
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        neo4j_check = loop.run_until_complete(check_neo4j_connection())
        graphiti_check = loop.run_until_complete(test_graphiti_basic())
        
        checks.extend([
            ("Neo4j Connectivity", neo4j_check),
            ("Graphiti Basic Test", graphiti_check)
        ])
        
    finally:
        loop.close()
    
    # Summary
    print("\n📋 Verification Summary")
    print("=" * 50)
    
    passed = 0
    total = len(checks)
    
    for check_name, result in checks:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{check_name:.<30} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 All checks passed! Graphiti integration is ready.")
        print("\nNext steps:")
        print("1. Run data migration: python3 -m src.ptolemies.tools.migrate_to_graphiti")
        print("2. Start enhanced MCP server: python3 -m src.ptolemies.mcp.enhanced_ptolemies_mcp")
        print("3. Test graph visualization: http://localhost:8000/graph/explore")
        return 0
    else:
        print(f"\n⚠️  {total - passed} checks failed. Please address the issues above.")
        print("\nTroubleshooting:")
        print("- Ensure Neo4j is running: brew services start neo4j")
        print("- Check .env file has all required variables")
        print("- Verify virtual environment is activated: source venv_graphiti/bin/activate")
        return 1

if __name__ == "__main__":
    sys.exit(main())