"""
Ptolemies Knowledge Base MCP Server.

This module implements a Model Context Protocol (MCP) server for the Ptolemies
knowledge base, allowing Large Language Models to access and manipulate
knowledge items through standardized API endpoints.

Based on the Model Context Protocol specification for LLM tool integration.
Follows MCP server patterns for consistent API design and error handling.

The server provides the following MCP tools:
- search: Semantic search in the knowledge base using vector similarity
- retrieve: Get a specific knowledge item by ID with optional embeddings
- store: Store a new knowledge item with automatic embedding generation
- related: Find related items through SurrealDB graph relationships

Integration with Graphiti patterns:
- Temporal knowledge graph support for time-based queries
- Hybrid search combining semantic, keyword, and graph traversal
- Incremental knowledge updates for real-time learning

References:
- Model Context Protocol: https://modelcontextprotocol.io/
- MCP Server Implementation: https://github.com/modelcontextprotocol/servers
- Graphiti Integration: https://github.com/getzep/graphiti
- SurrealDB Graph Queries: https://surrealdb.com/docs/surrealql/datamodel/graph
"""

import os
import json
import uuid
import logging
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime

import httpx
from fastapi import FastAPI, HTTPException, Depends, Body, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field, validator
import uvicorn

from ..db.surrealdb_client import SurrealDBClient, ResourceNotFoundError, QueryError
from ..models.knowledge_item import (
    KnowledgeItem, 
    KnowledgeItemCreate,
    KnowledgeItemUpdate,
    Embedding,
    Relationship
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ptolemies_mcp")

# Set up API key authentication
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# MCP tool schemas
class SearchParameters(BaseModel):
    """Parameters for semantic search in the knowledge base."""
    query: str = Field(..., description="Search query text")
    limit: int = Field(10, description="Maximum number of results to return")
    threshold: float = Field(0.7, description="Minimum similarity score threshold (0.0 to 1.0)")
    filter_tags: Optional[List[str]] = Field(None, description="Optional list of tags to filter by")
    filter_content_type: Optional[str] = Field(None, description="Optional content type to filter by")
    
    @validator('threshold')
    def validate_threshold(cls, v):
        """Ensure threshold is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")
        return v
    
    @validator('limit')
    def validate_limit(cls, v):
        """Ensure limit is positive and not too large."""
        if v < 1:
            raise ValueError("Limit must be at least 1")
        if v > 100:
            raise ValueError("Limit cannot exceed 100")
        return v


class RetrieveParameters(BaseModel):
    """Parameters for retrieving a specific knowledge item."""
    item_id: str = Field(..., description="ID of the knowledge item to retrieve")
    include_embeddings: bool = Field(False, description="Whether to include embedding vectors")
    include_relationships: bool = Field(True, description="Whether to include relationships")


class StoreParameters(BaseModel):
    """Parameters for storing a new knowledge item."""
    title: str = Field(..., description="Item title")
    content: str = Field(..., description="Primary content (text)")
    content_type: str = Field("text/plain", description="Type of content (e.g., 'text/plain', 'text/markdown', 'code/python')")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Flexible metadata")
    tags: List[str] = Field(default_factory=list, description="List of tags")
    source: Optional[str] = Field(None, description="Origin of the content")
    generate_embedding: bool = Field(True, description="Whether to automatically generate an embedding")
    
    @validator('content_type')
    def validate_content_type(cls, v):
        """Ensure content_type follows the format 'category/subcategory'."""
        if '/' not in v:
            raise ValueError("Content type should follow format 'category/subcategory'")
        return v


class RelatedParameters(BaseModel):
    """Parameters for finding related knowledge items."""
    item_id: str = Field(..., description="ID of the knowledge item")
    relationship_types: Optional[List[str]] = Field(None, description="Types of relationships to include")
    direction: str = Field("both", description="Relationship direction ('outgoing', 'incoming', or 'both')")
    limit: int = Field(10, description="Maximum number of related items to return")
    
    @validator('direction')
    def validate_direction(cls, v):
        """Ensure direction is valid."""
        valid_directions = ["outgoing", "incoming", "both"]
        if v not in valid_directions:
            raise ValueError(f"Direction must be one of: {', '.join(valid_directions)}")
        return v
    
    @validator('limit')
    def validate_limit(cls, v):
        """Ensure limit is positive and not too large."""
        if v < 1:
            raise ValueError("Limit must be at least 1")
        if v > 100:
            raise ValueError("Limit cannot exceed 100")
        return v


# MCP Response models
class MCPMetadata(BaseModel):
    """Metadata for MCP responses."""
    request_id: str = Field(..., description="Unique request identifier")
    execution_time_ms: int = Field(..., description="Execution time in milliseconds")
    usage: Dict[str, Any] = Field(default_factory=dict, description="Resource usage metrics")


class MCPResultData(BaseModel):
    """Data payload for MCP responses."""
    data: Any = Field(..., description="Response data")
    format: str = Field("json", description="Format of the response data")


class MCPResult(BaseModel):
    """Standard MCP response structure."""
    result: MCPResultData
    metadata: MCPMetadata


class MCPError(BaseModel):
    """Error response for MCP."""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional error details")


class MCPErrorResponse(BaseModel):
    """Standard MCP error response structure."""
    error: MCPError
    metadata: Dict[str, Any]


class MCPRequest(BaseModel):
    """Standard MCP request structure."""
    tool: str = Field(..., description="Tool name")
    operation: str = Field(..., description="Operation name")
    parameters: Dict[str, Any] = Field(..., description="Operation parameters")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Request metadata")


# Create FastAPI app
app = FastAPI(
    title="Ptolemies Knowledge Base MCP Server",
    description="Model Context Protocol server for accessing the Ptolemies knowledge base",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Can be set to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global database client
db_client = None


async def get_db_client():
    """
    Get or create the database client.
    
    Returns:
        SurrealDBClient: Database client instance
    """
    global db_client
    if db_client is None:
        db_client = SurrealDBClient()
        await db_client.connect()
    return db_client


async def verify_api_key(api_key: str = Depends(api_key_header)):
    """
    Verify the API key.
    
    Args:
        api_key: API key from request header
        
    Raises:
        HTTPException: If API key is invalid
    """
    # Get the expected API key from environment
    expected_api_key = os.getenv("PTOLEMIES_MCP_API_KEY")
    
    # If no API key is set in environment, allow all requests (for development)
    if not expected_api_key:
        return True
    
    # Otherwise, validate the API key
    if not api_key or api_key != expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    
    return True


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """
    Add a unique request ID to each request.
    
    Args:
        request: FastAPI request object
        call_next: Next middleware function
        
    Returns:
        Response: FastAPI response
    """
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Record start time for execution time calculation
    start_time = datetime.now()
    
    # Process the request
    response = await call_next(request)
    
    # Calculate execution time
    execution_time = (datetime.now() - start_time).total_seconds() * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Execution-Time"] = str(int(execution_time))
    
    return response


@app.on_event("startup")
async def startup_event():
    """
    Initialize services on application startup.
    """
    logger.info("Starting Ptolemies MCP server")
    # Initialize database client
    await get_db_client()


@app.on_event("shutdown")
async def shutdown_event():
    """
    Clean up resources on application shutdown.
    """
    logger.info("Shutting down Ptolemies MCP server")
    # Close database connection
    global db_client
    if db_client:
        await db_client.disconnect()


@app.get("/v1/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        dict: Health status
    """
    try:
        # Check database connection
        db = await get_db_client()
        
        return {
            "status": "healthy",
            "services": {
                "database": "connected",
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "services": {
                    "database": "disconnected",
                },
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )


@app.get("/v1/schema", tags=["Schema"])
async def get_schema():
    """
    Get the OpenAPI schema.
    
    Returns:
        dict: OpenAPI schema
    """
    return app.openapi()


@app.post("/v1/tools/{tool_name}/describe", tags=["Tools"])
async def describe_tool(
    tool_name: str,
    _: bool = Depends(verify_api_key),
):
    """
    Get the schema for a specific tool.
    
    Args:
        tool_name: Name of the tool
        
    Returns:
        dict: Tool schema
    """
    # Map tool names to their parameter schemas
    tool_schemas = {
        "search": SearchParameters.schema(),
        "retrieve": RetrieveParameters.schema(),
        "store": StoreParameters.schema(),
        "related": RelatedParameters.schema(),
    }
    
    if tool_name not in tool_schemas:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": {
                    "code": "tool_not_found",
                    "message": f"Tool '{tool_name}' not found",
                    "details": {
                        "available_tools": list(tool_schemas.keys())
                    }
                },
                "metadata": {
                    "request_id": uuid.uuid4()
                }
            }
        )
    
    return {
        "name": tool_name,
        "schema": tool_schemas[tool_name],
        "metadata": {
            "version": "1.0.0",
            "description": f"Ptolemies Knowledge Base {tool_name} tool"
        }
    }


@app.post("/v1/tools/{tool_name}/invoke", tags=["Tools"])
async def invoke_tool(
    request: Request,
    tool_name: str,
    mcp_request: MCPRequest = Body(...),
    _: bool = Depends(verify_api_key),
    db: SurrealDBClient = Depends(get_db_client),
):
    """
    Invoke a tool with the given parameters.
    
    Args:
        request: FastAPI request object
        tool_name: Name of the tool
        mcp_request: MCP request
        db: Database client
        
    Returns:
        MCPResult: Tool result
    """
    request_id = request.state.request_id
    start_time = datetime.now()
    
    # Validate tool name
    if tool_name != mcp_request.tool:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": "tool_mismatch",
                    "message": f"Tool name in URL '{tool_name}' does not match tool in request body '{mcp_request.tool}'",
                    "details": {}
                },
                "metadata": {
                    "request_id": request_id
                }
            }
        )
    
    # Dispatch to appropriate tool handler
    try:
        result = None
        
        if tool_name == "search":
            # Validate parameters
            params = SearchParameters(**mcp_request.parameters)
            result = await handle_search(db, params)
        
        elif tool_name == "retrieve":
            # Validate parameters
            params = RetrieveParameters(**mcp_request.parameters)
            result = await handle_retrieve(db, params)
        
        elif tool_name == "store":
            # Validate parameters
            params = StoreParameters(**mcp_request.parameters)
            result = await handle_store(db, params)
        
        elif tool_name == "related":
            # Validate parameters
            params = RelatedParameters(**mcp_request.parameters)
            result = await handle_related(db, params)
        
        else:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "error": {
                        "code": "tool_not_found",
                        "message": f"Tool '{tool_name}' not found",
                        "details": {
                            "available_tools": ["search", "retrieve", "store", "related"]
                        }
                    },
                    "metadata": {
                        "request_id": request_id
                    }
                }
            )
        
        # Calculate execution time
        execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Build response
        response = MCPResult(
            result=MCPResultData(
                data=result,
                format="json"
            ),
            metadata=MCPMetadata(
                request_id=request_id,
                execution_time_ms=execution_time,
                usage={
                    "compute_units": 1  # Placeholder for actual compute units
                }
            )
        )
        
        return response
    
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Invalid parameters",
                    "details": {
                        "errors": e.errors()
                    }
                },
                "metadata": {
                    "request_id": request_id
                }
            }
        )
    
    except ResourceNotFoundError as e:
        logger.error(f"Resource not found: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": {
                    "code": "resource_not_found",
                    "message": str(e),
                    "details": {}
                },
                "metadata": {
                    "request_id": request_id
                }
            }
        )
    
    except QueryError as e:
        logger.error(f"Query error: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "query_error",
                    "message": str(e),
                    "details": {}
                },
                "metadata": {
                    "request_id": request_id
                }
            }
        )
    
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "internal_server_error",
                    "message": "An unexpected error occurred",
                    "details": {
                        "error": str(e)
                    }
                },
                "metadata": {
                    "request_id": request_id
                }
            }
        )


# Tool implementation handlers

async def get_embedding_for_text(text: str) -> List[float]:
    """
    Generate an embedding vector for the given text.
    
    Args:
        text: Text to generate embedding for
        
    Returns:
        List[float]: Embedding vector
    """
    # For demonstration purposes, return a simple mock embedding
    # In a real implementation, this would call an embedding service
    import hashlib
    import struct
    
    # Generate a deterministic pseudo-embedding based on the text hash
    # This is just for demonstration - use a real embedding service in production
    hash_obj = hashlib.sha256(text.encode())
    hash_bytes = hash_obj.digest()
    
    # Create a 384-dimensional embedding from the hash
    # Again, this is just for demonstration
    embedding = []
    for i in range(0, 48, 4):  # 48 bytes (hash) / 4 bytes (float) = 12 values
        val = struct.unpack('f', hash_bytes[i % 32:i % 32 + 4])[0]
        embedding.append(val)
    
    # Repeat the values to get to 384 dimensions
    embedding = embedding * 32
    embedding = embedding[:384]
    
    return embedding


async def handle_search(db: SurrealDBClient, params: SearchParameters):
    """
    Handle semantic search in the knowledge base.
    
    Args:
        db: Database client
        params: Search parameters
        
    Returns:
        dict: Search results
    """
    logger.info(f"Performing semantic search for query: {params.query}")
    
    # Generate query embedding
    query_vector = await get_embedding_for_text(params.query)
    
    # Perform semantic search
    search_results = await db.semantic_search(
        query_vector=query_vector,
        limit=params.limit,
        threshold=params.threshold,
        filter_tags=params.filter_tags,
        filter_content_type=params.filter_content_type,
    )
    
    # Format results
    formatted_results = []
    for item, score in search_results:
        # Convert Pydantic model to dict and add score
        item_dict = item.dict()
        item_dict["score"] = score
        formatted_results.append(item_dict)
    
    return {
        "query": params.query,
        "results": formatted_results,
        "total": len(formatted_results),
        "filters": {
            "tags": params.filter_tags,
            "content_type": params.filter_content_type,
        }
    }


async def handle_retrieve(db: SurrealDBClient, params: RetrieveParameters):
    """
    Handle retrieval of a specific knowledge item.
    
    Args:
        db: Database client
        params: Retrieve parameters
        
    Returns:
        dict: Retrieved item
    """
    logger.info(f"Retrieving knowledge item: {params.item_id}")
    
    # Get the knowledge item
    item = await db.get_knowledge_item(params.item_id)
    item_dict = item.dict()
    
    # If requested, include embedding
    if params.include_embeddings and item.embedding_id:
        try:
            embedding = await db.get_item_embedding(params.item_id)
            if embedding:
                item_dict["embedding"] = embedding.dict()
        except Exception as e:
            logger.warning(f"Failed to retrieve embedding for item {params.item_id}: {str(e)}")
    
    # If requested, include relationships
    if params.include_relationships:
        try:
            relationships = await db.get_item_relationships(params.item_id, direction="both")
            item_dict["relationships"] = [rel.dict() for rel in relationships]
        except Exception as e:
            logger.warning(f"Failed to retrieve relationships for item {params.item_id}: {str(e)}")
    
    return item_dict


async def handle_store(db: SurrealDBClient, params: StoreParameters):
    """
    Handle storage of a new knowledge item.
    
    Args:
        db: Database client
        params: Store parameters
        
    Returns:
        dict: Created item
    """
    logger.info(f"Storing new knowledge item: {params.title}")
    
    # Create the knowledge item
    item_create = KnowledgeItemCreate(
        title=params.title,
        content=params.content,
        content_type=params.content_type,
        metadata=params.metadata,
        tags=params.tags,
        source=params.source,
    )
    
    item = await db.create_knowledge_item(item_create)
    item_dict = item.dict()
    
    # If requested, generate and store embedding
    if params.generate_embedding:
        try:
            # Generate embedding vector
            vector = await get_embedding_for_text(params.content)
            
            # Create embedding object
            embedding = Embedding(
                vector=vector,
                model="text-embedding-mock",  # Replace with actual model in production
                dimensions=len(vector),
            )
            
            # Store embedding and associate with item
            created_embedding = await db.create_embedding(embedding, item.id)
            item_dict["embedding_id"] = created_embedding.id
            
            # Update the item with the new embedding ID
            # (This is technically redundant since create_embedding already updates the item,
            # but we include it for clarity and to ensure the response has the correct embedding_id)
            item_update = KnowledgeItemUpdate(embedding_id=created_embedding.id)
            updated_item = await db.update_knowledge_item(item.id, item_update)
            item_dict = updated_item.dict()
        
        except Exception as e:
            logger.warning(f"Failed to generate embedding for item {item.id}: {str(e)}")
    
    return {
        "item": item_dict,
        "message": "Knowledge item created successfully"
    }


async def handle_related(db: SurrealDBClient, params: RelatedParameters):
    """
    Handle finding related knowledge items.
    
    Args:
        db: Database client
        params: Related parameters
        
    Returns:
        dict: Related items
    """
    logger.info(f"Finding related items for: {params.item_id}")
    
    # Get the knowledge item to verify it exists
    item = await db.get_knowledge_item(params.item_id)
    
    # Get relationships
    relationships = await db.get_item_relationships(
        params.item_id, 
        direction=params.direction
    )
    
    # Filter by relationship types if specified
    if params.relationship_types:
        relationships = [
            rel for rel in relationships 
            if rel.type in params.relationship_types
        ]
    
    # Limit the number of relationships
    relationships = relationships[:params.limit]
    
    # Get the related items
    related_items = []
    for rel in relationships:
        # Determine which ID refers to the related item
        related_id = rel.target_id if rel.source_id == params.item_id else rel.source_id
        
        try:
            related_item = await db.get_knowledge_item(related_id)
            
            # Add relationship information
            related_item_dict = related_item.dict()
            related_item_dict["relationship"] = {
                "type": rel.type,
                "weight": rel.weight,
                "direction": "outgoing" if rel.source_id == params.item_id else "incoming",
                "metadata": rel.metadata,
            }
            
            related_items.append(related_item_dict)
        
        except ResourceNotFoundError:
            logger.warning(f"Related item {related_id} not found")
            continue
        
        except Exception as e:
            logger.warning(f"Error retrieving related item {related_id}: {str(e)}")
            continue
    
    return {
        "item_id": params.item_id,
        "direction": params.direction,
        "relationship_types": params.relationship_types,
        "related_items": related_items,
        "total": len(related_items),
    }


def run_server(host="0.0.0.0", port=8080):
    """
    Run the MCP server.
    
    Args:
        host: Host to bind to
        port: Port to listen on
    """
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    # Set default host and port
    host = os.getenv("PTOLEMIES_MCP_HOST", "0.0.0.0")
    port = int(os.getenv("PTOLEMIES_MCP_PORT", "8080"))
    
    # Run the server
    run_server(host=host, port=port)