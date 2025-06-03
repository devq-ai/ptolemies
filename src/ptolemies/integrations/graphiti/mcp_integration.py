"""
MCP integration for Graphiti-enhanced Ptolemies Knowledge Base.

This module extends the Ptolemies MCP server with Graphiti's temporal knowledge
graph capabilities, providing enhanced relationship discovery and temporal reasoning.

Follows MCP specification patterns for consistent tool interfaces:
- Standardized parameter schemas
- Proper error handling and response formatting
- Async operation support for real-time interaction

References:
- Model Context Protocol: https://modelcontextprotocol.io/
- Graphiti MCP Server: https://github.com/getzep/graphiti#mcp-server
- Ptolemies MCP Architecture: ../mcp/ptolemies_mcp.py
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator

from .client import GraphitiIntegrationClient, GraphitiConfig
from ...db.surrealdb_client import SurrealDBClient
from ...models.knowledge_item import KnowledgeItem

# Configure logging
logger = logging.getLogger(__name__)

class GraphitiSearchParameters(BaseModel):
    """Parameters for Graphiti-enhanced search operations."""
    query: str = Field(..., description="Search query text")
    search_type: str = Field(
        default="hybrid",
        description="Type of search: 'entities', 'relationships', 'hybrid', or 'temporal'"
    )
    limit: int = Field(10, description="Maximum number of results to return")
    group_ids: Optional[List[str]] = Field(None, description="Optional group filtering")
    include_documents: bool = Field(True, description="Include SurrealDB document search")
    include_relationships: bool = Field(True, description="Include Graphiti relationship search")
    start_time: Optional[datetime] = Field(None, description="Start time for temporal queries")
    end_time: Optional[datetime] = Field(None, description="End time for temporal queries")
    
    @validator('search_type')
    def validate_search_type(cls, v):
        """Validate search type parameter."""
        valid_types = ['entities', 'relationships', 'hybrid', 'temporal']
        if v not in valid_types:
            raise ValueError(f"Search type must be one of: {valid_types}")
        return v

class ProcessKnowledgeParameters(BaseModel):
    """Parameters for processing knowledge items through Graphiti."""
    knowledge_item_id: str = Field(..., description="ID of the knowledge item to process")
    group_id: Optional[str] = Field(None, description="Optional logical grouping")
    extract_entities: bool = Field(True, description="Extract entities and relationships")
    update_graph: bool = Field(True, description="Update the temporal knowledge graph")

class TemporalEvolutionParameters(BaseModel):
    """Parameters for temporal evolution queries."""
    entity_name: str = Field(..., description="Name of the entity to track")
    start_time: Optional[datetime] = Field(None, description="Start time for evolution")
    end_time: Optional[datetime] = Field(None, description="End time for evolution")
    include_relationships: bool = Field(True, description="Include relationship changes")

class GraphiteCleanupParameters(BaseModel):
    """Parameters for graph cleanup operations."""
    group_id: Optional[str] = Field(None, description="Optional group to clean up")
    confirm: bool = Field(False, description="Confirmation required for cleanup")
    
    @validator('confirm')
    def validate_confirm(cls, v):
        """Require explicit confirmation for cleanup operations."""
        if not v:
            raise ValueError("Cleanup operations require explicit confirmation")
        return v

class GraphitiMCPIntegration:
    """
    MCP integration layer for Graphiti-enhanced Ptolemies Knowledge Base.
    
    Provides MCP tools for:
    - Enhanced search with temporal reasoning
    - Knowledge item processing through Graphiti
    - Temporal evolution tracking
    - Graph management and cleanup
    """
    
    def __init__(
        self,
        surrealdb_client: SurrealDBClient,
        graphiti_config: Optional[GraphitiConfig] = None
    ):
        """
        Initialize the Graphiti MCP integration.
        
        Args:
            surrealdb_client: SurrealDB client for hybrid operations
            graphiti_config: Optional Graphiti configuration
        """
        self.surrealdb_client = surrealdb_client
        self.graphiti_client = GraphitiIntegrationClient(
            config=graphiti_config,
            surrealdb_client=surrealdb_client
        )
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the Graphiti integration."""
        try:
            await self.graphiti_client.initialize()
            self._initialized = True
            logger.info("Graphiti MCP integration initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Graphiti MCP integration: {str(e)}")
            raise
    
    async def close(self) -> None:
        """Close the Graphiti integration."""
        if self._initialized:
            await self.graphiti_client.close()
            self._initialized = False
            logger.info("Graphiti MCP integration closed")
    
    async def _ensure_initialized(self) -> None:
        """Ensure the integration is initialized."""
        if not self._initialized:
            await self.initialize()
    
    # MCP Tool Implementations
    
    async def enhanced_search(self, params: GraphitiSearchParameters) -> Dict[str, Any]:
        """
        Enhanced search tool with Graphiti temporal reasoning.
        
        MCP Tool: enhanced_search
        Description: Search knowledge base with temporal graph capabilities
        
        Args:
            params: Search parameters including query, type, and filters
            
        Returns:
            Enhanced search results with temporal context
        """
        await self._ensure_initialized()
        
        try:
            if params.search_type == "entities":
                results = await self.graphiti_client.search_entities(
                    query=params.query,
                    limit=params.limit,
                    group_ids=params.group_ids
                )
                return {
                    "type": "entities",
                    "query": params.query,
                    "results": results,
                    "count": len(results)
                }
            
            elif params.search_type == "relationships":
                results = await self.graphiti_client.search_relationships(
                    query=params.query,
                    limit=params.limit,
                    group_ids=params.group_ids
                )
                return {
                    "type": "relationships", 
                    "query": params.query,
                    "results": results,
                    "count": len(results)
                }
            
            elif params.search_type == "hybrid":
                results = await self.graphiti_client.hybrid_search(
                    query=params.query,
                    limit=params.limit,
                    include_documents=params.include_documents,
                    include_relationships=params.include_relationships
                )
                return {
                    "type": "hybrid",
                    "query": params.query,
                    "results": results,
                    "relevance_score": results.get("combined_score", 0.0)
                }
            
            elif params.search_type == "temporal":
                # Temporal search requires entity name extraction from query
                # This is a simplified implementation
                results = await self.graphiti_client.get_temporal_evolution(
                    entity_name=params.query,  # Simplified - would need NER in practice
                    start_time=params.start_time,
                    end_time=params.end_time
                )
                return {
                    "type": "temporal",
                    "entity": params.query,
                    "results": results,
                    "timespan": {
                        "start": params.start_time.isoformat() if params.start_time else None,
                        "end": params.end_time.isoformat() if params.end_time else None
                    }
                }
            
            else:
                raise ValueError(f"Unsupported search type: {params.search_type}")
                
        except Exception as e:
            logger.error(f"Enhanced search failed: {str(e)}")
            return {
                "error": str(e),
                "query": params.query,
                "type": params.search_type
            }
    
    async def process_knowledge_item(self, params: ProcessKnowledgeParameters) -> Dict[str, Any]:
        """
        Process knowledge item through Graphiti for relationship extraction.
        
        MCP Tool: process_knowledge_item
        Description: Analyze knowledge item for temporal relationships
        
        Args:
            params: Processing parameters
            
        Returns:
            Processing results with extracted relationships
        """
        await self._ensure_initialized()
        
        try:
            # Retrieve knowledge item from SurrealDB
            knowledge_item = await self.surrealdb_client.get_knowledge_item(
                params.knowledge_item_id
            )
            
            # Process through Graphiti
            if params.extract_entities:
                result = await self.graphiti_client.process_knowledge_item(
                    knowledge_item=knowledge_item,
                    group_id=params.group_id
                )
                
                return {
                    "knowledge_item_id": params.knowledge_item_id,
                    "processing_result": result.dict(),
                    "entities_extracted": len(result.entities),
                    "relationships_extracted": len(result.relationships),
                    "processing_time": result.processing_time
                }
            else:
                return {
                    "knowledge_item_id": params.knowledge_item_id,
                    "message": "Entity extraction skipped",
                    "processing_time": 0.0
                }
                
        except Exception as e:
            logger.error(f"Knowledge item processing failed: {str(e)}")
            return {
                "error": str(e),
                "knowledge_item_id": params.knowledge_item_id
            }
    
    async def get_temporal_evolution(self, params: TemporalEvolutionParameters) -> Dict[str, Any]:
        """
        Get temporal evolution of an entity.
        
        MCP Tool: get_temporal_evolution  
        Description: Track how entity relationships changed over time
        
        Args:
            params: Temporal evolution parameters
            
        Returns:
            Temporal evolution data with validity periods
        """
        await self._ensure_initialized()
        
        try:
            evolution = await self.graphiti_client.get_temporal_evolution(
                entity_name=params.entity_name,
                start_time=params.start_time,
                end_time=params.end_time
            )
            
            return {
                "entity_name": params.entity_name,
                "evolution": evolution,
                "timespan": {
                    "start": params.start_time.isoformat() if params.start_time else None,
                    "end": params.end_time.isoformat() if params.end_time else None
                },
                "states_count": len(evolution)
            }
            
        except Exception as e:
            logger.error(f"Temporal evolution query failed: {str(e)}")
            return {
                "error": str(e),
                "entity_name": params.entity_name
            }
    
    async def cleanup_graph(self, params: GraphiteCleanupParameters) -> Dict[str, Any]:
        """
        Clean up the temporal knowledge graph.
        
        MCP Tool: cleanup_graph
        Description: Clean up graph data, optionally scoped to a group
        
        Args:
            params: Cleanup parameters with confirmation
            
        Returns:
            Cleanup operation results
        """
        await self._ensure_initialized()
        
        try:
            success = await self.graphiti_client.cleanup_graph(
                group_id=params.group_id
            )
            
            return {
                "success": success,
                "group_id": params.group_id,
                "scope": "group" if params.group_id else "all",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Graph cleanup failed: {str(e)}")
            return {
                "error": str(e),
                "success": False,
                "group_id": params.group_id
            }
    
    # MCP Tool Registry
    
    def get_mcp_tools(self) -> List[Dict[str, Any]]:
        """
        Get the MCP tool definitions for Graphiti integration.
        
        Returns:
            List of MCP tool definitions
        """
        return [
            {
                "name": "enhanced_search",
                "description": "Search knowledge base with Graphiti temporal reasoning",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query text"},
                        "search_type": {
                            "type": "string",
                            "enum": ["entities", "relationships", "hybrid", "temporal"],
                            "default": "hybrid",
                            "description": "Type of search to perform"
                        },
                        "limit": {"type": "integer", "default": 10, "description": "Maximum results"},
                        "group_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional group filtering"
                        },
                        "include_documents": {"type": "boolean", "default": True},
                        "include_relationships": {"type": "boolean", "default": True}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "process_knowledge_item",
                "description": "Process knowledge item through Graphiti for relationship extraction",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "knowledge_item_id": {"type": "string", "description": "Knowledge item ID"},
                        "group_id": {"type": "string", "description": "Optional logical grouping"},
                        "extract_entities": {"type": "boolean", "default": True},
                        "update_graph": {"type": "boolean", "default": True}
                    },
                    "required": ["knowledge_item_id"]
                }
            },
            {
                "name": "get_temporal_evolution",
                "description": "Track temporal evolution of an entity",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_name": {"type": "string", "description": "Entity name to track"},
                        "start_time": {"type": "string", "format": "date-time"},
                        "end_time": {"type": "string", "format": "date-time"},
                        "include_relationships": {"type": "boolean", "default": True}
                    },
                    "required": ["entity_name"]
                }
            },
            {
                "name": "cleanup_graph",
                "description": "Clean up temporal knowledge graph",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "group_id": {"type": "string", "description": "Optional group to clean"},
                        "confirm": {"type": "boolean", "description": "Required confirmation"}
                    },
                    "required": ["confirm"]
                }
            }
        ]