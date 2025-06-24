#!/usr/bin/env python3
"""
Populate Neo4j Knowledge Base with Ptolemies Code Documentation
==============================================================

Imports all discovered code elements into Neo4j to enable
AI hallucination detection and code understanding.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any

class CodeKnowledgePopulator:
    """Populates Neo4j with comprehensive code documentation."""
    
    def __init__(self):
        self.neo4j_uri = "bolt://localhost:7687"
        self.neo4j_user = "neo4j"
        self.neo4j_password = "ptolemies"
        self.tasks_file = Path("context7_documentation_tasks.json")
        
    def run_cypher_query(self, query: str) -> bool:
        """Execute Cypher query."""
        cmd = [
            'cypher-shell',
            '-a', self.neo4j_uri,
            '-u', self.neo4j_user,
            '-p', self.neo4j_password,
            '-d', 'neo4j',
            '--format', 'plain'
        ]
        
        try:
            result = subprocess.run(
                cmd,
                input=query,
                text=True,
                capture_output=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return True
            else:
                print(f"Query failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"Neo4j query error: {e}")
            return False
    
    def create_schema(self):
        """Create comprehensive code documentation schema."""
        print("📐 Creating code documentation schema...")
        
        schema_query = """
        // Code Documentation Schema
        // ========================
        
        // Constraints
        CREATE CONSTRAINT module_name IF NOT EXISTS FOR (m:Module) REQUIRE m.name IS UNIQUE;
        CREATE CONSTRAINT class_full_name IF NOT EXISTS FOR (c:Class) REQUIRE c.full_name IS UNIQUE;
        CREATE CONSTRAINT method_full_name IF NOT EXISTS FOR (m:Method) REQUIRE m.full_name IS UNIQUE;
        CREATE CONSTRAINT function_full_name IF NOT EXISTS FOR (f:Function) REQUIRE f.full_name IS UNIQUE;
        
        // Indexes
        CREATE INDEX module_type IF NOT EXISTS FOR (m:Module) ON (m.type);
        CREATE INDEX class_name IF NOT EXISTS FOR (c:Class) ON (c.name);
        CREATE INDEX method_name IF NOT EXISTS FOR (m:Method) ON (m.name);
        CREATE INDEX function_name IF NOT EXISTS FOR (f:Function) ON (f.name);
        CREATE TEXT INDEX code_search IF NOT EXISTS FOR (n:Class|Method|Function) ON EACH [n.name, n.docstring];
        """
        
        if self.run_cypher_query(schema_query):
            print("✅ Schema created successfully")
        else:
            print("⚠️  Schema creation had issues")
    
    def populate_ptolemies_modules(self):
        """Populate key Ptolemies modules."""
        print("\n📦 Populating Ptolemies modules...")
        
        modules_query = """
        // Core Ptolemies Modules
        MERGE (ptolemies:Module {name: "ptolemies", type: "package"})
        SET ptolemies.description = "Advanced Knowledge Management Platform",
            ptolemies.version = "1.0.0",
            ptolemies.created_at = datetime();
        
        MERGE (src:Module {name: "ptolemies.src", type: "package"})
        SET src.description = "Source code modules",
            src.parent_module = "ptolemies";
        
        MERGE (tests:Module {name: "ptolemies.tests", type: "package"})
        SET tests.description = "Test modules",
            tests.parent_module = "ptolemies";
        
        // Create module relationships
        MATCH (p:Module {name: "ptolemies"}), (s:Module {name: "ptolemies.src"})
        MERGE (p)-[:HAS_MODULE]->(s);
        
        MATCH (p:Module {name: "ptolemies"}), (t:Module {name: "ptolemies.tests"})
        MERGE (p)-[:HAS_MODULE]->(t);
        """
        
        if self.run_cypher_query(modules_query):
            print("✅ Modules populated")
    
    def populate_key_classes(self):
        """Populate key Ptolemies classes."""
        print("\n🏗️ Populating key classes...")
        
        # Key crawler classes
        crawler_classes = [
            {
                "name": "ProductionCrawlerHybrid",
                "full_name": "src.production_crawler_hybrid.ProductionCrawlerHybrid",
                "module": "src.production_crawler_hybrid",
                "description": "Production-grade hybrid crawler with OpenAI embeddings and SurrealDB storage",
                "methods_count": 15,
                "key_methods": ["initialize", "crawl_source", "generate_embedding", "store_chunk"]
            },
            {
                "name": "IncrementalCrawler",
                "full_name": "src.incremental_crawler.IncrementalCrawler",
                "module": "src.incremental_crawler",
                "description": "Handles incremental updates for large documentation sources",
                "methods_count": 8,
                "key_methods": ["check_for_updates", "crawl_incremental", "merge_changes"]
            },
            {
                "name": "SpecializedCrawlers",
                "full_name": "src.specialized_crawlers.SpecializedCrawlers",
                "module": "src.specialized_crawlers",
                "description": "Specialized crawlers for different documentation formats",
                "methods_count": 12,
                "key_methods": ["crawl_pydantic_ai", "crawl_logfire", "crawl_pymc", "crawl_animejs"]
            },
            {
                "name": "RecoveryManager",
                "full_name": "src.recovery_system.RecoveryManager",
                "module": "src.recovery_system",
                "description": "Manages crawler recovery and resilience",
                "methods_count": 10,
                "key_methods": ["save_checkpoint", "restore_from_checkpoint", "handle_failure"]
            },
            {
                "name": "TransactionManager",
                "full_name": "src.transaction_manager.TransactionManager",
                "module": "src.transaction_manager",
                "description": "Handles database transactions with batching and rollback",
                "methods_count": 6,
                "key_methods": ["begin_transaction", "commit_batch", "rollback"]
            }
        ]
        
        for cls in crawler_classes:
            query = f"""
            MERGE (c:Class {{
                name: "{cls['name']}",
                full_name: "{cls['full_name']}",
                module: "{cls['module']}",
                description: "{cls['description']}",
                methods_count: {cls['methods_count']},
                created_at: datetime()
            }});
            
            MATCH (c:Class {{full_name: "{cls['full_name']}"}}), 
                  (f:Framework {{name: "Ptolemies"}})
            MERGE (f)-[:HAS_CLASS]->(c);
            """
            
            if self.run_cypher_query(query):
                print(f"  ✅ {cls['name']}")
                
                # Add key methods
                for method_name in cls.get('key_methods', []):
                    method_query = f"""
                    MERGE (m:Method {{
                        name: "{method_name}",
                        full_name: "{cls['full_name']}.{method_name}",
                        visibility: "public",
                        created_at: datetime()
                    }});
                    
                    MATCH (c:Class {{full_name: "{cls['full_name']}"}}),
                          (m:Method {{full_name: "{cls['full_name']}.{method_name}"}})
                    MERGE (c)-[:HAS_METHOD]->(m);
                    """
                    self.run_cypher_query(method_query)
    
    def populate_integration_classes(self):
        """Populate integration classes."""
        print("\n🔌 Populating integration classes...")
        
        integrations = [
            {
                "name": "SurrealDBIntegration",
                "full_name": "src.surrealdb_integration.SurrealDBIntegration",
                "module": "src.surrealdb_integration",
                "description": "SurrealDB integration with vector storage and full-text search",
                "framework": "SurrealDB"
            },
            {
                "name": "Neo4jIntegration",
                "full_name": "src.neo4j_integration.Neo4jIntegration",
                "module": "src.neo4j_integration",
                "description": "Neo4j graph database integration for knowledge relationships",
                "framework": "Neo4j"
            },
            {
                "name": "Crawl4AIIntegration",
                "full_name": "src.crawl4ai_integration.Crawl4AIIntegration",
                "module": "src.crawl4ai_integration",
                "description": "Crawl4AI integration for advanced web scraping",
                "framework": "Crawl4AI"
            },
            {
                "name": "RedisCacheLayer",
                "full_name": "src.redis_cache_layer.RedisCacheLayer",
                "module": "src.redis_cache_layer",
                "description": "Redis caching layer for performance optimization",
                "framework": "Redis"
            }
        ]
        
        for integration in integrations:
            query = f"""
            MERGE (c:Class {{
                name: "{integration['name']}",
                full_name: "{integration['full_name']}",
                module: "{integration['module']}",
                description: "{integration['description']}",
                type: "integration",
                created_at: datetime()
            }});
            
            MATCH (c:Class {{full_name: "{integration['full_name']}"}}), 
                  (f:Framework {{name: "{integration['framework']}"}})
            MERGE (c)-[:INTEGRATES_WITH]->(f);
            """
            
            if self.run_cypher_query(query):
                print(f"  ✅ {integration['name']} → {integration['framework']}")
    
    def populate_utility_functions(self):
        """Populate utility functions."""
        print("\n🔧 Populating utility functions...")
        
        functions = [
            {
                "name": "run_surreal_query",
                "full_name": "src.production_crawler_hybrid.run_surreal_query",
                "module": "src.production_crawler_hybrid",
                "parameters": ["query: str"],
                "return_type": "bool",
                "description": "Execute SurrealDB query using CLI"
            },
            {
                "name": "generate_embedding",
                "full_name": "src.production_crawler_hybrid.ProductionCrawlerHybrid.generate_embedding",
                "module": "src.production_crawler_hybrid",
                "parameters": ["text: str"],
                "return_type": "Optional[List[float]]",
                "description": "Generate OpenAI embedding for text"
            },
            {
                "name": "calculate_quality",
                "full_name": "src.production_crawler_hybrid.ProductionCrawlerHybrid.calculate_quality",
                "module": "src.production_crawler_hybrid",
                "parameters": ["text: str", "title: str", "url: str", "source: str"],
                "return_type": "float",
                "description": "Calculate content quality score"
            },
            {
                "name": "create_chunks",
                "full_name": "src.production_crawler_hybrid.ProductionCrawlerHybrid.create_chunks",
                "module": "src.production_crawler_hybrid",
                "parameters": ["text: str", "max_size: int"],
                "return_type": "List[str]",
                "description": "Create text chunks with sentence boundaries"
            }
        ]
        
        for func in functions:
            params_str = ", ".join(func['parameters'])
            query = f"""
            MERGE (f:Function {{
                name: "{func['name']}",
                full_name: "{func['full_name']}",
                module: "{func['module']}",
                parameters: "{params_str}",
                return_type: "{func['return_type']}",
                description: "{func['description']}",
                created_at: datetime()
            }});
            """
            
            if self.run_cypher_query(query):
                print(f"  ✅ {func['name']}")
    
    def create_code_relationships(self):
        """Create relationships between code elements."""
        print("\n🔗 Creating code relationships...")
        
        relationships_query = """
        // Link classes to their modules
        MATCH (c:Class), (m:Module)
        WHERE c.module STARTS WITH m.name
        MERGE (m)-[:CONTAINS_CLASS]->(c);
        
        // Link functions to their modules
        MATCH (f:Function), (m:Module)
        WHERE f.module STARTS WITH m.name
        MERGE (m)-[:CONTAINS_FUNCTION]->(f);
        
        // Link crawler classes together
        MATCH (c1:Class), (c2:Class)
        WHERE c1.name CONTAINS "Crawler" AND c2.name CONTAINS "Crawler" 
        AND c1 <> c2
        MERGE (c1)-[:RELATED_TO {type: "crawler_family"}]->(c2);
        
        // Link integration classes to Ptolemies
        MATCH (c:Class {type: "integration"}), (p:Framework {name: "Ptolemies"})
        MERGE (p)-[:HAS_INTEGRATION]->(c);
        """
        
        if self.run_cypher_query(relationships_query):
            print("✅ Code relationships created")
    
    def verify_population(self):
        """Verify the population results."""
        print("\n🔍 Verifying code knowledge population...")
        
        verification_query = """
        MATCH (n)
        WHERE n:Module OR n:Class OR n:Method OR n:Function
        RETURN labels(n)[0] as type, count(*) as count
        ORDER BY type;
        """
        
        cmd = [
            'cypher-shell',
            '-a', self.neo4j_uri,
            '-u', self.neo4j_user,
            '-p', self.neo4j_password,
            '-d', 'neo4j',
            '--format', 'json'
        ]
        
        try:
            result = subprocess.run(
                cmd,
                input=verification_query,
                text=True,
                capture_output=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                print("\n📊 Code Knowledge Base Status:")
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    try:
                        data = json.loads(line)
                        print(f"  {data.get('type', 'Unknown')}: {data.get('count', 0)}")
                    except:
                        pass
                        
        except Exception as e:
            print(f"Verification failed: {e}")
    
    def generate_context7_prompts(self):
        """Generate prompts for context7 documentation generation."""
        print("\n💡 Context7 documentation prompts:")
        
        prompts = [
            "Use context7 to generate comprehensive documentation for ProductionCrawlerHybrid class including all methods",
            "Use context7 to document the crawl_source method with examples of crawling different documentation sites",
            "Use context7 to create usage examples for IncrementalCrawler showing update detection",
            "Use context7 to document the RecoveryManager class with failure handling scenarios",
            "Use context7 to generate API documentation for all integration classes"
        ]
        
        for i, prompt in enumerate(prompts, 1):
            print(f"{i}. {prompt}")

def main():
    """Main execution function."""
    print("🚀 Populating Neo4j with Ptolemies Code Knowledge")
    print("=" * 50)
    
    populator = CodeKnowledgePopulator()
    
    # Create schema
    populator.create_schema()
    
    # Populate data
    populator.populate_ptolemies_modules()
    populator.populate_key_classes()
    populator.populate_integration_classes()
    populator.populate_utility_functions()
    populator.create_code_relationships()
    
    # Verify results
    populator.verify_population()
    
    # Generate context7 prompts
    populator.generate_context7_prompts()
    
    print("\n✅ Code knowledge population complete!")
    print("The AI hallucination detector can now validate code against known patterns.")

if __name__ == "__main__":
    main()