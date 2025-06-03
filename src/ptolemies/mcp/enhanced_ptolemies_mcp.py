#!/usr/bin/env python3
"""
Enhanced Ptolemies MCP Server with Graphiti Integration

This MCP server provides advanced knowledge base capabilities by combining:
- SurrealDB document storage and search
- Graphiti temporal knowledge graph reasoning
- Hybrid search across both systems
- Graph visualization and exploration
- Temporal relationship evolution tracking

MCP Tools Available:
- search_knowledge: Hybrid search across documents and knowledge graph
- store_knowledge: Store new knowledge with automatic relationship extraction
- get_knowledge_evolution: Track how concepts evolved over time
- explore_graph: Interactive graph exploration and visualization
- get_related_concepts: Find conceptually related items
- temporal_reasoning: Answer questions using temporal graph data

Usage:
    python3 -m src.ptolemies.mcp.enhanced_ptolemies_mcp
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional, Sequence
from datetime import datetime

# MCP imports
try:
    from mcp.server import Server
    from mcp.server.models import InitializationOptions
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        Resource,
        Tool,
        TextContent,
        ImageContent,
        EmbeddedResource,
    )
except ImportError:
    raise ImportError("MCP library not found. Install with: pip install mcp")

from ..integrations.hybrid_storage import HybridKnowledgeManager, HybridSearchResult
from ..integrations.graphiti.service_wrapper import GraphitiServiceConfig
from ..models.knowledge_item import KnowledgeItemCreate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("enhanced_ptolemies_mcp")

class EnhancedPtolemiesMCPServer:
    """Enhanced MCP server with Graphiti integration."""
    
    def __init__(self):
        self.server = Server("enhanced-ptolemies")
        self.manager: Optional[HybridKnowledgeManager] = None
        self._setup_tools()
        self._setup_resources()
    
    def _setup_tools(self):
        """Setup MCP tools with Graphiti capabilities."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List all available tools."""
            return [
                Tool(
                    name="search_knowledge",
                    description="Hybrid search across documents and knowledge graph",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query text"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results",
                                "default": 20
                            },
                            "include_documents": {
                                "type": "boolean",
                                "description": "Include document search results",
                                "default": True
                            },
                            "include_entities": {
                                "type": "boolean", 
                                "description": "Include entity search results",
                                "default": True
                            },
                            "include_relationships": {
                                "type": "boolean",
                                "description": "Include relationship search results", 
                                "default": True
                            },
                            "filter_tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by tags"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                
                Tool(
                    name="store_knowledge",
                    description="Store new knowledge with automatic relationship extraction",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Knowledge item title"
                            },
                            "content": {
                                "type": "string",
                                "description": "Main content text"
                            },
                            "content_type": {
                                "type": "string",
                                "description": "Content type",
                                "default": "text/markdown"
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Associated tags"
                            },
                            "source": {
                                "type": "string",
                                "description": "Content source"
                            },
                            "extract_relationships": {
                                "type": "boolean",
                                "description": "Extract relationships via Graphiti",
                                "default": True
                            },
                            "category": {
                                "type": "string",
                                "description": "Content category",
                                "default": "knowledge"
                            }
                        },
                        "required": ["title", "content"]
                    }
                ),
                
                Tool(
                    name="get_knowledge_evolution",
                    description="Track how a concept evolved over time",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "concept": {
                                "type": "string",
                                "description": "Concept to track"
                            },
                            "start_time": {
                                "type": "string",
                                "description": "Start time (ISO format)",
                                "format": "date-time"
                            },
                            "end_time": {
                                "type": "string", 
                                "description": "End time (ISO format)",
                                "format": "date-time"
                            }
                        },
                        "required": ["concept"]
                    }
                ),
                
                Tool(
                    name="explore_graph",
                    description="Interactive graph exploration and visualization",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Starting point for exploration"
                            },
                            "depth": {
                                "type": "integer",
                                "description": "Exploration depth",
                                "default": 3
                            },
                            "layout": {
                                "type": "string",
                                "description": "Graph layout algorithm",
                                "enum": ["force", "hierarchical", "circular"],
                                "default": "force"
                            },
                            "include_documents": {
                                "type": "boolean",
                                "description": "Include document references",
                                "default": True
                            }
                        },
                        "required": ["query"]
                    }
                ),
                
                Tool(
                    name="get_related_concepts",
                    description="Find conceptually related items using graph traversal",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "concept": {
                                "type": "string",
                                "description": "Source concept"
                            },
                            "relationship_types": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Types of relationships to follow"
                            },
                            "max_distance": {
                                "type": "integer",
                                "description": "Maximum graph distance",
                                "default": 2
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum results",
                                "default": 20
                            }
                        },
                        "required": ["concept"]
                    }
                ),
                
                Tool(
                    name="temporal_reasoning",
                    description="Answer questions using temporal graph data",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "Question to answer"
                            },
                            "context_entities": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Entities to focus on"
                            },
                            "time_range": {
                                "type": "object",
                                "properties": {
                                    "start": {"type": "string", "format": "date-time"},
                                    "end": {"type": "string", "format": "date-time"}
                                },
                                "description": "Time range to consider"
                            }
                        },
                        "required": ["question"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> Sequence[TextContent]:
            """Handle tool execution."""
            try:
                await self._ensure_manager()
                
                if name == "search_knowledge":
                    return await self._search_knowledge(arguments)
                elif name == "store_knowledge":
                    return await self._store_knowledge(arguments)
                elif name == "get_knowledge_evolution":
                    return await self._get_knowledge_evolution(arguments)
                elif name == "explore_graph":
                    return await self._explore_graph(arguments)
                elif name == "get_related_concepts":
                    return await self._get_related_concepts(arguments)
                elif name == "temporal_reasoning":
                    return await self._temporal_reasoning(arguments)
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
                    
            except Exception as e:
                logger.error(f"Tool execution failed: {str(e)}")
                return [TextContent(type="text", text=f"Error executing tool: {str(e)}")]
    
    def _setup_resources(self):
        """Setup MCP resources."""
        
        @self.server.list_resources()
        async def handle_list_resources() -> List[Resource]:
            """List available resources."""
            return [
                Resource(
                    uri="ptolemies://graph/explorer",
                    name="Graph Explorer",
                    description="Interactive knowledge graph explorer"
                ),
                Resource(
                    uri="ptolemies://stats/knowledge",
                    name="Knowledge Statistics", 
                    description="Knowledge base statistics and metrics"
                ),
                Resource(
                    uri="ptolemies://docs/api",
                    name="API Documentation",
                    description="Enhanced Ptolemies API documentation"
                )
            ]
        
        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Read resource content."""
            if uri == "ptolemies://graph/explorer":
                return await self._get_graph_explorer_html()
            elif uri == "ptolemies://stats/knowledge":
                return await self._get_knowledge_stats()
            elif uri == "ptolemies://docs/api":
                return await self._get_api_documentation()
            else:
                raise ValueError(f"Unknown resource: {uri}")
    
    async def _ensure_manager(self):
        """Ensure hybrid manager is initialized."""
        if not self.manager:
            config = GraphitiServiceConfig()
            self.manager = HybridKnowledgeManager(graphiti_config=config)
            await self.manager.initialize()
            logger.info("Hybrid manager initialized")
    
    async def _search_knowledge(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Execute hybrid knowledge search."""
        query = arguments["query"]
        limit = arguments.get("limit", 20)
        include_documents = arguments.get("include_documents", True)
        include_entities = arguments.get("include_entities", True)
        include_relationships = arguments.get("include_relationships", True)
        filter_tags = arguments.get("filter_tags")
        
        logger.info(f"Searching for: {query}")
        
        result = await self.manager.hybrid_search(
            query=query,
            limit=limit,
            include_documents=include_documents,
            include_entities=include_entities,
            include_relationships=include_relationships,
            filter_tags=filter_tags
        )
        
        # Format results
        response = {
            "query": query,
            "total_results": result.total_results,
            "processing_time": result.processing_time,
            "sources": {
                "documents": len(result.documents),
                "entities": len(result.entities),
                "relationships": len(result.relationships)
            }
        }
        
        # Add document results
        if result.documents:
            response["documents"] = [
                {
                    "id": doc.id,
                    "title": doc.title,
                    "content_preview": doc.content[:200] + "..." if len(doc.content) > 200 else doc.content,
                    "tags": doc.tags,
                    "source": doc.source,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None
                }
                for doc in result.documents
            ]
        
        # Add entity results
        if result.entities:
            response["entities"] = result.entities
        
        # Add relationship results
        if result.relationships:
            response["relationships"] = result.relationships
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
    
    async def _store_knowledge(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Store new knowledge item."""
        title = arguments["title"]
        content = arguments["content"]
        content_type = arguments.get("content_type", "text/markdown")
        tags = arguments.get("tags", [])
        source = arguments.get("source", "mcp_client")
        extract_relationships = arguments.get("extract_relationships", True)
        category = arguments.get("category", "knowledge")
        
        # Create knowledge item
        item_create = KnowledgeItemCreate(
            title=title,
            content=content,
            content_type=content_type,
            tags=tags,
            source=source,
            metadata={"category": category, "source_type": "mcp"}
        )
        
        logger.info(f"Storing knowledge: {title}")
        
        knowledge_item, graphiti_result = await self.manager.store_knowledge_item(
            item_create,
            extract_relationships=extract_relationships
        )
        
        response = {
            "success": True,
            "knowledge_item": {
                "id": knowledge_item.id,
                "title": knowledge_item.title,
                "content_type": knowledge_item.content_type,
                "tags": knowledge_item.tags,
                "created_at": knowledge_item.created_at.isoformat() if knowledge_item.created_at else None
            }
        }
        
        if graphiti_result:
            response["graphiti_processing"] = {
                "episode_id": graphiti_result.get("episode_id"),
                "entities_extracted": len(graphiti_result.get("entities", [])),
                "relationships_extracted": len(graphiti_result.get("relationships", [])),
                "processing_time": graphiti_result.get("processing_time", 0)
            }
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
    
    async def _get_knowledge_evolution(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Get temporal evolution of a concept."""
        concept = arguments["concept"]
        start_time = arguments.get("start_time")
        end_time = arguments.get("end_time")
        
        # Parse datetime strings if provided
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00')) if start_time else None
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00')) if end_time else None
        
        logger.info(f"Getting evolution for: {concept}")
        
        evolution_data = await self.manager.get_knowledge_evolution(
            concept=concept,
            start_time=start_dt,
            end_time=end_dt
        )
        
        return [TextContent(type="text", text=json.dumps(evolution_data, indent=2))]
    
    async def _explore_graph(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Explore knowledge graph interactively."""
        query = arguments["query"]
        depth = arguments.get("depth", 3)
        layout = arguments.get("layout", "force")
        include_documents = arguments.get("include_documents", True)
        
        logger.info(f"Exploring graph from: {query}")
        
        viz_data = await self.manager.get_graph_visualization(
            query=query,
            depth=depth,
            layout=layout
        )
        
        # Enhance with exploration metadata
        response = {
            "exploration_query": query,
            "graph_data": viz_data,
            "exploration_stats": {
                "nodes": len(viz_data.get("nodes", [])),
                "edges": len(viz_data.get("edges", [])),
                "depth": depth,
                "layout": layout
            }
        }
        
        if include_documents:
            # Add document context for nodes
            for node in viz_data.get("nodes", []):
                if "document_references" in node:
                    response.setdefault("document_context", []).extend(
                        node["document_references"]
                    )
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
    
    async def _get_related_concepts(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Find related concepts using graph traversal."""
        concept = arguments["concept"]
        relationship_types = arguments.get("relationship_types", [])
        max_distance = arguments.get("max_distance", 2)
        limit = arguments.get("limit", 20)
        
        logger.info(f"Finding concepts related to: {concept}")
        
        # Use hybrid search to find related items
        search_result = await self.manager.hybrid_search(
            query=concept,
            limit=limit,
            include_entities=True,
            include_relationships=True
        )
        
        # Process relationships to find connected concepts
        related_concepts = []
        concept_scores = {}
        
        # Extract concepts from entities and relationships
        for entity in search_result.entities:
            entity_name = entity.get("name", "")
            if entity_name and entity_name.lower() != concept.lower():
                score = entity.get("relevance_score", 0.5)
                concept_scores[entity_name] = max(concept_scores.get(entity_name, 0), score)
        
        for rel in search_result.relationships:
            source = rel.get("source", "")
            target = rel.get("target", "")
            rel_type = rel.get("type", "")
            
            # Add related concepts based on relationships
            for candidate in [source, target]:
                if candidate and candidate.lower() != concept.lower():
                    if not relationship_types or rel_type in relationship_types:
                        score = rel.get("weight", 0.5)
                        concept_scores[candidate] = max(concept_scores.get(candidate, 0), score)
        
        # Sort by relevance score
        related_concepts = [
            {"concept": name, "relevance_score": score, "distance": 1}
            for name, score in sorted(concept_scores.items(), key=lambda x: x[1], reverse=True)
        ]
        
        response = {
            "source_concept": concept,
            "related_concepts": related_concepts[:limit],
            "search_stats": {
                "entities_found": len(search_result.entities),
                "relationships_found": len(search_result.relationships),
                "max_distance": max_distance,
                "relationship_types_filter": relationship_types
            }
        }
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
    
    async def _temporal_reasoning(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        """Answer questions using temporal graph data."""
        question = arguments["question"]
        context_entities = arguments.get("context_entities", [])
        time_range = arguments.get("time_range", {})
        
        logger.info(f"Temporal reasoning for: {question}")
        
        # Extract key concepts from the question for search
        search_terms = question
        if context_entities:
            search_terms += " " + " ".join(context_entities)
        
        # Search for relevant information
        search_result = await self.manager.hybrid_search(
            query=search_terms,
            limit=30,
            include_documents=True,
            include_entities=True,
            include_relationships=True
        )
        
        # Compile temporal context
        temporal_context = {
            "question": question,
            "search_performed": search_terms,
            "relevant_documents": [
                {
                    "title": doc.title,
                    "content_preview": doc.content[:300],
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    "tags": doc.tags
                }
                for doc in search_result.documents
            ],
            "entities": search_result.entities,
            "relationships": search_result.relationships,
            "context_entities": context_entities,
            "time_range": time_range
        }
        
        # Get evolution data for context entities
        if context_entities:
            evolution_data = {}
            for entity in context_entities[:3]:  # Limit to avoid too much data
                try:
                    start_time = None
                    end_time = None
                    if time_range:
                        start_time = datetime.fromisoformat(time_range.get("start", "").replace('Z', '+00:00')) if time_range.get("start") else None
                        end_time = datetime.fromisoformat(time_range.get("end", "").replace('Z', '+00:00')) if time_range.get("end") else None
                    
                    evolution = await self.manager.get_knowledge_evolution(
                        concept=entity,
                        start_time=start_time,
                        end_time=end_time
                    )
                    evolution_data[entity] = evolution
                    
                except Exception as e:
                    logger.warning(f"Failed to get evolution for {entity}: {str(e)}")
            
            temporal_context["entity_evolution"] = evolution_data
        
        response = {
            "reasoning_type": "temporal_analysis",
            "context": temporal_context,
            "analysis": {
                "total_sources": len(search_result.documents),
                "relevant_entities": len(search_result.entities),
                "relationship_connections": len(search_result.relationships),
                "temporal_depth": "multi_period" if time_range else "current",
                "reasoning_note": "This analysis combines document content, entity relationships, and temporal evolution data to provide context for answering the question."
            }
        }
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
    
    async def _get_graph_explorer_html(self) -> str:
        """Generate HTML for graph exploration interface."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Ptolemies Knowledge Graph Explorer</title>
            <script src="https://d3js.org/d3.v7.min.js"></script>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .graph-container { border: 1px solid #ccc; height: 600px; }
                .search-box { margin-bottom: 20px; }
                .stats { margin-top: 20px; padding: 10px; background: #f5f5f5; }
                .node { fill: #1f77b4; stroke: #fff; stroke-width: 2px; }
                .link { stroke: #999; stroke-opacity: 0.6; }
            </style>
        </head>
        <body>
            <h1>Ptolemies Knowledge Graph Explorer</h1>
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="Enter concept to explore..." style="width: 300px; padding: 5px;">
                <button onclick="exploreGraph()">Explore</button>
            </div>
            <div class="graph-container" id="graphContainer">
                <p>Enter a concept above to start exploring the knowledge graph.</p>
            </div>
            <div class="stats" id="statsPanel">
                Graph statistics will appear here after exploration.
            </div>
            
            <script>
                async function exploreGraph() {
                    const query = document.getElementById('searchInput').value;
                    if (!query) return;
                    
                    // This would integrate with the MCP server for actual data
                    document.getElementById('graphContainer').innerHTML = 
                        `<p>Exploring: ${query}<br>Integration with live Graphiti data would appear here.</p>`;
                    
                    document.getElementById('statsPanel').innerHTML = 
                        `<strong>Search:</strong> ${query}<br><strong>Status:</strong> Ready for MCP integration`;
                }
            </script>
        </body>
        </html>
        """
    
    async def _get_knowledge_stats(self) -> str:
        """Get knowledge base statistics."""
        await self._ensure_manager()
        
        try:
            # Get document count
            documents = await self.manager.surrealdb_client.list_knowledge_items(limit=1000)
            doc_count = len(documents)
            
            # Basic statistics
            stats = {
                "timestamp": datetime.now().isoformat(),
                "total_documents": doc_count,
                "storage_systems": {
                    "surrealdb": {
                        "status": "active",
                        "documents": doc_count
                    },
                    "graphiti": {
                        "status": "active" if self.manager.graphiti_client else "inactive",
                        "service_url": f"http://localhost:{self.manager.graphiti_client.config.service_port}" if self.manager.graphiti_client else None
                    }
                },
                "integration_status": "hybrid_active",
                "recent_activity": "Migration and enhanced MCP server deployment"
            }
            
            return json.dumps(stats, indent=2)
            
        except Exception as e:
            return json.dumps({"error": f"Failed to get stats: {str(e)}"}, indent=2)
    
    async def _get_api_documentation(self) -> str:
        """Get API documentation."""
        return """
# Enhanced Ptolemies MCP Server API

## Overview
This MCP server provides hybrid knowledge base capabilities combining SurrealDB document storage with Graphiti temporal knowledge graph reasoning.

## Tools Available

### search_knowledge
Hybrid search across documents and knowledge graph.
- **query**: Search text (required)
- **limit**: Max results (default: 20)
- **include_documents**: Include document results (default: true)
- **include_entities**: Include entity results (default: true)
- **include_relationships**: Include relationship results (default: true)
- **filter_tags**: Array of tags to filter by

### store_knowledge
Store new knowledge with automatic relationship extraction.
- **title**: Knowledge item title (required)
- **content**: Main content text (required)
- **content_type**: Content type (default: text/markdown)
- **tags**: Associated tags array
- **source**: Content source
- **extract_relationships**: Extract via Graphiti (default: true)
- **category**: Content category (default: knowledge)

### get_knowledge_evolution
Track how a concept evolved over time.
- **concept**: Concept to track (required)
- **start_time**: Start time (ISO format)
- **end_time**: End time (ISO format)

### explore_graph
Interactive graph exploration and visualization.
- **query**: Starting point for exploration (required)
- **depth**: Exploration depth (default: 3)
- **layout**: Graph layout algorithm (default: force)
- **include_documents**: Include document references (default: true)

### get_related_concepts
Find conceptually related items using graph traversal.
- **concept**: Source concept (required)
- **relationship_types**: Types of relationships to follow
- **max_distance**: Maximum graph distance (default: 2)
- **limit**: Maximum results (default: 20)

### temporal_reasoning
Answer questions using temporal graph data.
- **question**: Question to answer (required)
- **context_entities**: Entities to focus on
- **time_range**: Time range to consider

## Resources Available

### ptolemies://graph/explorer
Interactive knowledge graph explorer interface

### ptolemies://stats/knowledge  
Knowledge base statistics and metrics

### ptolemies://docs/api
This API documentation

## Architecture
- **SurrealDB**: Document storage, metadata, search indices
- **Graphiti**: Temporal relationship extraction, graph reasoning
- **Hybrid Manager**: Coordinated operations, unified queries
- **MCP Integration**: Tool-based interface for LLM interaction
"""

    async def run(self):
        """Run the MCP server."""
        logger.info("🚀 Starting Enhanced Ptolemies MCP Server")
        logger.info("Features: Hybrid storage, Graphiti integration, temporal reasoning")
        
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="enhanced-ptolemies",
                    server_version="2.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=None,
                        experimental_capabilities=None,
                    ),
                ),
            )

async def main():
    """Main entry point."""
    server = EnhancedPtolemiesMCPServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())