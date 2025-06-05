#!/usr/bin/env python3
"""
Knowledge Board Web Server

Creates the web interface for viewing the temporal knowledge graph on localhost:8000.
This implements requirement #4: "View the knowledge board on localhost:8000"

Serves:
- Interactive knowledge graph visualization
- Temporal evolution views
- Entity and relationship exploration
- Search interface
"""

import os
import sys
import logging
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Logfire if available
logfire_initialized = False
try:
    import logfire
    
    # Initialize Logfire if token is available
    logfire_token = os.getenv("LOGFIRE_TOKEN")
    if logfire_token:
        logfire.configure(
            token=logfire_token,
            service_name=os.getenv("LOGFIRE_SERVICE_NAME", "ptolemies-knowledge-board"),
            environment=os.getenv("LOGFIRE_ENVIRONMENT", "development")
        )
        logfire_initialized = True
        logging.info("Logfire initialized successfully")
    else:
        logging.info("Logfire token not found, running without Logfire")
except ImportError:
    logging.info("Logfire not installed, running without observability")
    logfire = None

# Add project paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("knowledge_board")

# Log initialization status
if logfire_initialized:
    logger.info("Knowledge Board server starting with Logfire observability")
else:
    logger.info("Knowledge Board server starting without Logfire")

# Configuration
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "Ptolemis"
GRAPHITI_API_URL = "http://localhost:8001"

app = FastAPI(
    title="Ptolemies Knowledge Board",
    description="Temporal Knowledge Graph Visualization Dashboard",
    version="1.0.0"
)

# Create static and templates directories
STATIC_DIR = Path(__file__).parent / "static"
TEMPLATES_DIR = Path(__file__).parent / "templates"

STATIC_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Instrument FastAPI with Logfire if available
if logfire and logfire_initialized:
    logfire.instrument_fastapi(app)
    logger.info("FastAPI instrumented with Logfire")

class Neo4jClient:
    """Neo4j client for querying graph data"""
    
    def __init__(self):
        self.driver = None
        self._initialize_driver()
    
    def _initialize_driver(self):
        """Initialize Neo4j driver"""
        try:
            from neo4j import GraphDatabase
            self.driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USER, NEO4J_PASSWORD)
            )
            logger.info("Neo4j driver initialized successfully")
        except ImportError:
            logger.error("Neo4j driver not installed. Install with: pip install neo4j")
            self.driver = None
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j driver: {str(e)}")
            self.driver = None
    
    def test_connection(self) -> bool:
        """Test Neo4j connection"""
        if not self.driver:
            return False
        
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                return result.single()["test"] == 1
        except Exception as e:
            logger.error(f"Neo4j connection test failed: {str(e)}")
            if logfire:
                logfire.error("Neo4j connection test failed", error=str(e))
            return False
    
    def get_graph_stats(self) -> Dict[str, int]:
        """Get basic graph statistics"""
        if not self.driver:
            return {"entities": 0, "relationships": 0, "episodes": 0}
        
        try:
            with self.driver.session() as session:
                # Count entities
                entities = session.run("MATCH (n:Entity) RETURN count(n) as count").single()["count"]
                
                # Count relationships
                relationships = session.run("MATCH ()-[r:RELATES_TO]->() RETURN count(r) as count").single()["count"]
                
                # Count episodes
                episodes = session.run("MATCH (e:Episodic) RETURN count(e) as count").single()["count"]
                
                return {
                    "entities": entities,
                    "relationships": relationships,
                    "episodes": episodes
                }
        except Exception as e:
            logger.error(f"Error getting graph stats: {str(e)}")
            return {"entities": 0, "relationships": 0, "episodes": 0}
    
    def get_entities(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get entities for visualization"""
        if not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                query = """
                MATCH (n:Entity)
                RETURN n.uuid as id, n.name as name, labels(n) as labels,
                       n.created_at as created_at, n.group_id as group_id,
                       n.summary as summary
                LIMIT $limit
                """
                
                result = session.run(query, limit=limit)
                entities = []
                
                for record in result:
                    entities.append({
                        "id": record["id"],
                        "name": record["name"],
                        "labels": record["labels"],
                        "group_id": record["group_id"],
                        "summary": record["summary"],
                        "created_at": record["created_at"]
                    })
                
                return entities
        except Exception as e:
            logger.error(f"Error getting entities: {str(e)}")
            return []
    
    def get_relationships(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get relationships for visualization"""
        if not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                query = """
                MATCH (source:Entity)-[r:RELATES_TO]->(target:Entity)
                RETURN r.uuid as id, source.uuid as source, target.uuid as target,
                       r.name as type, r.fact as fact, r.created_at as created_at,
                       r.group_id as group_id
                LIMIT $limit
                """
                
                result = session.run(query, limit=limit)
                relationships = []
                
                for record in result:
                    relationships.append({
                        "id": record["id"],
                        "source": record["source"],
                        "target": record["target"],
                        "type": record["type"],
                        "fact": record["fact"],
                        "group_id": record["group_id"],
                        "created_at": record["created_at"]
                    })
                
                return relationships
        except Exception as e:
            logger.error(f"Error getting relationships: {str(e)}")
            return []
    
    def search_entities(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search entities by name"""
        if not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                cypher_query = """
                MATCH (n:Entity)
                WHERE toLower(n.name) CONTAINS toLower($search_query)
                   OR toLower(n.summary) CONTAINS toLower($search_query)
                RETURN n.uuid as id, n.name as name, n.summary as summary,
                       n.group_id as group_id, n.created_at as created_at
                ORDER BY n.name
                LIMIT $limit
                """
                
                result = session.run(cypher_query, search_query=query, limit=limit)
                entities = []
                
                for record in result:
                    entities.append({
                        "id": record["id"],
                        "name": record["name"],
                        "summary": record["summary"],
                        "group_id": record["group_id"],
                        "created_at": record["created_at"]
                    })
                
                return entities
        except Exception as e:
            logger.error(f"Error searching entities: {str(e)}")
            return []
    
    def get_entity_neighbors(self, entity_id: str, depth: int = 2) -> Dict[str, Any]:
        """Get entity and its connected neighbors"""
        if not self.driver:
            return {"nodes": [], "edges": []}
        
        try:
            with self.driver.session() as session:
                # Build dynamic query since Neo4j doesn't allow parameters in path patterns
                query = f"""
                MATCH path = (center:Entity {{uuid: $entity_id}})-[:RELATES_TO*1..{depth}]-(connected:Entity)
                WITH nodes(path) as path_nodes, relationships(path) as path_rels
                UNWIND path_nodes as node
                WITH DISTINCT node, path_rels
                UNWIND path_rels as rel
                RETURN DISTINCT 
                       node.uuid as node_id, node.name as node_name, node.group_id as node_group,
                       rel.uuid as rel_id, startNode(rel).uuid as rel_source, 
                       endNode(rel).uuid as rel_target, rel.name as rel_type, rel.fact as rel_fact
                """
                
                result = session.run(query, entity_id=entity_id)
                
                nodes = {}
                edges = []
                
                for record in result:
                    # Add nodes
                    node_id = record["node_id"]
                    if node_id not in nodes:
                        nodes[node_id] = {
                            "id": node_id,
                            "name": record["node_name"],
                            "group": record["node_group"]
                        }
                    
                    # Add edges
                    if record["rel_id"]:
                        edges.append({
                            "id": record["rel_id"],
                            "source": record["rel_source"],
                            "target": record["rel_target"],
                            "type": record["rel_type"],
                            "fact": record["rel_fact"]
                        })
                
                return {
                    "nodes": list(nodes.values()),
                    "edges": edges
                }
        except Exception as e:
            logger.error(f"Error getting entity neighbors: {str(e)}")
            return {"nodes": [], "edges": []}

# Initialize Neo4j client
neo4j_client = Neo4jClient()

@app.get("/", response_class=HTMLResponse)
async def knowledge_board(request: Request):
    """Main knowledge board page"""
    if logfire:
        logfire.info("Knowledge board main page accessed")
    
    stats = neo4j_client.get_graph_stats()
    
    context = {
        "request": request,
        "title": "Ptolemies Knowledge Board",
        "stats": stats,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    }
    
    return templates.TemplateResponse("index.html", context)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if logfire:
        logfire.info("Health check requested")
    
    neo4j_healthy = neo4j_client.test_connection()
    
    return {
        "status": "healthy" if neo4j_healthy else "degraded",
        "neo4j_connected": neo4j_healthy,
        "logfire": "enabled" if logfire_initialized else "disabled",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/graph/stats")
async def get_graph_stats():
    """Get graph statistics"""
    return neo4j_client.get_graph_stats()

@app.get("/api/graph/data")
async def get_graph_data(limit: int = Query(100, description="Maximum number of nodes to return")):
    """Get graph data for visualization"""
    entities = neo4j_client.get_entities(limit=limit)
    relationships = neo4j_client.get_relationships(limit=limit)
    
    # Format for visualization
    nodes = []
    for entity in entities:
        nodes.append({
            "id": entity["id"],
            "label": entity["name"],
            "group": entity.get("group_id", "default"),
            "title": entity.get("summary", entity["name"]),
            "size": 20
        })
    
    edges = []
    for rel in relationships:
        edges.append({
            "id": rel["id"],
            "from": rel["source"],
            "to": rel["target"],
            "label": rel["type"],
            "title": rel.get("fact", rel["type"]),
            "arrows": "to"
        })
    
    return {
        "nodes": nodes,
        "edges": edges,
        "stats": neo4j_client.get_graph_stats()
    }

@app.get("/api/search/entities")
async def search_entities(
    q: str = Query(..., description="Search query"),
    limit: int = Query(20, description="Maximum results")
):
    """Search entities"""
    if logfire:
        with logfire.span("entity_search", query=q, limit=limit):
            results = neo4j_client.search_entities(q, limit=limit)
            logfire.info("Entity search completed", 
                        query=q, 
                        result_count=len(results))
    else:
        results = neo4j_client.search_entities(q, limit=limit)
    
    return {
        "query": q,
        "results": results,
        "total_count": len(results)
    }

@app.get("/api/entity/{entity_id}/neighbors")
async def get_entity_neighbors(
    entity_id: str,
    depth: int = Query(2, description="Depth of neighbor search")
):
    """Get entity and its connected neighbors"""
    if logfire:
        with logfire.span("get_entity_neighbors", entity_id=entity_id, depth=depth):
            result = neo4j_client.get_entity_neighbors(entity_id, depth=depth)
            logfire.info("Entity neighbors retrieved",
                        entity_id=entity_id,
                        node_count=len(result.get("nodes", [])),
                        edge_count=len(result.get("edges", [])))
            return result
    else:
        return neo4j_client.get_entity_neighbors(entity_id, depth=depth)

@app.get("/api/temporal/timeline")
async def get_temporal_timeline():
    """Get temporal timeline of knowledge creation"""
    if not neo4j_client.driver:
        return {"timeline": []}
    
    try:
        with neo4j_client.driver.session() as session:
            query = """
            MATCH (e:Episodic)
            RETURN e.created_at as timestamp, e.name as episode_name,
                   e.group_id as group_id
            ORDER BY e.created_at ASC
            """
            
            result = session.run(query)
            timeline = []
            
            for record in result:
                timeline.append({
                    "timestamp": record["timestamp"],
                    "episode": record["episode_name"],
                    "group": record["group_id"]
                })
            
            return {"timeline": timeline}
    except Exception as e:
        logger.error(f"Error getting timeline: {str(e)}")
        return {"timeline": []}

if __name__ == "__main__":
    port = int(os.getenv("KNOWLEDGE_BOARD_PORT", "8000"))
    host = os.getenv("KNOWLEDGE_BOARD_HOST", "localhost")
    
    logger.info(f"Starting Knowledge Board on {host}:{port}")
    
    # Test Neo4j connection
    if neo4j_client.test_connection():
        logger.info("✅ Neo4j connection successful")
    else:
        logger.warning("⚠️ Neo4j connection failed - some features may not work")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )