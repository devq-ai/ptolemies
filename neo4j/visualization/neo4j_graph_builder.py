#!/usr/bin/env python3
"""
Neo4j Comprehensive Graph Builder
================================

Builds rich relationships between classes, functions, methods, attributes, and frameworks
to create comprehensive code knowledge graphs for visualization and analysis.
"""

import subprocess
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Neo4jGraphBuilder:
    """Build comprehensive code relationship graphs in Neo4j."""
    
    def __init__(self):
        self.neo4j_config = {
            'uri': 'bolt://localhost:7687',
            'user': 'neo4j',
            'password': 'ptolemies',
            'database': 'neo4j'
        }
    
    def run_cypher_query(self, query: str, description: str = "") -> bool:
        """Execute Cypher query."""
        cmd = [
            'cypher-shell',
            '-a', self.neo4j_config['uri'],
            '-u', self.neo4j_config['user'],
            '-p', self.neo4j_config['password'],
            '-d', self.neo4j_config['database'],
            '--format', 'plain'
        ]
        
        try:
            result = subprocess.run(
                cmd, input=query, text=True,
                capture_output=True, timeout=60
            )
            
            if result.returncode == 0:
                if description:
                    logger.info(f"✅ {description}")
                return True
            else:
                logger.error(f"❌ {description}: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Query failed ({description}): {e}")
            return False
    
    def create_comprehensive_schema(self):
        """Create comprehensive schema for code relationships."""
        
        logger.info("🏗️ Creating comprehensive Neo4j schema...")
        
        # Enhanced constraints and indexes
        schema_queries = [
            # Core constraints
            """
            CREATE CONSTRAINT framework_name_unique IF NOT EXISTS 
            FOR (f:Framework) REQUIRE f.name IS UNIQUE;
            """,
            """
            CREATE CONSTRAINT class_full_name_unique IF NOT EXISTS 
            FOR (c:Class) REQUIRE c.full_name IS UNIQUE;
            """,
            """
            CREATE CONSTRAINT method_full_name_unique IF NOT EXISTS 
            FOR (m:Method) REQUIRE m.full_name IS UNIQUE;
            """,
            """
            CREATE CONSTRAINT function_full_name_unique IF NOT EXISTS 
            FOR (f:Function) REQUIRE f.full_name IS UNIQUE;
            """,
            """
            CREATE CONSTRAINT attribute_full_name_unique IF NOT EXISTS 
            FOR (a:Attribute) REQUIRE a.full_name IS UNIQUE;
            """,
            """
            CREATE CONSTRAINT module_full_name_unique IF NOT EXISTS 
            FOR (m:Module) REQUIRE m.full_name IS UNIQUE;
            """,
            
            # Performance indexes
            """
            CREATE INDEX framework_type_idx IF NOT EXISTS 
            FOR (f:Framework) ON (f.type);
            """,
            """
            CREATE INDEX class_module_idx IF NOT EXISTS 
            FOR (c:Class) ON (c.module);
            """,
            """
            CREATE INDEX method_visibility_idx IF NOT EXISTS 
            FOR (m:Method) ON (m.visibility);
            """,
            """
            CREATE INDEX function_type_idx IF NOT EXISTS 
            FOR (f:Function) ON (f.function_type);
            """,
            
            # Full-text search indexes
            """
            CREATE TEXT INDEX code_elements_search IF NOT EXISTS 
            FOR (n:Framework) ON EACH [n.name, n.description];
            """,
            """
            CREATE TEXT INDEX class_search IF NOT EXISTS 
            FOR (n:Class) ON EACH [n.name, n.description, n.docstring];
            """,
            """
            CREATE TEXT INDEX method_search IF NOT EXISTS 
            FOR (n:Method) ON EACH [n.name, n.description, n.docstring];
            """
        ]
        
        for i, query in enumerate(schema_queries):
            self.run_cypher_query(query, f"Schema step {i+1}/{len(schema_queries)}")
    
    def build_framework_hierarchy(self):
        """Build framework dependency and integration hierarchies."""
        
        logger.info("🔗 Building framework hierarchy relationships...")
        
        # Define framework categories and relationships
        framework_relationships = [
            # Web frameworks
            ("FastAPI", "DEPENDS_ON", "Pydantic AI", "validation"),
            ("FastAPI", "INTEGRATES_WITH", "Logfire", "observability"),
            ("FastAPI", "CONNECTS_TO", "SurrealDB", "database"),
            ("NextJS", "USES", "Tailwind", "styling"),
            ("NextJS", "INCLUDES", "Shadcn", "components"),
            
            # AI/ML stack
            ("Pydantic AI", "ENHANCED_BY", "Logfire", "monitoring"),
            ("Panel", "VISUALIZES", "bokeh", "plotting"),
            ("PyMC", "RELATES_TO", "PyGAD", "optimization"),
            
            # Development tools
            ("Claude Code", "WORKS_WITH", "FastMCP", "mcp_protocol"),
            ("Crawl4AI", "PROCESSES", "AnimeJS", "web_content"),
            
            # Specialized tools
            ("circom", "IMPLEMENTS", "Wildwood", "zero_knowledge"),
            
            # Cross-framework relationships
            ("FastAPI", "DOCUMENTED_BY", "Claude Code", "documentation"),
            ("SurrealDB", "CRAWLED_BY", "Crawl4AI", "data_extraction"),
        ]
        
        for source, relationship, target, context in framework_relationships:
            query = f"""
            MATCH (source:Framework {{name: "{source}"}}), (target:Framework {{name: "{target}"}})
            MERGE (source)-[r:{relationship}]->(target)
            SET r.context = "{context}",
                r.created_at = datetime(),
                r.relationship_type = "framework_integration";
            """
            self.run_cypher_query(query, f"Framework relationship: {source} -> {target}")
    
    def build_inheritance_chains(self):
        """Build class inheritance and composition relationships."""
        
        logger.info("🧬 Building inheritance and composition chains...")
        
        # Define inheritance patterns for major frameworks
        inheritance_patterns = [
            # FastAPI inheritance
            ("fastapi.FastAPI", "INHERITS_FROM", "fastapi.applications.FastAPI", "base_class"),
            ("fastapi.Request", "INHERITS_FROM", "starlette.requests.Request", "web_framework"),
            ("fastapi.Response", "INHERITS_FROM", "starlette.responses.Response", "web_framework"),
            ("fastapi.HTTPException", "INHERITS_FROM", "Exception", "error_handling"),
            
            # Pydantic AI patterns
            ("pydantic_ai.Agent", "COMPOSED_OF", "pydantic_ai.models.Model", "ai_model"),
            ("pydantic_ai.RunContext", "CONTAINS", "pydantic_ai.dependencies.Dependencies", "context"),
            
            # Panel patterns
            ("panel.Panel", "INHERITS_FROM", "param.Parameterized", "parameter_framework"),
            ("panel.Param", "EXTENDS", "param.Parameter", "configuration"),
            
            # SurrealDB patterns
            ("surrealdb.Surreal", "IMPLEMENTS", "surrealdb.Connection", "database_interface"),
        ]
        
        for source_class, relationship, target_class, context in inheritance_patterns:
            # Create target class if it doesn't exist
            create_target_query = f"""
            MERGE (target:Class {{full_name: "{target_class}"}})
            SET target.name = split("{target_class}", ".")[size(split("{target_class}", "."))-1],
                target.module = substring("{target_class}", 0, size("{target_class}") - size(split("{target_class}", ".")[size(split("{target_class}", "."))-1]) - 1),
                target.inferred = true,
                target.created_at = datetime();
            """
            self.run_cypher_query(create_target_query, f"Create inferred class: {target_class}")
            
            # Create relationship
            relationship_query = f"""
            MATCH (source:Class {{full_name: "{source_class}"}}), (target:Class {{full_name: "{target_class}"}})
            MERGE (source)-[r:{relationship}]->(target)
            SET r.context = "{context}",
                r.created_at = datetime(),
                r.relationship_type = "code_structure";
            """
            self.run_cypher_query(relationship_query, f"Inheritance: {source_class} -> {target_class}")
    
    def build_method_relationships(self):
        """Build method call and override relationships."""
        
        logger.info("🔧 Building method relationships...")
        
        # Method call patterns and overrides
        method_patterns = [
            # FastAPI method patterns
            ("fastapi.FastAPI.get", "CALLS", "fastapi.routing.add_api_route", "route_decoration"),
            ("fastapi.FastAPI.post", "CALLS", "fastapi.routing.add_api_route", "route_decoration"),
            ("fastapi.FastAPI.include_router", "CALLS", "fastapi.routing.include_router", "router_composition"),
            
            # Pydantic AI patterns
            ("pydantic_ai.Agent.run", "CALLS", "pydantic_ai.Agent._run_sync", "async_execution"),
            ("pydantic_ai.Agent.run_sync", "IMPLEMENTS", "pydantic_ai.Agent.run", "sync_wrapper"),
            
            # SurrealDB patterns
            ("surrealdb.Surreal.connect", "INITIALIZES", "surrealdb.Surreal.connection", "database_setup"),
            ("surrealdb.Surreal.query", "USES", "surrealdb.Surreal.connection", "query_execution"),
            ("surrealdb.Surreal.use", "CONFIGURES", "surrealdb.Surreal.connection", "namespace_setup"),
        ]
        
        for source_method, relationship, target_method, context in method_patterns:
            # Create target method if it doesn't exist
            target_parts = target_method.split('.')
            if len(target_parts) >= 2:
                target_class = '.'.join(target_parts[:-1])
                method_name = target_parts[-1]
                
                create_target_query = f"""
                MERGE (target_class:Class {{full_name: "{target_class}"}})
                SET target_class.inferred = true
                MERGE (target_method:Method {{full_name: "{target_method}"}})
                SET target_method.name = "{method_name}",
                    target_method.inferred = true,
                    target_method.created_at = datetime()
                MERGE (target_class)-[:HAS_METHOD]->(target_method);
                """
                self.run_cypher_query(create_target_query, f"Create inferred method: {target_method}")
            
            # Create method relationship
            relationship_query = f"""
            MATCH (source:Method {{full_name: "{source_method}"}}), (target:Method {{full_name: "{target_method}"}})
            MERGE (source)-[r:{relationship}]->(target)
            SET r.context = "{context}",
                r.created_at = datetime(),
                r.relationship_type = "method_interaction";
            """
            self.run_cypher_query(relationship_query, f"Method relationship: {source_method} -> {target_method}")
    
    def build_parameter_relationships(self):
        """Build function/method parameter and return type relationships."""
        
        logger.info("📋 Building parameter and type relationships...")
        
        # Parameter type relationships
        parameter_patterns = [
            # FastAPI parameters
            ("fastapi.Depends", "PROVIDES", "Dependency", "dependency_injection"),
            ("fastapi.Query", "VALIDATES", "QueryParameter", "request_validation"),
            ("fastapi.Path", "EXTRACTS", "PathParameter", "url_parsing"),
            ("fastapi.Body", "DESERIALIZES", "RequestBody", "request_processing"),
            
            # Common return types
            ("fastapi.FastAPI.get", "RETURNS", "Response", "http_response"),
            ("pydantic_ai.Agent.run", "RETURNS", "RunResult", "ai_execution_result"),
            ("surrealdb.Surreal.query", "RETURNS", "QueryResult", "database_result"),
        ]
        
        for function_name, relationship, type_name, context in parameter_patterns:
            # Create type node
            create_type_query = f"""
            MERGE (type:Type {{name: "{type_name}"}})
            SET type.category = "parameter_type",
                type.created_at = datetime();
            """
            self.run_cypher_query(create_type_query, f"Create type: {type_name}")
            
            # Create relationship
            if "." in function_name:
                # Method or function
                node_type = "Method" if function_name.count('.') >= 2 else "Function"
                relationship_query = f"""
                MATCH (func:{node_type} {{full_name: "{function_name}"}}), (type:Type {{name: "{type_name}"}})
                MERGE (func)-[r:{relationship}]->(type)
                SET r.context = "{context}",
                    r.created_at = datetime(),
                    r.relationship_type = "type_relationship";
                """
                self.run_cypher_query(relationship_query, f"Parameter relationship: {function_name} -> {type_name}")
    
    def build_usage_patterns(self):
        """Build common usage pattern relationships."""
        
        logger.info("📊 Building usage pattern relationships...")
        
        # Usage patterns from documentation
        usage_patterns = [
            # FastAPI usage patterns
            ("FastAPI", "COMMONLY_USES", "fastapi.FastAPI", "application_creation"),
            ("FastAPI", "COMMONLY_USES", "fastapi.Depends", "dependency_injection"),
            ("FastAPI", "COMMONLY_USES", "pydantic.BaseModel", "data_validation"),
            
            # Pydantic AI patterns
            ("Pydantic AI", "COMMONLY_USES", "pydantic_ai.Agent", "ai_agent_creation"),
            ("Pydantic AI", "INTEGRATES_WITH", "FastAPI", "web_ai_integration"),
            
            # Panel patterns
            ("Panel", "COMMONLY_USES", "panel.Panel", "dashboard_creation"),
            ("Panel", "INTEGRATES_WITH", "bokeh", "visualization"),
            
            # SurrealDB patterns
            ("SurrealDB", "COMMONLY_USES", "surrealdb.Surreal", "database_client"),
            ("SurrealDB", "SUPPORTS", "SQL", "query_language"),
        ]
        
        for framework, relationship, target, context in usage_patterns:
            query = f"""
            MATCH (framework:Framework {{name: "{framework}"}})
            MERGE (target_node:UsagePattern {{name: "{target}"}})
            SET target_node.context = "{context}",
                target_node.created_at = datetime()
            MERGE (framework)-[r:{relationship}]->(target_node)
            SET r.pattern_type = "common_usage",
                r.created_at = datetime();
            """
            self.run_cypher_query(query, f"Usage pattern: {framework} -> {target}")
    
    def create_code_complexity_metrics(self):
        """Add complexity and metrics to code elements."""
        
        logger.info("📈 Adding complexity metrics to code elements...")
        
        # Add complexity metrics to methods
        complexity_query = """
        MATCH (m:Method)
        SET m.complexity_estimated = 
            CASE 
                WHEN m.parameters IS NOT NULL AND size(split(m.parameters, ',')) > 5 THEN 'high'
                WHEN m.parameters IS NOT NULL AND size(split(m.parameters, ',')) > 2 THEN 'medium'
                ELSE 'low'
            END,
        m.parameter_count = 
            CASE 
                WHEN m.parameters IS NOT NULL THEN size(split(m.parameters, ','))
                ELSE 0
            END;
        """
        self.run_cypher_query(complexity_query, "Method complexity metrics")
        
        # Add framework maturity scores
        maturity_query = """
        MATCH (f:Framework)
        SET f.maturity_score = 
            CASE f.name
                WHEN 'FastAPI' THEN 9
                WHEN 'NextJS' THEN 9
                WHEN 'Pydantic AI' THEN 7
                WHEN 'SurrealDB' THEN 6
                WHEN 'Panel' THEN 8
                WHEN 'bokeh' THEN 8
                WHEN 'Tailwind' THEN 9
                WHEN 'Claude Code' THEN 6
                WHEN 'Logfire' THEN 6
                ELSE 5
            END,
        f.documentation_quality = 
            CASE f.name
                WHEN 'FastAPI' THEN 'excellent'
                WHEN 'NextJS' THEN 'excellent'
                WHEN 'Pydantic AI' THEN 'good'
                WHEN 'SurrealDB' THEN 'developing'
                ELSE 'fair'
            END;
        """
        self.run_cypher_query(maturity_query, "Framework maturity scores")
    
    def generate_visualization_queries(self) -> Dict[str, str]:
        """Generate useful queries for graph visualization."""
        
        queries = {
            "framework_overview": """
            MATCH (f:Framework)
            OPTIONAL MATCH (f)-[r1]->(c:Class)
            OPTIONAL MATCH (c)-[r2]->(m:Method)
            RETURN f.name as framework, 
                   count(DISTINCT c) as classes, 
                   count(DISTINCT m) as methods,
                   f.maturity_score as maturity
            ORDER BY maturity DESC;
            """,
            
            "framework_relationships": """
            MATCH (f1:Framework)-[r]->(f2:Framework)
            RETURN f1.name as source, 
                   type(r) as relationship, 
                   f2.name as target,
                   r.context as context;
            """,
            
            "class_inheritance_tree": """
            MATCH (c1:Class)-[r:INHERITS_FROM|COMPOSED_OF|EXTENDS]->(c2:Class)
            RETURN c1.name as child_class,
                   c1.module as child_module,
                   type(r) as relationship,
                   c2.name as parent_class,
                   c2.module as parent_module;
            """,
            
            "method_call_chains": """
            MATCH (m1:Method)-[r:CALLS|IMPLEMENTS|USES]->(m2:Method)
            RETURN m1.full_name as calling_method,
                   type(r) as relationship,
                   m2.full_name as called_method,
                   r.context as context;
            """,
            
            "framework_ecosystem": """
            MATCH (f:Framework)
            OPTIONAL MATCH (f)-[r1:HAS_CLASS]->(c:Class)
            OPTIONAL MATCH (c)-[r2:HAS_METHOD]->(m:Method)
            OPTIONAL MATCH (f)-[r3:HAS_FUNCTION]->(func:Function)
            RETURN f.name as framework,
                   collect(DISTINCT c.name) as classes,
                   collect(DISTINCT m.name) as methods,
                   collect(DISTINCT func.name) as functions,
                   f.type as framework_type;
            """,
            
            "high_complexity_elements": """
            MATCH (m:Method)
            WHERE m.complexity_estimated = 'high'
            OPTIONAL MATCH (c:Class)-[:HAS_METHOD]->(m)
            OPTIONAL MATCH (f:Framework)-[:HAS_CLASS]->(c)
            RETURN f.name as framework,
                   c.name as class,
                   m.name as method,
                   m.parameter_count as params
            ORDER BY m.parameter_count DESC;
            """,
            
            "framework_integration_map": """
            MATCH (f1:Framework)-[r]->(f2:Framework)
            WHERE type(r) IN ['INTEGRATES_WITH', 'DEPENDS_ON', 'USES']
            RETURN f1.name as from_framework,
                   f2.name as to_framework,
                   type(r) as integration_type,
                   r.context as context;
            """,
            
            "code_search_by_name": """
            // Usage: Replace 'FastAPI' with your search term
            CALL db.index.fulltext.queryNodes('code_elements_search', 'FastAPI')
            YIELD node, score
            RETURN labels(node) as node_type,
                   node.name as name,
                   node.description as description,
                   score
            ORDER BY score DESC;
            """
        }
        
        return queries
    
    def export_visualization_queries(self, queries: Dict[str, str]):
        """Export visualization queries to a file."""
        
        query_file = "neo4j_visualization_queries.cypher"
        
        with open(query_file, 'w') as f:
            f.write("# Neo4j Graph Visualization Queries\n")
            f.write("# ===================================\n\n")
            f.write("# Generated on: " + datetime.now().isoformat() + "\n\n")
            
            for name, query in queries.items():
                f.write(f"# {name.replace('_', ' ').title()}\n")
                f.write(f"# {'-' * len(name)}\n")
                f.write(query.strip() + "\n\n")
        
        logger.info(f"📄 Visualization queries exported to: {query_file}")
    
    def build_comprehensive_graph(self):
        """Build the complete comprehensive graph."""
        
        logger.info("🚀 Building Comprehensive Neo4j Knowledge Graph")
        logger.info("=" * 50)
        
        # Step 1: Create schema
        self.create_comprehensive_schema()
        
        # Step 2: Build framework relationships
        self.build_framework_hierarchy()
        
        # Step 3: Build inheritance chains
        self.build_inheritance_chains()
        
        # Step 4: Build method relationships
        self.build_method_relationships()
        
        # Step 5: Build parameter relationships
        self.build_parameter_relationships()
        
        # Step 6: Build usage patterns
        self.build_usage_patterns()
        
        # Step 7: Add complexity metrics
        self.create_code_complexity_metrics()
        
        # Step 8: Generate and export visualization queries
        queries = self.generate_visualization_queries()
        self.export_visualization_queries(queries)
        
        # Final verification
        self.verify_graph_completeness()
        
        logger.info("\n🎉 Comprehensive Neo4j Knowledge Graph Complete!")
        logger.info("="*50)
    
    def verify_graph_completeness(self):
        """Verify the completeness of the built graph."""
        
        logger.info("🔍 Verifying graph completeness...")
        
        verification_queries = [
            ("Total nodes", "MATCH (n) RETURN count(n) as total;"),
            ("Total relationships", "MATCH ()-[r]->() RETURN count(r) as total;"),
            ("Framework nodes", "MATCH (f:Framework) RETURN count(f) as total;"),
            ("Class nodes", "MATCH (c:Class) RETURN count(c) as total;"),
            ("Method nodes", "MATCH (m:Method) RETURN count(m) as total;"),
            ("Function nodes", "MATCH (f:Function) RETURN count(f) as total;"),
            ("Type nodes", "MATCH (t:Type) RETURN count(t) as total;"),
            ("Usage pattern nodes", "MATCH (u:UsagePattern) RETURN count(u) as total;"),
        ]
        
        print("\n📊 Graph Statistics:")
        print("-" * 30)
        
        for description, query in verification_queries:
            cmd = [
                'cypher-shell',
                '-a', self.neo4j_config['uri'],
                '-u', self.neo4j_config['user'],
                '-p', self.neo4j_config['password'],
                '-d', self.neo4j_config['database'],
                '--format', 'plain'
            ]
            
            try:
                result = subprocess.run(
                    cmd, input=query, text=True,
                    capture_output=True, timeout=30
                )
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        count = lines[1].strip('"')
                        print(f"  {description}: {count}")
                        
            except Exception as e:
                print(f"  {description}: Error - {e}")

def main():
    """Main execution function."""
    
    builder = Neo4jGraphBuilder()
    
    try:
        builder.build_comprehensive_graph()
        
        print("\n✅ Neo4j comprehensive graph building complete!")
        print("\n📖 Next steps:")
        print("  1. Open Neo4j Browser: http://localhost:7474")
        print("  2. Use queries from 'neo4j_visualization_queries.cypher'")
        print("  3. Explore framework relationships and code structures")
        print("  4. Visualize inheritance trees and method call chains")
        
    except Exception as e:
        logger.error(f"Critical error: {e}")

if __name__ == "__main__":
    main()