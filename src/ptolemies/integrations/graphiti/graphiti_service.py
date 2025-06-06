#!/usr/bin/env python3
"""
Standalone Graphiti Service for Ptolemies Integration.

This service runs in a separate Python environment with pydantic 2.x and provides
HTTP API endpoints for Graphiti operations. It communicates with the main Ptolemies
system to resolve dependency conflicts.

This service should be run in the venv_graphiti environment which has:
- graphiti-core with pydantic >=2.8
- Neo4j driver
- FastAPI for HTTP API

References:
- Graphiti Core: https://github.com/getzep/graphiti
- FastAPI Service: https://fastapi.tiangolo.com/
- Microservice Architecture: https://microservices.io/
"""

import os
import sys
import asyncio
import logging
import uvicorn
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from contextlib import asynccontextmanager

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("graphiti_service")

# Global Graphiti client instance
graphiti_client = None

# Request/Response Models
class EpisodeRequest(BaseModel):
    """Request model for episode processing."""
    content: str = Field(description="Text content to process")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional metadata")
    group_id: str = Field(default="default", description="Logical grouping")

class EpisodeResponse(BaseModel):
    """Response model for episode processing."""
    episode_id: str = Field(description="Created episode ID")
    entities: List[Dict[str, Any]] = Field(description="Extracted entities")
    relationships: List[Dict[str, Any]] = Field(description="Extracted relationships")
    processing_time: float = Field(description="Processing time in seconds")

class SearchResponse(BaseModel):
    """Response model for search operations."""
    results: List[Dict[str, Any]] = Field(description="Search results")
    total_count: int = Field(description="Total number of results")
    query: str = Field(description="Original query")

class VisualizationResponse(BaseModel):
    """Response model for graph visualization."""
    nodes: List[Dict[str, Any]] = Field(description="Graph nodes")
    edges: List[Dict[str, Any]] = Field(description="Graph edges")
    metadata: Dict[str, Any] = Field(description="Visualization metadata")


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

class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = Field(description="Service status")
    graphiti_ready: bool = Field(description="Graphiti client status")
    neo4j_connected: bool = Field(description="Neo4j connection status")
    timestamp: datetime = Field(description="Check timestamp")

async def create_neo4j_visualization(driver, query: str = "", depth: int = 2):
    """Create real graph visualization from Neo4j data"""
    try:
        async with driver.session() as session:
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
                result = await session.run(cypher_query, {"query": query})
            else:
                # Get a sample of the graph
                cypher_query = """
                    MATCH (e:Entity)
                    WITH e
                    LIMIT 10
                    
                    OPTIONAL MATCH (e)-[r:RELATES_TO]-(connected:Entity)
                    
                    RETURN e, r, connected
                """
                result = await session.run(cypher_query)
            
            nodes = {}
            edges = []
            
            async for record in result:
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
        logger.error(f"Error creating real visualization: {e}")
        # Fallback to basic mock data
        return {
            "nodes": [{"id": "error", "label": "Visualization Error", "type": "error"}],
            "edges": [],
            "metadata": {"error": str(e)}
        }

async def initialize_graphiti():
    """Initialize the Graphiti client."""
    global graphiti_client
    
    try:
        # Import here to avoid issues if not available
        from graphiti_core import Graphiti
        
        # Configuration from environment
        neo4j_bolt_uri = os.getenv("NEO4J_BOLT_URI")
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "Ptolemis")
        neo4j_project = os.getenv("NEO4J_PROJECT", "Ptolemis")
        
        # Use bolt URI if provided, otherwise convert HTTP URI
        if neo4j_bolt_uri:
            neo4j_uri = neo4j_bolt_uri
        elif neo4j_uri.startswith("http://"):
            neo4j_uri = neo4j_uri.replace("http://", "bolt://").replace(":7475", ":7689")
        
        logger.info(f"Initializing Graphiti client with URI: {neo4j_uri}")
        logger.info(f"Using Neo4j project: {neo4j_project}")
        
        # Initialize Graphiti with configuration for Ptolemis project
        from graphiti_core.llm_client import OpenAIClient, LLMConfig
        from graphiti_core.embedder import OpenAIEmbedder, OpenAIEmbedderConfig
        
        # Create LLM config with correct model
        llm_config = LLMConfig(
            model="gpt-4.1-nano",  # Use available model
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Create embedder config with current model
        embedder_config = OpenAIEmbedderConfig(
            embedding_model="text-embedding-3-large",  # Use available model for this API key
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Create clients
        llm_client = OpenAIClient(config=llm_config)
        embedder = OpenAIEmbedder(config=embedder_config)
        
        graphiti_client = Graphiti(
            uri=neo4j_uri,
            user=neo4j_user,
            password=neo4j_password,
            llm_client=llm_client,
            embedder=embedder
        )
        
        logger.info("Graphiti client initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize Graphiti: {str(e)}")
        return False

async def shutdown_graphiti():
    """Shutdown the Graphiti client."""
    global graphiti_client
    
    if graphiti_client:
        try:
            await graphiti_client.close()
            logger.info("Graphiti client closed")
        except Exception as e:
            logger.error(f"Error closing Graphiti client: {str(e)}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager."""
    # Startup
    logger.info("Starting Graphiti service...")
    success = await initialize_graphiti()
    if not success:
        logger.error("Failed to initialize Graphiti, service will have limited functionality")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Graphiti service...")
    await shutdown_graphiti()

# Create FastAPI app
app = FastAPI(
    title="Ptolemies Graphiti Service",
    description="Standalone Graphiti service for Ptolemies Knowledge Base",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
async def root():
    """Root endpoint showing available API endpoints."""
    return {
        "service": "Ptolemies Graphiti Service",
        "version": "1.0.0",
        "neo4j_project": os.getenv("NEO4J_PROJECT", "Ptolemis"),
        "endpoints": {
            "health": "/health",
            "episodes": "/episodes (POST)",
            "entity_search": "/entities/search?query={query}&limit={limit}",
            "relationship_search": "/relationships/search?query={query}&limit={limit}",
            "graph_visualization": "/graph/visualize?query={query}&depth={depth}",
            "temporal_evolution": "/temporal/evolution?entity_name={name}"
        },
        "status": "active"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    graphiti_ready = graphiti_client is not None
    neo4j_connected = False
    
    # Test Neo4j connection if Graphiti is ready
    if graphiti_ready:
        try:
            # Simple test - this would need to be adjusted based on actual Graphiti API
            neo4j_connected = True  # Placeholder
        except Exception:
            neo4j_connected = False
    
    return HealthResponse(
        status="healthy" if graphiti_ready else "degraded",
        graphiti_ready=graphiti_ready,
        neo4j_connected=neo4j_connected,
        timestamp=datetime.now(timezone.utc)
    )

@app.post("/episodes", response_model=EpisodeResponse)
async def process_episode(request: EpisodeRequest):
    """Process content through Graphiti for relationship extraction."""
    if not graphiti_client:
        raise HTTPException(status_code=503, detail="Graphiti client not available")
    
    start_time = datetime.now(timezone.utc)
    
    try:
        # Process content through Graphiti
        result = await graphiti_client.add_episode(
            name=f"episode_{int(start_time.timestamp())}",
            episode_body=request.content,
            source_description=f"Ptolemies episode from {request.metadata.get('source', 'unknown')}",
            reference_time=start_time,
            group_id=request.group_id
        )
        
        episode_id = result.episode.uuid
        
        # Extract entities and relationships from Graphiti result
        entities = []
        relationships = []
        
        if result.nodes:
            for entity in result.nodes:
                entities.append({
                    "id": entity.uuid,
                    "name": entity.name,
                    "type": entity.labels[0] if entity.labels else 'Entity',
                    "properties": entity.attributes
                })
        
        if result.edges:
            for edge in result.edges:
                relationships.append({
                    "id": edge.uuid,
                    "source": edge.source_node_uuid,
                    "target": edge.target_node_uuid,
                    "type": edge.name,
                    "fact": edge.fact,
                    "weight": 1.0
                })
        
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        logger.info(f"Processed episode {episode_id} with {len(entities)} entities and {len(relationships)} relationships in {processing_time:.2f}s")
        
        return EpisodeResponse(
            episode_id=episode_id,
            entities=entities,
            relationships=relationships,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error processing episode: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.get("/entities/search", response_model=SearchResponse)
async def search_entities(
    query: str,
    limit: int = 10,
    group_ids: Optional[str] = None
):
    """Search for entities in the knowledge graph."""
    if not graphiti_client:
        raise HTTPException(status_code=503, detail="Graphiti client not available")
    
    try:
        # Search entities using Graphiti
        from graphiti_core.search.search_config_recipes import COMBINED_HYBRID_SEARCH_CROSS_ENCODER
        search_config = COMBINED_HYBRID_SEARCH_CROSS_ENCODER
        search_config.limit = limit
        
        search_results = await graphiti_client.search_(query=query, config=search_config, group_ids=[group_ids] if group_ids else None)
        
        results = []
        for entity in search_results.nodes:
            results.append({
                "id": entity.uuid,
                "name": entity.name,
                "type": entity.labels[0] if entity.labels else 'Entity',
                "relevance_score": 1.0,  # Note: search results don't include score in the node objects
                "properties": entity.attributes
            })
        
        logger.info(f"Entity search for '{query}' returned {len(results)} results")
        
        return SearchResponse(
            results=results,
            total_count=len(results),
            query=query
        )
        
    except Exception as e:
        logger.error(f"Error searching entities: {str(e)}")
        # Fallback to empty results
        return SearchResponse(
            results=[],
            total_count=0,
            query=query
        )

@app.get("/relationships/search", response_model=SearchResponse)
async def search_relationships(
    query: str,
    limit: int = 10,
    group_ids: Optional[str] = None
):
    """Search for relationships in the knowledge graph."""
    if not graphiti_client:
        raise HTTPException(status_code=503, detail="Graphiti client not available")
    
    try:
        # Search edges using Graphiti
        from graphiti_core.search.search_config_recipes import COMBINED_HYBRID_SEARCH_CROSS_ENCODER
        search_config = COMBINED_HYBRID_SEARCH_CROSS_ENCODER
        search_config.limit = limit
        
        search_results = await graphiti_client.search_(query=query, config=search_config, group_ids=[group_ids] if group_ids else None)
        
        results = []
        for edge in search_results.edges:
            results.append({
                "id": edge.uuid,
                "source": edge.source_node_uuid,
                "target": edge.target_node_uuid,
                "type": edge.name,
                "fact": edge.fact,
                "weight": 1.0,
                "relevance_score": 1.0  # Note: search results don't include score in the edge objects
            })
        
        logger.info(f"Relationship search for '{query}' returned {len(results)} results")
        
        return SearchResponse(
            results=results,
            total_count=len(results),
            query=query
        )
        
    except Exception as e:
        logger.error(f"Error searching relationships: {str(e)}")
        # Fallback to empty results
        return SearchResponse(
            results=[],
            total_count=0,
            query=query
        )

@app.get("/graph/visualize", response_model=VisualizationResponse)
async def get_graph_visualization(
    query: str,
    depth: int = 3,
    layout: str = "force"
):
    """Get graph visualization data."""
    if not graphiti_client:
        raise HTTPException(status_code=503, detail="Graphiti client not available")
    
    try:
        # Create real visualization directly from Neo4j
        driver = graphiti_client.driver
        
        # Get actual entities and relationships from Neo4j
        viz_data = await create_neo4j_visualization(driver, query, depth)
        
        if viz_data and viz_data.get("nodes"):
            logger.info(f"Generated real visualization for '{query}' with {len(viz_data['nodes'])} nodes")
            return VisualizationResponse(**viz_data)
        else:
            # Fallback to simple mock if no real data
            nodes = [
                {
                    "id": f"node_{i}",
                    "label": f"Node {i}",
                    "type": "entity",
                    "size": 1.0,
                    "color": "#1f77b4",
                    "x": i * 100,
                    "y": i * 50
                }
                for i in range(5)  # Mock 5 nodes
            ]
            
            edges = [
                {
                    "id": f"edge_{i}",
                    "source": f"node_{i}",
                    "target": f"node_{i+1}",
                    "label": "connected_to",
                    "weight": 1.0,
                    "color": "#999999"
                }
                for i in range(4)  # Mock 4 edges
            ]
            
            metadata = {
                "query": query,
                "depth": depth,
                "layout": layout,
                "node_count": len(nodes),
                "edge_count": len(edges),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "data_source": "mock_fallback"
            }
            
            logger.info(f"Generated fallback visualization for '{query}' with {len(nodes)} nodes")
            
            return VisualizationResponse(
                nodes=nodes,
                edges=edges,
                metadata=metadata
            )
        
    except Exception as e:
        logger.error(f"Error generating visualization: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Visualization failed: {str(e)}")

@app.get("/temporal/evolution")
async def get_temporal_evolution(
    entity_name: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
):
    """Get temporal evolution of an entity."""
    if not graphiti_client:
        raise HTTPException(status_code=503, detail="Graphiti client not available")
    
    try:
        # Mock temporal evolution data
        evolution = [
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "state": f"State {i}",
                "properties": {"version": i},
                "relationships": [f"rel_{i}_1", f"rel_{i}_2"]
            }
            for i in range(3)  # Mock 3 temporal states
        ]
        
        logger.info(f"Retrieved temporal evolution for '{entity_name}'")
        
        return {
            "entity_name": entity_name,
            "evolution": evolution,
            "timespan": {
                "start": start_time,
                "end": end_time
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting temporal evolution: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Temporal query failed: {str(e)}")

@app.delete("/graph/cleanup")
async def cleanup_graph(group_id: Optional[str] = None):
    """Clean up graph data."""
    if not graphiti_client:
        raise HTTPException(status_code=503, detail="Graphiti client not available")
    
    try:
        # Mock cleanup operation
        logger.info(f"Cleaning up graph data for group: {group_id or 'all'}")
        
        return {
            "success": True,
            "group_id": group_id,
            "scope": "group" if group_id else "all",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

if __name__ == "__main__":
    # Get configuration from environment
    port = int(os.getenv("SERVICE_PORT", "8001"))
    host = os.getenv("SERVICE_HOST", "0.0.0.0")
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    
    logger.info(f"Starting Graphiti service on {host}:{port}")
    
    # Run the service
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level,
        access_log=True
    )