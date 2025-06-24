#!/usr/bin/env python3
"""
Complete Neo4j Graph Population
==============================

Ensures Neo4j has a complete graph with all framework data
for comprehensive RAG and hallucination detection.
"""

import subprocess
import json
from datetime import datetime

def run_neo4j_query(query: str) -> bool:
    """Execute Neo4j query."""
    cmd = [
        'cypher-shell',
        '-a', 'bolt://localhost:7687',
        '-u', 'neo4j',
        '-p', 'ptolemies',
        '-d', 'neo4j',
        '--format', 'plain'
    ]
    
    try:
        result = subprocess.run(
            cmd, input=query, text=True,
            capture_output=True, timeout=30
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Neo4j query error: {e}")
        return False

def get_surrealdb_sources() -> list:
    """Get all sources from SurrealDB."""
    cmd = [
        'surreal', 'sql',
        '--conn', 'ws://localhost:8000/rpc',
        '--user', 'root',
        '--pass', 'root',
        '--ns', 'ptolemies',
        '--db', 'knowledge',
        '--pretty'
    ]
    
    query = "SELECT DISTINCT source_name FROM document_chunks;"
    
    try:
        result = subprocess.run(
            cmd, input=query, text=True,
            capture_output=True, timeout=30
        )
        
        sources = []
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if 'source_name:' in line:
                    source = line.split("source_name: '")[1].split("'")[0]
                    sources.append(source)
        
        return sources
    except Exception as e:
        print(f"SurrealDB query error: {e}")
        return []

def populate_complete_graph():
    """Populate Neo4j with complete framework data."""
    
    print("🔗 Starting complete Neo4j graph population...")
    
    # Get sources from SurrealDB
    sources = get_surrealdb_sources()
    print(f"📊 Found {len(sources)} sources in SurrealDB")
    
    # Create comprehensive framework schema
    schema_query = """
    // Complete Framework Schema
    CREATE CONSTRAINT framework_name IF NOT EXISTS FOR (f:Framework) REQUIRE f.name IS UNIQUE;
    CREATE CONSTRAINT class_full_name IF NOT EXISTS FOR (c:Class) REQUIRE c.full_name IS UNIQUE;
    CREATE CONSTRAINT method_full_name IF NOT EXISTS FOR (m:Method) REQUIRE m.full_name IS UNIQUE;
    CREATE CONSTRAINT function_full_name IF NOT EXISTS FOR (f:Function) REQUIRE f.full_name IS UNIQUE;
    
    // Indexes for performance
    CREATE INDEX framework_type IF NOT EXISTS FOR (f:Framework) ON (f.type);
    CREATE INDEX class_module IF NOT EXISTS FOR (c:Class) ON (c.module);
    CREATE TEXT INDEX content_search IF NOT EXISTS FOR (n:Framework|Class|Method|Function) ON EACH [n.name, n.description];
    """
    
    print("📐 Creating schema...")
    if run_neo4j_query(schema_query):
        print("✅ Schema created")
    
    # Populate frameworks from crawled sources
    framework_mappings = {
        "FastAPI": {"language": "Python", "type": "web_framework"},
        "Pydantic AI": {"language": "Python", "type": "ai_framework"},
        "SurrealDB": {"language": "Rust", "type": "database"},
        "Logfire": {"language": "Python", "type": "observability"},
        "NextJS": {"language": "JavaScript", "type": "web_framework"},
        "Claude Code": {"language": "Various", "type": "development_tool"},
        "Crawl4AI": {"language": "Python", "type": "scraping_framework"},
        "FastMCP": {"language": "Python", "type": "mcp_framework"},
        "Tailwind": {"language": "CSS", "type": "css_framework"},
        "AnimeJS": {"language": "JavaScript", "type": "animation"},
        "Shadcn": {"language": "TypeScript", "type": "ui_framework"},
        "Panel": {"language": "Python", "type": "visualization"},
        "bokeh": {"language": "Python", "type": "visualization"},
        "PyMC": {"language": "Python", "type": "statistics"},
        "Wildwood": {"language": "Various", "type": "machine_learning"},
        "PyGAD": {"language": "Python", "type": "genetic_algorithm"},
        "circom": {"language": "Various", "type": "zero_knowledge"}
    }
    
    # Create framework nodes
    for source in sources:
        if source in framework_mappings:
            mapping = framework_mappings[source]
            query = f"""
            MERGE (f:Framework {{
                name: "{source}",
                language: "{mapping['language']}",
                type: "{mapping['type']}",
                created_at: datetime(),
                has_documentation: true
            }});
            """
            
            if run_neo4j_query(query):
                print(f"✅ Framework: {source}")
    
    # Add common classes for major frameworks
    common_classes = [
        # FastAPI
        {"framework": "FastAPI", "name": "FastAPI", "module": "fastapi", "description": "Main FastAPI application class"},
        {"framework": "FastAPI", "name": "Request", "module": "fastapi", "description": "HTTP request object"},
        {"framework": "FastAPI", "name": "Response", "module": "fastapi", "description": "HTTP response object"},
        {"framework": "FastAPI", "name": "HTTPException", "module": "fastapi", "description": "HTTP exception class"},
        
        # Pydantic AI
        {"framework": "Pydantic AI", "name": "Agent", "module": "pydantic_ai", "description": "AI agent class"},
        {"framework": "Pydantic AI", "name": "RunContext", "module": "pydantic_ai", "description": "Agent runtime context"},
        
        # SurrealDB
        {"framework": "SurrealDB", "name": "Surreal", "module": "surrealdb", "description": "SurrealDB client class"},
        
        # Panel
        {"framework": "Panel", "name": "Panel", "module": "panel", "description": "Panel application class"},
        {"framework": "Panel", "name": "Param", "module": "panel", "description": "Parameter definition class"},
    ]
    
    for cls in common_classes:
        query = f"""
        MATCH (f:Framework {{name: "{cls['framework']}"}})
        MERGE (c:Class {{
            name: "{cls['name']}",
            full_name: "{cls['module']}.{cls['name']}",
            module: "{cls['module']}",
            description: "{cls['description']}",
            framework: "{cls['framework']}",
            created_at: datetime()
        }})
        MERGE (f)-[:HAS_CLASS]->(c);
        """
        
        if run_neo4j_query(query):
            print(f"✅ Class: {cls['framework']}.{cls['name']}")
    
    # Add common methods
    common_methods = [
        # FastAPI methods
        {"class": "fastapi.FastAPI", "name": "get", "params": ["path", "response_model", "status_code"]},
        {"class": "fastapi.FastAPI", "name": "post", "params": ["path", "response_model", "status_code"]},
        {"class": "fastapi.FastAPI", "name": "put", "params": ["path", "response_model", "status_code"]},
        {"class": "fastapi.FastAPI", "name": "delete", "params": ["path", "response_model", "status_code"]},
        {"class": "fastapi.FastAPI", "name": "include_router", "params": ["router", "prefix", "tags"]},
        
        # Pydantic AI methods
        {"class": "pydantic_ai.Agent", "name": "run", "params": ["user_prompt", "message_history"]},
        {"class": "pydantic_ai.Agent", "name": "run_sync", "params": ["user_prompt", "message_history"]},
        
        # SurrealDB methods
        {"class": "surrealdb.Surreal", "name": "connect", "params": ["url"]},
        {"class": "surrealdb.Surreal", "name": "use", "params": ["namespace", "database"]},
        {"class": "surrealdb.Surreal", "name": "query", "params": ["sql", "vars"]},
    ]
    
    for method in common_methods:
        params_str = ", ".join(method['params'])
        query = f"""
        MATCH (c:Class {{full_name: "{method['class']}"}})
        MERGE (m:Method {{
            name: "{method['name']}",
            full_name: "{method['class']}.{method['name']}",
            parameters: "{params_str}",
            visibility: "public",
            created_at: datetime()
        }})
        MERGE (c)-[:HAS_METHOD]->(m);
        """
        
        if run_neo4j_query(query):
            print(f"✅ Method: {method['class']}.{method['name']}")
    
    # Add common functions
    common_functions = [
        {"module": "fastapi", "name": "Depends", "params": ["dependency"], "description": "Dependency injection"},
        {"module": "fastapi", "name": "Query", "params": ["default", "alias"], "description": "Query parameter"},
        {"module": "fastapi", "name": "Path", "params": ["default", "alias"], "description": "Path parameter"},
        {"module": "fastapi", "name": "Body", "params": ["default", "embed"], "description": "Request body parameter"},
    ]
    
    for func in common_functions:
        params_str = ", ".join(func['params'])
        query = f"""
        MATCH (f:Framework {{name: "FastAPI"}})
        MERGE (fn:Function {{
            name: "{func['name']}",
            full_name: "{func['module']}.{func['name']}",
            module: "{func['module']}",
            parameters: "{params_str}",
            description: "{func['description']}",
            created_at: datetime()
        }})
        MERGE (f)-[:HAS_FUNCTION]->(fn);
        """
        
        if run_neo4j_query(query):
            print(f"✅ Function: {func['module']}.{func['name']}")
    
    # Create relationships between frameworks
    integration_query = """
    // Framework integration relationships
    MATCH (fastapi:Framework {name: "FastAPI"}), (pydantic:Framework {name: "Pydantic AI"})
    MERGE (fastapi)-[:INTEGRATES_WITH {type: "ai_integration"}]->(pydantic);
    
    MATCH (fastapi:Framework {name: "FastAPI"}), (logfire:Framework {name: "Logfire"})
    MERGE (fastapi)-[:INTEGRATES_WITH {type: "observability"}]->(logfire);
    
    MATCH (fastapi:Framework {name: "FastAPI"}), (surrealdb:Framework {name: "SurrealDB"})
    MERGE (fastapi)-[:INTEGRATES_WITH {type: "database"}]->(surrealdb);
    
    MATCH (nextjs:Framework {name: "NextJS"}), (tailwind:Framework {name: "Tailwind"})
    MERGE (nextjs)-[:INTEGRATES_WITH {type: "styling"}]->(tailwind);
    
    MATCH (nextjs:Framework {name: "NextJS"}), (shadcn:Framework {name: "Shadcn"})
    MERGE (nextjs)-[:INTEGRATES_WITH {type: "components"}]->(shadcn);
    """
    
    print("🔗 Creating framework relationships...")
    if run_neo4j_query(integration_query):
        print("✅ Relationships created")
    
    # Verify final state
    verification_query = """
    MATCH (n)
    WHERE n:Framework OR n:Class OR n:Method OR n:Function
    RETURN labels(n)[0] as type, count(*) as count
    ORDER BY type;
    """
    
    print("\n📊 Final Neo4j Graph Status:")
    cmd = [
        'cypher-shell',
        '-a', 'bolt://localhost:7687',
        '-u', 'neo4j',
        '-p', 'ptolemies',
        '-d', 'neo4j',
        '--format', 'plain'
    ]
    
    result = subprocess.run(
        cmd, input=verification_query, text=True,
        capture_output=True, timeout=30
    )
    
    if result.returncode == 0:
        lines = result.stdout.strip().split('\n')
        total_nodes = 0
        if len(lines) > 1:
            for line in lines[1:]:
                if line.strip():
                    parts = line.split(', ')
                    if len(parts) == 2:
                        node_type = parts[0].strip('"')
                        count = int(parts[1].strip('"'))
                        total_nodes += count
                        print(f"  {node_type}: {count}")
        
        print(f"\n🎯 Total Neo4j Nodes: {total_nodes}")
        
        if total_nodes >= 100:
            print("✅ Neo4j graph is comprehensive!")
            return True
        else:
            print("⚠️  Neo4j graph needs more data")
            return False
    
    return False

def main():
    """Main execution."""
    print("🚀 Complete Neo4j Graph Population")
    print("=" * 40)
    
    success = populate_complete_graph()
    
    if success:
        print("\n🎉 Neo4j graph population complete!")
        print("✅ Ready for comprehensive RAG and hallucination detection")
    else:
        print("\n⚠️  Graph population had issues")

if __name__ == "__main__":
    main()