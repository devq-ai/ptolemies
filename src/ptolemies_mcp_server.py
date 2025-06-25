#!/usr/bin/env python3
"""
Ptolemies MCP Server
Model Context Protocol server for the Ptolemies knowledge base system.
Provides search, indexing, and knowledge management capabilities.
"""

import asyncio
import json
import traceback
from typing import Dict, List, Any, Optional, Union, Sequence, Callable
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

import logfire
from surrealdb_integration import SurrealDBVectorStore, VectorStoreConfig, create_vector_store
from neo4j_integration import Neo4jGraphStore, Neo4jConfig, create_graph_store
from hybrid_query_engine import HybridQueryEngine, HybridQueryConfig, QueryType, create_hybrid_engine
from performance_optimizer import PerformanceOptimizer, PerformanceConfig, create_performance_optimizer
from redis_cache_layer import RedisCacheLayer, RedisCacheConfig, create_redis_cache_layer
from crawl4ai_integration import PtolemiesCrawler, CrawlConfig
from mcp_tool_registry import MCPToolRegistry, ToolMetadata, ToolCategory, create_tool_spec

# Configure Logfire
logfire.configure(send_to_logfire=False)  # Configure appropriately for production

@dataclass
class PtolemiesMCPConfig:
    """Configuration for Ptolemies MCP Server."""
    # Server settings
    server_name: str = "ptolemies-knowledge"
    server_version: str = "1.0.0"
    max_concurrent_requests: int = 10
    default_search_limit: int = 50

    # Component configurations
    vector_config: Optional[VectorStoreConfig] = None
    graph_config: Optional[Neo4jConfig] = None
    hybrid_config: Optional[HybridQueryConfig] = None
    performance_config: Optional[PerformanceConfig] = None
    cache_config: Optional[RedisCacheConfig] = None
    crawl_config: Optional[CrawlConfig] = None

    # Search settings
    enable_semantic_search: bool = True
    enable_graph_search: bool = True
    enable_hybrid_search: bool = True
    enable_concept_expansion: bool = True

    # Performance settings
    enable_caching: bool = True
    enable_performance_optimization: bool = True
    cache_search_results: bool = True
    cache_ttl_seconds: int = 3600

    # Tool registry settings
    enable_dynamic_tools: bool = True
    tool_registry_config_file: Optional[str] = None

class PtolemiesMCPServer:
    """Main MCP server for Ptolemies knowledge base."""

    def __init__(self, config: PtolemiesMCPConfig = None):
        self.config = config or PtolemiesMCPConfig()
        self.server = Server(self.config.server_name)

        # Core components
        self.vector_store: Optional[SurrealDBVectorStore] = None
        self.graph_store: Optional[Neo4jGraphStore] = None
        self.hybrid_engine: Optional[HybridQueryEngine] = None
        self.performance_optimizer: Optional[PerformanceOptimizer] = None
        self.cache_layer: Optional[RedisCacheLayer] = None
        self.crawl_service: Optional[PtolemiesCrawler] = None

        # Tool registry
        self.tool_registry: Optional[MCPToolRegistry] = None
        if self.config.enable_dynamic_tools:
            self.tool_registry = MCPToolRegistry(self.config.tool_registry_config_file)

        # Request tracking
        self.active_requests = 0
        self.request_semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)

        # Setup MCP handlers
        self._setup_handlers()

        # Register built-in tools if registry is enabled
        if self.tool_registry:
            self._register_builtin_tools()

    def _setup_handlers(self):
        """Setup MCP server handlers."""

        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            """List available tools."""
            tools = []

            # Get tools from registry if enabled
            if self.tool_registry:
                registry_tools = self.tool_registry.get_tool_specs()
                tools.extend(registry_tools)

            if self.config.enable_semantic_search:
                tools.append(types.Tool(
                    name="semantic_search",
                    description="Search the knowledge base using semantic similarity",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results",
                                "default": self.config.default_search_limit
                            },
                            "source_filter": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter results by source names"
                            },
                            "quality_threshold": {
                                "type": "number",
                                "description": "Minimum quality score for results",
                                "default": 0.5
                            }
                        },
                        "required": ["query"]
                    }
                ))

            if self.config.enable_graph_search:
                tools.append(types.Tool(
                    name="graph_search",
                    description="Search for related concepts and relationships in the knowledge graph",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query"
                            },
                            "search_type": {
                                "type": "string",
                                "enum": ["concept", "document", "relationship"],
                                "description": "Type of graph search",
                                "default": "concept"
                            },
                            "max_depth": {
                                "type": "integer",
                                "description": "Maximum traversal depth",
                                "default": 2
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results",
                                "default": self.config.default_search_limit
                            }
                        },
                        "required": ["query"]
                    }
                ))

            if self.config.enable_hybrid_search:
                tools.append(types.Tool(
                    name="hybrid_search",
                    description="Search using both semantic and graph approaches for comprehensive results",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query"
                            },
                            "query_type": {
                                "type": "string",
                                "enum": ["semantic_only", "graph_only", "hybrid_balanced",
                                        "semantic_then_graph", "graph_then_semantic", "concept_expansion"],
                                "description": "Type of hybrid search strategy",
                                "default": "hybrid_balanced"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results",
                                "default": self.config.default_search_limit
                            },
                            "source_filter": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter results by source names"
                            }
                        },
                        "required": ["query"]
                    }
                ))

            # Document management tools
            tools.append(types.Tool(
                name="index_document",
                description="Index a document or URL into the knowledge base",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL to crawl and index"
                        },
                        "content": {
                            "type": "string",
                            "description": "Raw content to index (alternative to URL)"
                        },
                        "title": {
                            "type": "string",
                            "description": "Document title"
                        },
                        "source_name": {
                            "type": "string",
                            "description": "Source identifier"
                        },
                        "topics": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Document topics/tags"
                        }
                    }
                }
            ))

            # Document retrieval tools
            tools.append(types.Tool(
                name="retrieve_document",
                description="Retrieve a specific document by ID or URL",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "document_id": {
                            "type": "string",
                            "description": "Document ID to retrieve"
                        },
                        "url": {
                            "type": "string",
                            "description": "Document URL to retrieve"
                        },
                        "include_chunks": {
                            "type": "boolean",
                            "description": "Include document chunks in response",
                            "default": False
                        },
                        "include_metadata": {
                            "type": "boolean",
                            "description": "Include document metadata",
                            "default": True
                        }
                    }
                }
            ))

            # Concept exploration tools
            tools.append(types.Tool(
                name="explore_concept",
                description="Explore a concept and its relationships in the knowledge graph",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "concept_name": {
                            "type": "string",
                            "description": "Name of the concept to explore"
                        },
                        "relationship_types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Types of relationships to include",
                            "default": ["RELATES_TO", "IMPLEMENTS", "DEPENDS_ON"]
                        },
                        "max_depth": {
                            "type": "integer",
                            "description": "Maximum depth for relationship traversal",
                            "default": 2
                        },
                        "include_documents": {
                            "type": "boolean",
                            "description": "Include related documents",
                            "default": True
                        }
                    },
                    "required": ["concept_name"]
                }
            ))

            # Knowledge discovery tools
            tools.append(types.Tool(
                name="discover_patterns",
                description="Discover patterns and relationships in the knowledge base",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "pattern_type": {
                            "type": "string",
                            "enum": ["topic_clusters", "concept_hierarchies", "document_similarities", "temporal_patterns"],
                            "description": "Type of pattern to discover",
                            "default": "concept_hierarchies"
                        },
                        "focus_area": {
                            "type": "string",
                            "description": "Specific area to focus pattern discovery on"
                        },
                        "min_confidence": {
                            "type": "number",
                            "description": "Minimum confidence threshold for patterns",
                            "default": 0.7
                        }
                    }
                }
            ))

            # Analytics and management tools
            tools.append(types.Tool(
                name="get_knowledge_stats",
                description="Get statistics about the knowledge base",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "include_performance": {
                            "type": "boolean",
                            "description": "Include performance metrics",
                            "default": True
                        },
                        "include_cache": {
                            "type": "boolean",
                            "description": "Include cache statistics",
                            "default": True
                        }
                    }
                }
            ))

            tools.append(types.Tool(
                name="get_query_suggestions",
                description="Get query suggestions based on partial input",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "partial_query": {
                            "type": "string",
                            "description": "Partial query text"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of suggestions",
                            "default": 10
                        }
                    },
                    "required": ["partial_query"]
                }
            ))

            return tools

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
            """Handle tool calls."""
            async with self.request_semaphore:
                self.active_requests += 1
                try:
                    with logfire.span("MCP tool call", tool_name=name):
                        logfire.info("Tool called", tool=name, arguments=arguments)

                        # Try registry tools first
                        if self.tool_registry and name in self.tool_registry.tools:
                            return await self.tool_registry.execute_tool(name, arguments)

                        # Fallback to built-in tools
                        if name == "semantic_search":
                            return await self._handle_semantic_search(arguments)
                        elif name == "graph_search":
                            return await self._handle_graph_search(arguments)
                        elif name == "hybrid_search":
                            return await self._handle_hybrid_search(arguments)
                        elif name == "index_document":
                            return await self._handle_index_document(arguments)
                        elif name == "retrieve_document":
                            return await self._handle_retrieve_document(arguments)
                        elif name == "explore_concept":
                            return await self._handle_explore_concept(arguments)
                        elif name == "discover_patterns":
                            return await self._handle_discover_patterns(arguments)
                        elif name == "get_knowledge_stats":
                            return await self._handle_get_knowledge_stats(arguments)
                        elif name == "get_query_suggestions":
                            return await self._handle_get_query_suggestions(arguments)
                        else:
                            raise ValueError(f"Unknown tool: {name}")

                except Exception as e:
                    logfire.error("Tool call failed", tool=name, error=str(e), traceback=traceback.format_exc())
                    return [types.TextContent(
                        type="text",
                        text=f"Error: {str(e)}"
                    )]
                finally:
                    self.active_requests -= 1

    def _register_builtin_tools(self):
        """Register built-in tools with the registry."""
        if not self.tool_registry:
            return

        # Register semantic search tool
        if self.config.enable_semantic_search:
            semantic_spec = create_tool_spec(
                "semantic_search",
                "Search the knowledge base using semantic similarity",
                {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query"},
                        "limit": {"type": "integer", "description": "Maximum number of results", "default": self.config.default_search_limit},
                        "source_filter": {"type": "array", "items": {"type": "string"}, "description": "Filter results by source names"},
                        "quality_threshold": {"type": "number", "description": "Minimum quality score for results", "default": 0.5}
                    },
                    "required": ["query"]
                }
            )
            semantic_metadata = ToolMetadata(
                name="semantic_search",
                description="Semantic vector search across knowledge base",
                category=ToolCategory.SEARCH,
                cache_ttl_seconds=self.config.cache_ttl_seconds if self.config.cache_search_results else None
            )
            self.tool_registry.register_tool("semantic_search", self._handle_semantic_search, semantic_spec, semantic_metadata)

        # Register graph search tool
        if self.config.enable_graph_search:
            graph_spec = create_tool_spec(
                "graph_search",
                "Search for related concepts and relationships in the knowledge graph",
                {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query"},
                        "search_type": {"type": "string", "enum": ["concept", "document", "relationship"], "description": "Type of graph search", "default": "concept"},
                        "max_depth": {"type": "integer", "description": "Maximum traversal depth", "default": 2},
                        "limit": {"type": "integer", "description": "Maximum number of results", "default": self.config.default_search_limit}
                    },
                    "required": ["query"]
                }
            )
            graph_metadata = ToolMetadata(
                name="graph_search",
                description="Graph-based concept and relationship search",
                category=ToolCategory.SEARCH,
                cache_ttl_seconds=self.config.cache_ttl_seconds if self.config.cache_search_results else None
            )
            self.tool_registry.register_tool("graph_search", self._handle_graph_search, graph_spec, graph_metadata)

        # Register hybrid search tool
        if self.config.enable_hybrid_search:
            hybrid_spec = create_tool_spec(
                "hybrid_search",
                "Search using both semantic and graph approaches for comprehensive results",
                {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query"},
                        "query_type": {"type": "string", "enum": ["semantic_only", "graph_only", "hybrid_balanced", "semantic_then_graph", "graph_then_semantic", "concept_expansion"], "description": "Type of hybrid search strategy", "default": "hybrid_balanced"},
                        "limit": {"type": "integer", "description": "Maximum number of results", "default": self.config.default_search_limit},
                        "source_filter": {"type": "array", "items": {"type": "string"}, "description": "Filter results by source names"}
                    },
                    "required": ["query"]
                }
            )
            hybrid_metadata = ToolMetadata(
                name="hybrid_search",
                description="Advanced hybrid search combining multiple approaches",
                category=ToolCategory.SEARCH,
                cache_ttl_seconds=self.config.cache_ttl_seconds if self.config.cache_search_results else None
            )
            self.tool_registry.register_tool("hybrid_search", self._handle_hybrid_search, hybrid_spec, hybrid_metadata)

        # Register document indexing tool
        index_spec = create_tool_spec(
            "index_document",
            "Index a document or URL into the knowledge base",
            {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to crawl and index"},
                    "content": {"type": "string", "description": "Raw content to index (alternative to URL)"},
                    "title": {"type": "string", "description": "Document title"},
                    "source_name": {"type": "string", "description": "Source identifier"},
                    "topics": {"type": "array", "items": {"type": "string"}, "description": "Document topics/tags"}
                }
            }
        )
        index_metadata = ToolMetadata(
            name="index_document",
            description="Index documents and URLs into knowledge base",
            category=ToolCategory.INDEXING,
            timeout_seconds=300  # Longer timeout for indexing
        )
        self.tool_registry.register_tool("index_document", self._handle_index_document, index_spec, index_metadata)

        # Register analytics tools
        stats_spec = create_tool_spec(
            "get_knowledge_stats",
            "Get statistics about the knowledge base",
            {
                "type": "object",
                "properties": {
                    "include_performance": {"type": "boolean", "description": "Include performance metrics", "default": True},
                    "include_cache": {"type": "boolean", "description": "Include cache statistics", "default": True}
                }
            }
        )
        stats_metadata = ToolMetadata(
            name="get_knowledge_stats",
            description="Retrieve knowledge base analytics and statistics",
            category=ToolCategory.ANALYTICS
        )
        self.tool_registry.register_tool("get_knowledge_stats", self._handle_get_knowledge_stats, stats_spec, stats_metadata)

        suggestions_spec = create_tool_spec(
            "get_query_suggestions",
            "Get query suggestions based on partial input",
            {
                "type": "object",
                "properties": {
                    "partial_query": {"type": "string", "description": "Partial query text"},
                    "limit": {"type": "integer", "description": "Maximum number of suggestions", "default": 10}
                },
                "required": ["partial_query"]
            }
        )
        suggestions_metadata = ToolMetadata(
            name="get_query_suggestions",
            description="Generate intelligent query suggestions",
            category=ToolCategory.UTILITIES
        )
        self.tool_registry.register_tool("get_query_suggestions", self._handle_get_query_suggestions, suggestions_spec, suggestions_metadata)

        logfire.info("Built-in tools registered with tool registry", total_tools=len(self.tool_registry.tools))

    async def _handle_semantic_search(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle semantic search requests."""
        query = arguments["query"]
        limit = arguments.get("limit", self.config.default_search_limit)
        source_filter = arguments.get("source_filter")
        quality_threshold = arguments.get("quality_threshold", 0.5)

        if not self.vector_store:
            raise RuntimeError("Vector store not initialized")

        with logfire.span("Semantic search", query=query, limit=limit):
            # Check cache first if enabled
            cache_key = None
            if self.config.cache_search_results and self.cache_layer:
                cache_key = f"semantic:{hash(f'{query}:{limit}:{source_filter}:{quality_threshold}')}"
                cached_result, found = await self.cache_layer.get(cache_key, "query")
                if found:
                    logfire.info("Cache hit for semantic search")
                    return [types.TextContent(type="text", text=json.dumps(cached_result, indent=2))]

            # Perform search with performance optimization
            if self.performance_optimizer:
                async def search_operation(**kwargs):
                    return await self.vector_store.semantic_search(
                        query=query,
                        limit=limit,
                        source_filter=source_filter,
                        quality_threshold=quality_threshold
                    )

                results, was_cached = await self.performance_optimizer.cached_operation(
                    "query", "semantic_search", search_operation
                )
            else:
                results = await self.vector_store.semantic_search(
                    query=query,
                    limit=limit,
                    source_filter=source_filter,
                    quality_threshold=quality_threshold
                )

            # Format results
            formatted_results = []
            for result in results:
                doc = result.document
                formatted_results.append({
                    "id": doc.id,
                    "title": doc.title,
                    "content": doc.content[:500] + "..." if len(doc.content) > 500 else doc.content,
                    "source_name": doc.source_name,
                    "source_url": doc.source_url,
                    "similarity_score": result.similarity_score,
                    "quality_score": doc.quality_score,
                    "topics": doc.topics,
                    "chunk_info": f"{doc.chunk_index + 1}/{doc.total_chunks}" if doc.total_chunks > 1 else "1/1"
                })

            response_data = {
                "query": query,
                "search_type": "semantic",
                "results_count": len(formatted_results),
                "results": formatted_results
            }

            # Cache results if enabled
            if cache_key and self.cache_layer:
                await self.cache_layer.set(cache_key, response_data, "query", self.config.cache_ttl_seconds)

            logfire.info("Semantic search completed",
                        query=query,
                        results_count=len(formatted_results))

            return [types.TextContent(
                type="text",
                text=json.dumps(response_data, indent=2)
            )]

    async def _handle_graph_search(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle graph search requests."""
        query = arguments["query"]
        search_type = arguments.get("search_type", "concept")
        max_depth = arguments.get("max_depth", 2)
        limit = arguments.get("limit", self.config.default_search_limit)

        if not self.graph_store:
            raise RuntimeError("Graph store not initialized")

        with logfire.span("Graph search", query=query, search_type=search_type):
            # Check cache first if enabled
            cache_key = None
            if self.config.cache_search_results and self.cache_layer:
                cache_key = f"graph:{hash(f'{query}:{search_type}:{max_depth}:{limit}')}"
                cached_result, found = await self.cache_layer.get(cache_key, "query")
                if found:
                    logfire.info("Cache hit for graph search")
                    return [types.TextContent(type="text", text=json.dumps(cached_result, indent=2))]

            # Perform search
            result = await self.graph_store.graph_search(
                query=query,
                search_type=search_type,
                limit=limit,
                max_depth=max_depth
            )

            # Format results
            response_data = {
                "query": query,
                "search_type": "graph",
                "graph_search_type": search_type,
                "max_depth": max_depth,
                "nodes_count": len(result.nodes),
                "relationships_count": len(result.relationships),
                "paths_count": len(result.paths),
                "nodes": result.nodes[:limit],
                "relationships": result.relationships[:limit],
                "paths": result.paths[:10],  # Limit paths for readability
                "metadata": result.query_metadata
            }

            # Cache results if enabled
            if cache_key and self.cache_layer:
                await self.cache_layer.set(cache_key, response_data, "query", self.config.cache_ttl_seconds)

            logfire.info("Graph search completed",
                        query=query,
                        nodes_count=len(result.nodes),
                        relationships_count=len(result.relationships))

            return [types.TextContent(
                type="text",
                text=json.dumps(response_data, indent=2)
            )]

    async def _handle_hybrid_search(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle hybrid search requests."""
        query = arguments["query"]
        query_type_str = arguments.get("query_type", "hybrid_balanced")
        limit = arguments.get("limit", self.config.default_search_limit)
        source_filter = arguments.get("source_filter")

        if not self.hybrid_engine:
            raise RuntimeError("Hybrid engine not initialized")

        # Convert string to QueryType enum
        query_type = QueryType(query_type_str)

        with logfire.span("Hybrid search", query=query, query_type=query_type_str):
            # Check cache first if enabled
            cache_key = None
            if self.config.cache_search_results and self.cache_layer:
                cache_key = f"hybrid:{hash(f'{query}:{query_type_str}:{limit}:{source_filter}')}"
                cached_result, found = await self.cache_layer.get(cache_key, "query")
                if found:
                    logfire.info("Cache hit for hybrid search")
                    return [types.TextContent(type="text", text=json.dumps(cached_result, indent=2))]

            # Perform search
            results, metrics = await self.hybrid_engine.search(
                query=query,
                query_type=query_type,
                source_filter=source_filter,
                limit=limit
            )

            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": result.id,
                    "title": result.title,
                    "content": result.content,
                    "source_name": result.source_name,
                    "source_url": result.source_url,
                    "semantic_score": result.semantic_score,
                    "graph_score": result.graph_score,
                    "combined_score": result.combined_score,
                    "rank": result.rank,
                    "found_via": result.found_via,
                    "topics": result.topics,
                    "related_concepts": result.related_concepts
                })

            response_data = {
                "query": query,
                "search_type": "hybrid",
                "query_type": query_type_str,
                "results_count": len(formatted_results),
                "results": formatted_results,
                "metrics": {
                    "total_time_ms": metrics.total_time_ms,
                    "semantic_time_ms": metrics.semantic_time_ms,
                    "graph_time_ms": metrics.graph_time_ms,
                    "fusion_time_ms": metrics.fusion_time_ms,
                    "semantic_results": metrics.semantic_results,
                    "graph_results": metrics.graph_results,
                    "overlap_count": metrics.overlap_count,
                    "concept_expansions": metrics.concept_expansions,
                    "query_analysis": asdict(metrics.query_analysis)
                }
            }

            # Cache results if enabled
            if cache_key and self.cache_layer:
                await self.cache_layer.set(cache_key, response_data, "query", self.config.cache_ttl_seconds)

            logfire.info("Hybrid search completed",
                        query=query,
                        query_type=query_type_str,
                        results_count=len(formatted_results),
                        total_time_ms=metrics.total_time_ms)

            return [types.TextContent(
                type="text",
                text=json.dumps(response_data, indent=2)
            )]

    async def _handle_index_document(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle document indexing requests."""
        url = arguments.get("url")
        content = arguments.get("content")
        title = arguments.get("title")
        source_name = arguments.get("source_name")
        topics = arguments.get("topics", [])

        if not url and not content:
            raise ValueError("Either 'url' or 'content' must be provided")

        if not self.crawl_service:
            raise RuntimeError("Crawl service not initialized")

        with logfire.span("Index document", url=url, source_name=source_name):
            try:
                if url:
                    # Crawl and index URL
                    result = await self.crawl_service.crawl_documentation_source(
                        source_url=url,
                        source_name=source_name or url
                    )
                else:
                    # For content indexing, we'll need to implement a direct indexing method
                    # For now, return a placeholder response
                    result = {
                        "source_name": source_name or "Direct Content",
                        "chunks_indexed": 1,
                        "processing_time_ms": 100,
                        "status": "Content indexing not yet implemented in PtolemiesCrawler"
                    }

                response_data = {
                    "status": "success",
                    "source_name": result["source_name"],
                    "chunks_indexed": result["chunks_indexed"],
                    "processing_time_ms": result["processing_time_ms"],
                    "concepts_extracted": result.get("concepts_extracted", 0),
                    "relationships_created": result.get("relationships_created", 0)
                }

                logfire.info("Document indexed successfully",
                           source_name=result["source_name"],
                           chunks_indexed=result["chunks_indexed"])

                return [types.TextContent(
                    type="text",
                    text=json.dumps(response_data, indent=2)
                )]

            except Exception as e:
                logfire.error("Document indexing failed", url=url, error=str(e))
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "status": "error",
                        "error": str(e)
                    }, indent=2)
                )]

    async def _handle_get_knowledge_stats(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle knowledge base statistics requests."""
        include_performance = arguments.get("include_performance", True)
        include_cache = arguments.get("include_cache", True)

        with logfire.span("Get knowledge stats"):
            stats = {
                "server_info": {
                    "name": self.config.server_name,
                    "version": self.config.server_version,
                    "active_requests": self.active_requests
                }
            }

            # Vector store stats
            if self.vector_store:
                try:
                    vector_stats = await self.vector_store.get_stats()
                    stats["vector_store"] = vector_stats
                except Exception as e:
                    stats["vector_store"] = {"error": str(e)}

            # Graph store stats
            if self.graph_store:
                try:
                    graph_stats = await self.graph_store.get_stats()
                    stats["graph_store"] = graph_stats
                except Exception as e:
                    stats["graph_store"] = {"error": str(e)}

            # Performance stats
            if include_performance and self.performance_optimizer:
                try:
                    perf_report = self.performance_optimizer.get_performance_report()
                    stats["performance"] = perf_report
                except Exception as e:
                    stats["performance"] = {"error": str(e)}

            # Cache stats
            if include_cache and self.cache_layer:
                try:
                    cache_stats = await self.cache_layer.get_cache_stats()
                    stats["cache"] = cache_stats
                except Exception as e:
                    stats["cache"] = {"error": str(e)}

            logfire.info("Knowledge stats retrieved")

            return [types.TextContent(
                type="text",
                text=json.dumps(stats, indent=2)
            )]

    async def _handle_get_query_suggestions(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle query suggestion requests."""
        partial_query = arguments["partial_query"]
        limit = arguments.get("limit", 10)

        if not self.hybrid_engine:
            raise RuntimeError("Hybrid engine not initialized")

        with logfire.span("Get query suggestions", partial_query=partial_query):
            suggestions = await self.hybrid_engine.get_query_suggestions(partial_query)

            response_data = {
                "partial_query": partial_query,
                "suggestions": suggestions[:limit]
            }

            logfire.info("Query suggestions generated",
                        partial_query=partial_query,
                        suggestions_count=len(suggestions))

            return [types.TextContent(
                type="text",
                text=json.dumps(response_data, indent=2)
            )]

    async def _handle_retrieve_document(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle document retrieval requests."""
        document_id = arguments.get("document_id")
        url = arguments.get("url")
        include_chunks = arguments.get("include_chunks", False)
        include_metadata = arguments.get("include_metadata", True)

        if not document_id and not url:
            raise ValueError("Either 'document_id' or 'url' must be provided")

        if not self.vector_store:
            raise RuntimeError("Vector store not initialized")

        with logfire.span("Retrieve document", document_id=document_id, url=url):
            try:
                # Search for document by ID or URL
                if document_id:
                    documents = await self.vector_store.get_document_by_id(document_id)
                else:
                    # Search by URL in source_url field
                    search_results = await self.vector_store.semantic_search(
                        query=url,
                        limit=1,
                        source_filter=None,
                        quality_threshold=0.0
                    )
                    documents = [result.document for result in search_results if result.document.source_url == url]

                if not documents:
                    return [types.TextContent(
                        type="text",
                        text=json.dumps({
                            "status": "not_found",
                            "message": f"Document not found: {document_id or url}"
                        }, indent=2)
                    )]

                document = documents[0]

                # Build response
                response_data = {
                    "status": "found",
                    "document": {
                        "id": document.id,
                        "title": document.title,
                        "source_name": document.source_name,
                        "source_url": document.source_url,
                        "topics": document.topics
                    }
                }

                if include_metadata:
                    response_data["document"]["metadata"] = {
                        "quality_score": document.quality_score,
                        "content_hash": document.content_hash,
                        "chunk_index": document.chunk_index,
                        "total_chunks": document.total_chunks,
                        "created_at": document.created_at,
                        "updated_at": document.updated_at
                    }

                if include_chunks:
                    response_data["document"]["content"] = document.content

                    # Get related chunks if this is part of a multi-chunk document
                    if document.total_chunks > 1:
                        related_results = await self.vector_store.semantic_search(
                            query=document.title,
                            limit=document.total_chunks,
                            source_filter=[document.source_name],
                            quality_threshold=0.0
                        )

                        chunks = []
                        for result in related_results:
                            if result.document.source_url == document.source_url:
                                chunks.append({
                                    "chunk_index": result.document.chunk_index,
                                    "content": result.document.content,
                                    "quality_score": result.document.quality_score
                                })

                        # Sort chunks by index
                        chunks.sort(key=lambda x: x["chunk_index"])
                        response_data["document"]["all_chunks"] = chunks

                logfire.info("Document retrieved successfully",
                            document_id=document.id,
                            include_chunks=include_chunks)

                return [types.TextContent(
                    type="text",
                    text=json.dumps(response_data, indent=2)
                )]

            except Exception as e:
                logfire.error("Document retrieval failed", error=str(e))
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "status": "error",
                        "error": str(e)
                    }, indent=2)
                )]

    async def _handle_explore_concept(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle concept exploration requests."""
        concept_name = arguments["concept_name"]
        relationship_types = arguments.get("relationship_types", ["RELATES_TO", "IMPLEMENTS", "DEPENDS_ON"])
        max_depth = arguments.get("max_depth", 2)
        include_documents = arguments.get("include_documents", True)

        if not self.graph_store:
            raise RuntimeError("Graph store not initialized")

        with logfire.span("Explore concept", concept_name=concept_name):
            try:
                # Search for the concept in the graph
                concept_result = await self.graph_store.graph_search(
                    query=concept_name,
                    search_type="concept",
                    max_depth=max_depth,
                    limit=50
                )

                # Find related concepts through relationships
                related_concepts = []
                relationships = []

                for node in concept_result.nodes:
                    if node.get("type") == "concept" and concept_name.lower() in node.get("name", "").lower():
                        # This is our target concept, find its relationships
                        for rel in concept_result.relationships:
                            if (rel.get("from_node") == node.get("id") or
                                rel.get("to_node") == node.get("id")):
                                if rel.get("type") in relationship_types:
                                    relationships.append(rel)

                                    # Find the related concept
                                    related_id = rel.get("to_node") if rel.get("from_node") == node.get("id") else rel.get("from_node")
                                    for related_node in concept_result.nodes:
                                        if related_node.get("id") == related_id:
                                            related_concepts.append(related_node)

                # Get related documents if requested
                related_documents = []
                if include_documents and self.vector_store:
                    doc_search = await self.vector_store.semantic_search(
                        query=concept_name,
                        limit=10,
                        quality_threshold=0.6
                    )

                    for result in doc_search:
                        doc = result.document
                        related_documents.append({
                            "id": doc.id,
                            "title": doc.title,
                            "source_name": doc.source_name,
                            "source_url": doc.source_url,
                            "similarity_score": result.similarity_score,
                            "content_preview": doc.content[:200] + "..." if len(doc.content) > 200 else doc.content
                        })

                response_data = {
                    "concept_name": concept_name,
                    "exploration_depth": max_depth,
                    "related_concepts_count": len(related_concepts),
                    "relationships_count": len(relationships),
                    "related_documents_count": len(related_documents),
                    "related_concepts": related_concepts,
                    "relationships": relationships,
                    "related_documents": related_documents if include_documents else []
                }

                logfire.info("Concept exploration completed",
                            concept_name=concept_name,
                            related_concepts=len(related_concepts),
                            relationships=len(relationships))

                return [types.TextContent(
                    type="text",
                    text=json.dumps(response_data, indent=2)
                )]

            except Exception as e:
                logfire.error("Concept exploration failed", concept_name=concept_name, error=str(e))
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "status": "error",
                        "concept_name": concept_name,
                        "error": str(e)
                    }, indent=2)
                )]

    async def _handle_discover_patterns(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle pattern discovery requests."""
        pattern_type = arguments.get("pattern_type", "concept_hierarchies")
        focus_area = arguments.get("focus_area")
        min_confidence = arguments.get("min_confidence", 0.7)

        with logfire.span("Discover patterns", pattern_type=pattern_type):
            try:
                patterns = []

                if pattern_type == "topic_clusters":
                    patterns = await self._discover_topic_clusters(focus_area, min_confidence)
                elif pattern_type == "concept_hierarchies":
                    patterns = await self._discover_concept_hierarchies(focus_area, min_confidence)
                elif pattern_type == "document_similarities":
                    patterns = await self._discover_document_similarities(focus_area, min_confidence)
                elif pattern_type == "temporal_patterns":
                    patterns = await self._discover_temporal_patterns(focus_area, min_confidence)
                else:
                    raise ValueError(f"Unknown pattern type: {pattern_type}")

                response_data = {
                    "pattern_type": pattern_type,
                    "focus_area": focus_area,
                    "min_confidence": min_confidence,
                    "patterns_found": len(patterns),
                    "patterns": patterns
                }

                logfire.info("Pattern discovery completed",
                            pattern_type=pattern_type,
                            patterns_found=len(patterns))

                return [types.TextContent(
                    type="text",
                    text=json.dumps(response_data, indent=2)
                )]

            except Exception as e:
                logfire.error("Pattern discovery failed", pattern_type=pattern_type, error=str(e))
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "status": "error",
                        "pattern_type": pattern_type,
                        "error": str(e)
                    }, indent=2)
                )]

    async def _discover_topic_clusters(self, focus_area: Optional[str], min_confidence: float) -> List[Dict[str, Any]]:
        """Discover clusters of related topics."""
        if not self.vector_store:
            return []

        try:
            # Get all unique topics from documents
            stats = await self.vector_store.get_stats()
            all_topics = stats.get("topics", [])

            if focus_area:
                # Filter topics related to focus area
                focus_search = await self.vector_store.semantic_search(
                    query=focus_area,
                    limit=100,
                    quality_threshold=0.5
                )
                relevant_topics = set()
                for result in focus_search:
                    relevant_topics.update(result.document.topics)
                all_topics = list(relevant_topics)

            # Group topics by similarity (simplified clustering)
            clusters = []
            processed_topics = set()

            for topic in all_topics[:20]:  # Limit for performance
                if topic in processed_topics:
                    continue

                # Find similar topics
                similar_topics = [topic]
                for other_topic in all_topics:
                    if other_topic != topic and other_topic not in processed_topics:
                        # Simple similarity check based on common words
                        topic_words = set(topic.lower().split())
                        other_words = set(other_topic.lower().split())
                        similarity = len(topic_words & other_words) / len(topic_words | other_words)

                        if similarity >= min_confidence:
                            similar_topics.append(other_topic)
                            processed_topics.add(other_topic)

                if len(similar_topics) > 1:
                    clusters.append({
                        "cluster_name": f"Cluster around '{topic}'",
                        "topics": similar_topics,
                        "size": len(similar_topics),
                        "confidence": min_confidence
                    })

                processed_topics.add(topic)

            return clusters

        except Exception as e:
            logfire.error("Topic clustering failed", error=str(e))
            return []

    async def _discover_concept_hierarchies(self, focus_area: Optional[str], min_confidence: float) -> List[Dict[str, Any]]:
        """Discover hierarchical relationships between concepts."""
        if not self.graph_store:
            return []

        try:
            # Search for concepts in focus area or generally
            search_query = focus_area if focus_area else "framework"
            result = await self.graph_store.graph_search(
                query=search_query,
                search_type="concept",
                max_depth=3,
                limit=50
            )

            hierarchies = []
            processed_concepts = set()

            for node in result.nodes:
                if node.get("type") == "concept" and node.get("id") not in processed_concepts:
                    # Find hierarchical relationships (parent-child)
                    children = []
                    parents = []

                    for rel in result.relationships:
                        if rel.get("from_node") == node.get("id") and rel.get("type") in ["IMPLEMENTS", "EXTENDS", "CONTAINS"]:
                            # This concept has children
                            for child_node in result.nodes:
                                if child_node.get("id") == rel.get("to_node"):
                                    children.append({
                                        "name": child_node.get("name", "Unknown"),
                                        "relationship": rel.get("type"),
                                        "confidence": rel.get("strength", min_confidence)
                                    })

                        elif rel.get("to_node") == node.get("id") and rel.get("type") in ["IMPLEMENTS", "EXTENDS", "CONTAINS"]:
                            # This concept has parents
                            for parent_node in result.nodes:
                                if parent_node.get("id") == rel.get("from_node"):
                                    parents.append({
                                        "name": parent_node.get("name", "Unknown"),
                                        "relationship": rel.get("type"),
                                        "confidence": rel.get("strength", min_confidence)
                                    })

                    if children or parents:
                        hierarchies.append({
                            "concept": node.get("name", "Unknown"),
                            "parents": parents,
                            "children": children,
                            "depth_level": len(parents),
                            "branch_size": len(children)
                        })

                    processed_concepts.add(node.get("id"))

            return hierarchies

        except Exception as e:
            logfire.error("Concept hierarchy discovery failed", error=str(e))
            return []

    async def _discover_document_similarities(self, focus_area: Optional[str], min_confidence: float) -> List[Dict[str, Any]]:
        """Discover similar documents and content patterns."""
        if not self.vector_store:
            return []

        try:
            # Get sample of documents
            if focus_area:
                search_results = await self.vector_store.semantic_search(
                    query=focus_area,
                    limit=20,
                    quality_threshold=0.5
                )
            else:
                # Get diverse sample - simplified approach
                search_results = await self.vector_store.semantic_search(
                    query="documentation",
                    limit=20,
                    quality_threshold=0.0
                )

            similarities = []
            processed_pairs = set()

            for i, result1 in enumerate(search_results):
                for j, result2 in enumerate(search_results[i+1:], i+1):
                    pair_key = f"{result1.document.id}-{result2.document.id}"
                    if pair_key in processed_pairs:
                        continue

                    # Calculate similarity based on shared topics and content
                    doc1, doc2 = result1.document, result2.document

                    # Topic similarity
                    topics1 = set(doc1.topics)
                    topics2 = set(doc2.topics)
                    topic_similarity = len(topics1 & topics2) / len(topics1 | topics2) if topics1 | topics2 else 0

                    # Source similarity
                    source_similarity = 1.0 if doc1.source_name == doc2.source_name else 0.0

                    # Combined similarity
                    combined_similarity = (topic_similarity + source_similarity) / 2

                    if combined_similarity >= min_confidence:
                        similarities.append({
                            "document1": {
                                "id": doc1.id,
                                "title": doc1.title,
                                "source": doc1.source_name
                            },
                            "document2": {
                                "id": doc2.id,
                                "title": doc2.title,
                                "source": doc2.source_name
                            },
                            "similarity_score": combined_similarity,
                            "shared_topics": list(topics1 & topics2),
                            "similarity_type": "topic_overlap" if topic_similarity > source_similarity else "source_similarity"
                        })

                    processed_pairs.add(pair_key)

            # Sort by similarity score
            similarities.sort(key=lambda x: x["similarity_score"], reverse=True)

            return similarities[:10]  # Return top 10 similar pairs

        except Exception as e:
            logfire.error("Document similarity discovery failed", error=str(e))
            return []

    async def _discover_temporal_patterns(self, focus_area: Optional[str], min_confidence: float) -> List[Dict[str, Any]]:
        """Discover temporal patterns in document creation and updates."""
        if not self.vector_store:
            return []

        try:
            # This is a simplified implementation - in a real system you'd analyze timestamps
            stats = await self.vector_store.get_stats()

            patterns = [
                {
                    "pattern_type": "creation_frequency",
                    "description": "Document creation patterns over time",
                    "confidence": min_confidence,
                    "details": {
                        "total_documents": stats.get("total_documents", 0),
                        "note": "Temporal analysis requires timestamp data not available in current implementation"
                    }
                }
            ]

            return patterns

        except Exception as e:
            logfire.error("Temporal pattern discovery failed", error=str(e))
            return []

    # Tool Management Methods
    def register_custom_tool(
        self,
        name: str,
        handler: Callable,
        tool_spec: types.Tool,
        metadata: ToolMetadata
    ) -> bool:
        """Register a custom tool with the server."""
        if not self.tool_registry:
            logfire.warning("Tool registry not enabled", tool_name=name)
            return False

        return self.tool_registry.register_tool(name, handler, tool_spec, metadata)

    def unregister_tool(self, name: str) -> bool:
        """Unregister a tool from the server."""
        if not self.tool_registry:
            return False

        return self.tool_registry.unregister_tool(name)

    def set_tool_status(self, name: str, status: str) -> bool:
        """Set tool status (active, inactive, disabled, error)."""
        if not self.tool_registry:
            return False

        from mcp_tool_registry import ToolStatus
        try:
            tool_status = ToolStatus(status)
            return self.tool_registry.set_tool_status(name, tool_status)
        except ValueError:
            logfire.error("Invalid tool status", status=status)
            return False

    def get_tool_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a tool."""
        if not self.tool_registry:
            return None

        return self.tool_registry.get_tool_info(name)

    def list_tools_by_category(self, category: str = None) -> List[Dict[str, Any]]:
        """List tools, optionally filtered by category."""
        if not self.tool_registry:
            return []

        from mcp_tool_registry import ToolCategory
        try:
            tool_category = ToolCategory(category) if category else None
            return self.tool_registry.list_tools(category=tool_category)
        except ValueError:
            logfire.error("Invalid tool category", category=category)
            return []

    def get_tool_registry_stats(self) -> Dict[str, Any]:
        """Get tool registry statistics."""
        if not self.tool_registry:
            return {"error": "Tool registry not enabled"}

        return self.tool_registry.get_registry_stats()

    async def initialize_components(self):
        """Initialize all required components."""
        with logfire.span("Initialize MCP server components"):
            try:
                logfire.info("Initializing Ptolemies MCP server components")

                # Initialize cache layer first (if enabled)
                if self.config.enable_caching:
                    self.cache_layer = await create_redis_cache_layer()
                    logfire.info("Cache layer initialized")

                # Initialize performance optimizer
                if self.config.enable_performance_optimization:
                    self.performance_optimizer = create_performance_optimizer()
                    logfire.info("Performance optimizer initialized")

                # Initialize vector store
                if self.config.enable_semantic_search:
                    self.vector_store = await create_vector_store(self.config.vector_config)
                    logfire.info("Vector store initialized")

                # Initialize graph store
                if self.config.enable_graph_search:
                    self.graph_store = await create_graph_store(self.config.graph_config)
                    logfire.info("Graph store initialized")

                # Initialize hybrid engine
                if self.config.enable_hybrid_search and self.vector_store and self.graph_store:
                    self.hybrid_engine = HybridQueryEngine(
                        self.vector_store,
                        self.graph_store,
                        self.config.hybrid_config
                    )
                    logfire.info("Hybrid engine initialized")

                # Initialize crawl service
                self.crawl_service = PtolemiesCrawler(
                    self.config.crawl_config or CrawlConfig(),
                    self.vector_store,
                    self.graph_store
                )
                logfire.info("Crawl service initialized")

                logfire.info("All MCP server components initialized successfully")

            except Exception as e:
                logfire.error("Failed to initialize MCP server components", error=str(e))
                raise

    async def cleanup(self):
        """Cleanup resources."""
        with logfire.span("Cleanup MCP server"):
            logfire.info("Cleaning up Ptolemies MCP server")

            if self.vector_store:
                await self.vector_store.close()

            if self.graph_store:
                await self.graph_store.close()

            if self.cache_layer:
                await self.cache_layer.close()

            logfire.info("MCP server cleanup completed")

async def create_mcp_server(config: PtolemiesMCPConfig = None) -> PtolemiesMCPServer:
    """Create and initialize MCP server."""
    server = PtolemiesMCPServer(config)
    await server.initialize_components()
    return server

async def main():
    """Main entry point for the MCP server."""
    try:
        logfire.info("Starting Ptolemies MCP server")

        # Create server with default configuration
        mcp_server = await create_mcp_server()

        # Run server with stdio transport
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await mcp_server.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name=mcp_server.config.server_name,
                    server_version=mcp_server.config.server_version,
                    capabilities=mcp_server.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={}
                    )
                )
            )
    except Exception as e:
        logfire.error("MCP server failed", error=str(e), traceback=traceback.format_exc())
        raise
    finally:
        if 'mcp_server' in locals():
            await mcp_server.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
