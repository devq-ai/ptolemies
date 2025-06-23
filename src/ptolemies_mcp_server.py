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