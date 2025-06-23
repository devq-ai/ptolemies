#!/usr/bin/env python3
"""
Test suite for Ptolemies MCP Server
"""

import pytest
import asyncio
import json
import os
import sys
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path

# Set logfire config for testing
os.environ['LOGFIRE_IGNORE_NO_CONFIG'] = '1'

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ptolemies_mcp_server import (
    PtolemiesMCPServer,
    PtolemiesMCPConfig,
    create_mcp_server
)
from surrealdb_integration import VectorStoreConfig
from neo4j_integration import Neo4jConfig
from hybrid_query_engine import HybridQueryConfig, QueryType
from performance_optimizer import PerformanceConfig
from redis_cache_layer import RedisCacheConfig
from crawl4ai_integration import CrawlConfig

import mcp.types as types

class TestPtolemiesMCPConfig:
    """Test MCP server configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = PtolemiesMCPConfig()
        
        assert config.server_name == "ptolemies-knowledge"
        assert config.server_version == "1.0.0"
        assert config.max_concurrent_requests == 10
        assert config.default_search_limit == 50
        assert config.enable_semantic_search is True
        assert config.enable_graph_search is True
        assert config.enable_hybrid_search is True
        assert config.enable_concept_expansion is True
        assert config.enable_caching is True
        assert config.enable_performance_optimization is True
        assert config.cache_search_results is True
        assert config.cache_ttl_seconds == 3600
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = PtolemiesMCPConfig(
            server_name="custom-server",
            server_version="2.0.0",
            max_concurrent_requests=20,
            default_search_limit=100,
            enable_caching=False
        )
        
        assert config.server_name == "custom-server"
        assert config.server_version == "2.0.0"
        assert config.max_concurrent_requests == 20
        assert config.default_search_limit == 100
        assert config.enable_caching is False

class TestPtolemiesMCPServer:
    """Test MCP server functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Test configuration with mocked components."""
        return PtolemiesMCPConfig(
            enable_caching=False,  # Disable caching for simpler testing
            enable_performance_optimization=False
        )
    
    @pytest.fixture
    def mcp_server(self, mock_config):
        """Test MCP server instance."""
        return PtolemiesMCPServer(mock_config)
    
    def test_server_initialization(self, mcp_server):
        """Test server initialization."""
        assert mcp_server.config.server_name == "ptolemies-knowledge"
        assert mcp_server.server is not None
        assert mcp_server.active_requests == 0
        assert mcp_server.request_semaphore._value == 10
    
    def test_tools_configuration_all_enabled(self):
        """Test tool configuration with all features enabled."""
        config = PtolemiesMCPConfig()
        server = PtolemiesMCPServer(config)
        
        assert config.enable_semantic_search is True
        assert config.enable_graph_search is True
        assert config.enable_hybrid_search is True
        
        # Test that server is properly configured
        assert server.config.enable_semantic_search is True
        assert server.config.enable_graph_search is True
        assert server.config.enable_hybrid_search is True
    
    def test_tools_configuration_selective_features(self):
        """Test tool configuration with selective features enabled."""
        config = PtolemiesMCPConfig(
            enable_semantic_search=True,
            enable_graph_search=False,
            enable_hybrid_search=False
        )
        server = PtolemiesMCPServer(config)
        
        assert server.config.enable_semantic_search is True
        assert server.config.enable_graph_search is False
        assert server.config.enable_hybrid_search is False
    
    def test_mcp_server_setup(self):
        """Test MCP server basic setup."""
        server = PtolemiesMCPServer()
        
        # Test basic properties
        assert hasattr(server, 'server')
        assert hasattr(server, 'config')
        assert hasattr(server, 'request_semaphore')
        
        # Test default configuration
        assert server.config.server_name == "ptolemies-knowledge"
        assert server.config.server_version == "1.0.0"

class TestMCPToolHandlers:
    """Test MCP tool handlers."""
    
    @pytest.fixture
    def mcp_server_with_mocks(self):
        """MCP server with mocked components."""
        config = PtolemiesMCPConfig(enable_caching=False, enable_performance_optimization=False)
        server = PtolemiesMCPServer(config)
        
        # Mock components
        server.vector_store = AsyncMock()
        server.graph_store = AsyncMock()
        server.hybrid_engine = AsyncMock()
        server.crawl_service = AsyncMock()
        server.cache_layer = None
        server.performance_optimizer = None
        
        return server
    
    @pytest.mark.asyncio
    async def test_handle_semantic_search_success(self, mcp_server_with_mocks):
        """Test successful semantic search handling."""
        server = mcp_server_with_mocks
        
        # Mock search results
        mock_doc = Mock()
        mock_doc.id = "doc_1"
        mock_doc.title = "Test Document"
        mock_doc.content = "Test content"
        mock_doc.source_name = "Test Source"
        mock_doc.source_url = "https://test.com"
        mock_doc.quality_score = 0.9
        mock_doc.topics = ["test"]
        mock_doc.chunk_index = 0
        mock_doc.total_chunks = 1
        
        mock_result = Mock()
        mock_result.document = mock_doc
        mock_result.similarity_score = 0.85
        
        server.vector_store.semantic_search.return_value = [mock_result]
        
        arguments = {
            "query": "test query",
            "limit": 10
        }
        
        result = await server._handle_semantic_search(arguments)
        
        assert len(result) == 1
        assert isinstance(result[0], types.TextContent)
        
        # Parse the JSON response
        response_data = json.loads(result[0].text)
        assert response_data["query"] == "test query"
        assert response_data["search_type"] == "semantic"
        assert response_data["results_count"] == 1
        assert len(response_data["results"]) == 1
        
        # Check result format
        search_result = response_data["results"][0]
        assert search_result["id"] == "doc_1"
        assert search_result["title"] == "Test Document"
        assert search_result["similarity_score"] == 0.85
    
    @pytest.mark.asyncio
    async def test_handle_semantic_search_no_vector_store(self, mcp_server_with_mocks):
        """Test semantic search with no vector store."""
        server = mcp_server_with_mocks
        server.vector_store = None
        
        arguments = {"query": "test query"}
        
        with pytest.raises(RuntimeError, match="Vector store not initialized"):
            await server._handle_semantic_search(arguments)
    
    @pytest.mark.asyncio
    async def test_handle_graph_search_success(self, mcp_server_with_mocks):
        """Test successful graph search handling."""
        server = mcp_server_with_mocks
        
        # Mock graph search results
        mock_graph_result = Mock()
        mock_graph_result.nodes = [{"id": "concept_1", "name": "Test Concept"}]
        mock_graph_result.relationships = [{"from": "concept_1", "to": "concept_2", "type": "RELATED_TO"}]
        mock_graph_result.paths = []
        mock_graph_result.query_metadata = {"search_time_ms": 50.0}
        
        server.graph_store.graph_search.return_value = mock_graph_result
        
        arguments = {
            "query": "test concept",
            "search_type": "concept",
            "max_depth": 2,
            "limit": 10
        }
        
        result = await server._handle_graph_search(arguments)
        
        assert len(result) == 1
        response_data = json.loads(result[0].text)
        
        assert response_data["query"] == "test concept"
        assert response_data["search_type"] == "graph"
        assert response_data["graph_search_type"] == "concept"
        assert response_data["nodes_count"] == 1
        assert response_data["relationships_count"] == 1
    
    @pytest.mark.asyncio
    async def test_handle_hybrid_search_success(self, mcp_server_with_mocks):
        """Test successful hybrid search handling."""
        server = mcp_server_with_mocks
        
        # Mock hybrid search results
        mock_result = Mock()
        mock_result.id = "hybrid_1"
        mock_result.title = "Hybrid Result"
        mock_result.content = "Hybrid content"
        mock_result.source_name = "Hybrid Source"
        mock_result.source_url = "https://hybrid.com"
        mock_result.semantic_score = 0.8
        mock_result.graph_score = 0.7
        mock_result.combined_score = 0.75
        mock_result.rank = 1
        mock_result.found_via = ["semantic_search", "graph_search"]
        mock_result.topics = ["hybrid"]
        mock_result.related_concepts = ["concept1"]
        
        mock_metrics = Mock()
        mock_metrics.total_time_ms = 150.0
        mock_metrics.semantic_time_ms = 80.0
        mock_metrics.graph_time_ms = 60.0
        mock_metrics.fusion_time_ms = 10.0
        mock_metrics.semantic_results = 5
        mock_metrics.graph_results = 3
        mock_metrics.overlap_count = 2
        mock_metrics.concept_expansions = 1
        # Create a proper dataclass-like object for query_analysis
        from hybrid_query_engine import QueryAnalysis
        mock_metrics.query_analysis = QueryAnalysis(
            query_type="general",
            detected_concepts=["test"],
            suggested_expansions=[],
            complexity_score=0.5,
            semantic_weight=0.6,
            graph_weight=0.4
        )
        
        server.hybrid_engine.search.return_value = ([mock_result], mock_metrics)
        
        arguments = {
            "query": "hybrid test",
            "query_type": "hybrid_balanced",
            "limit": 10
        }
        
        result = await server._handle_hybrid_search(arguments)
        
        assert len(result) == 1
        response_data = json.loads(result[0].text)
        
        assert response_data["query"] == "hybrid test"
        assert response_data["search_type"] == "hybrid"
        assert response_data["query_type"] == "hybrid_balanced"
        assert response_data["results_count"] == 1
        assert "metrics" in response_data
        
        # Check metrics
        metrics = response_data["metrics"]
        assert metrics["total_time_ms"] == 150.0
        assert metrics["semantic_results"] == 5
        assert metrics["graph_results"] == 3
    
    @pytest.mark.asyncio
    async def test_handle_index_document_url(self, mcp_server_with_mocks):
        """Test document indexing from URL."""
        server = mcp_server_with_mocks
        
        # Mock crawl service result
        mock_crawl_result = {
            "source_name": "Test Site",
            "chunks_indexed": 5,
            "processing_time_ms": 2000,
            "concepts_extracted": 10,
            "relationships_created": 15
        }
        
        server.crawl_service.crawl_documentation_source.return_value = mock_crawl_result
        
        arguments = {
            "url": "https://test.com",
            "source_name": "Test Site",
            "topics": ["testing"]
        }
        
        result = await server._handle_index_document(arguments)
        
        assert len(result) == 1
        response_data = json.loads(result[0].text)
        
        assert response_data["status"] == "success"
        assert response_data["source_name"] == "Test Site"
        assert response_data["chunks_indexed"] == 5
        assert response_data["concepts_extracted"] == 10
    
    @pytest.mark.asyncio
    async def test_handle_index_document_content(self, mcp_server_with_mocks):
        """Test document indexing from content."""
        server = mcp_server_with_mocks
        
        arguments = {
            "content": "This is test content to index",
            "title": "Test Document",
            "source_name": "Direct Content",
            "topics": ["content"]
        }
        
        result = await server._handle_index_document(arguments)
        
        assert len(result) == 1
        response_data = json.loads(result[0].text)
        
        assert response_data["status"] == "success"
        assert response_data["chunks_indexed"] == 1
        # Since we return a placeholder response for content indexing
        assert "source_name" in response_data
    
    @pytest.mark.asyncio
    async def test_handle_index_document_missing_params(self, mcp_server_with_mocks):
        """Test document indexing with missing parameters."""
        server = mcp_server_with_mocks
        
        arguments = {}  # No url or content
        
        with pytest.raises(ValueError, match="Either 'url' or 'content' must be provided"):
            await server._handle_index_document(arguments)
    
    @pytest.mark.asyncio
    async def test_handle_get_knowledge_stats(self, mcp_server_with_mocks):
        """Test knowledge base statistics retrieval."""
        server = mcp_server_with_mocks
        
        # Mock component stats
        server.vector_store.get_stats.return_value = {"total_documents": 100}
        server.graph_store.get_stats.return_value = {"total_nodes": 50, "total_relationships": 75}
        
        arguments = {
            "include_performance": False,
            "include_cache": False
        }
        
        result = await server._handle_get_knowledge_stats(arguments)
        
        assert len(result) == 1
        response_data = json.loads(result[0].text)
        
        assert "server_info" in response_data
        assert "vector_store" in response_data
        assert "graph_store" in response_data
        
        # Check server info
        server_info = response_data["server_info"]
        assert server_info["name"] == "ptolemies-knowledge"
        assert "active_requests" in server_info
        
        # Check component stats
        assert response_data["vector_store"]["total_documents"] == 100
        assert response_data["graph_store"]["total_nodes"] == 50
    
    @pytest.mark.asyncio
    async def test_handle_get_query_suggestions(self, mcp_server_with_mocks):
        """Test query suggestions retrieval."""
        server = mcp_server_with_mocks
        
        # Mock suggestions
        mock_suggestions = [
            "FastAPI authentication",
            "FastAPI middleware",
            "FastAPI security"
        ]
        
        server.hybrid_engine.get_query_suggestions.return_value = mock_suggestions
        
        arguments = {
            "partial_query": "FastAPI",
            "limit": 5
        }
        
        result = await server._handle_get_query_suggestions(arguments)
        
        assert len(result) == 1
        response_data = json.loads(result[0].text)
        
        assert response_data["partial_query"] == "FastAPI"
        assert len(response_data["suggestions"]) == 3
        assert "FastAPI authentication" in response_data["suggestions"]

class TestMCPServerLifecycle:
    """Test MCP server lifecycle management."""
    
    @pytest.mark.asyncio
    async def test_initialize_components_success(self):
        """Test successful component initialization."""
        config = PtolemiesMCPConfig(
            enable_caching=False,
            enable_performance_optimization=False
        )
        
        server = PtolemiesMCPServer(config)
        
        # Mock the create functions
        with patch('ptolemies_mcp_server.create_vector_store') as mock_create_vector, \
             patch('ptolemies_mcp_server.create_graph_store') as mock_create_graph, \
             patch('ptolemies_mcp_server.create_performance_optimizer') as mock_create_perf, \
             patch('ptolemies_mcp_server.PtolemiesCrawler') as mock_crawl_service:
            
            mock_create_vector.return_value = AsyncMock()
            mock_create_graph.return_value = AsyncMock()
            mock_create_perf.return_value = Mock()
            mock_crawl_service.return_value = AsyncMock()
            
            await server.initialize_components()
            
            assert server.vector_store is not None
            assert server.graph_store is not None
            assert server.hybrid_engine is not None
            assert server.crawl_service is not None
    
    @pytest.mark.asyncio
    async def test_cleanup_components(self):
        """Test component cleanup."""
        config = PtolemiesMCPConfig()
        server = PtolemiesMCPServer(config)
        
        # Mock components
        server.vector_store = AsyncMock()
        server.graph_store = AsyncMock()
        server.cache_layer = AsyncMock()
        
        await server.cleanup()
        
        server.vector_store.close.assert_called_once()
        server.graph_store.close.assert_called_once()
        server.cache_layer.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_mcp_server_function(self):
        """Test the create_mcp_server utility function."""
        config = PtolemiesMCPConfig(
            enable_caching=False,
            enable_performance_optimization=False
        )
        
        with patch('ptolemies_mcp_server.PtolemiesMCPServer.initialize_components') as mock_init:
            mock_init.return_value = None
            
            server = await create_mcp_server(config)
            
            assert isinstance(server, PtolemiesMCPServer)
            assert server.config == config
            mock_init.assert_called_once()

class TestMCPServerConcurrency:
    """Test MCP server concurrency handling."""
    
    @pytest.mark.asyncio
    async def test_request_semaphore_limits(self):
        """Test request concurrency limiting."""
        config = PtolemiesMCPConfig(max_concurrent_requests=2)
        server = PtolemiesMCPServer(config)
        
        # Mock components
        server.vector_store = AsyncMock()
        server.vector_store.semantic_search.return_value = []
        
        async def slow_search(*args, **kwargs):
            await asyncio.sleep(0.1)
            return []
        
        server.vector_store.semantic_search = slow_search
        
        # Start multiple concurrent requests
        tasks = []
        for i in range(5):  # More than the limit of 2
            task = asyncio.create_task(
                server._handle_semantic_search({"query": f"test {i}"})
            )
            tasks.append(task)
        
        # Wait a short time and check active requests
        await asyncio.sleep(0.05)
        assert server.active_requests <= 2  # Should be limited by semaphore
        
        # Wait for all to complete
        await asyncio.gather(*tasks)
        assert server.active_requests == 0
    
    @pytest.mark.asyncio
    async def test_active_request_tracking(self):
        """Test active request counting."""
        config = PtolemiesMCPConfig(enable_caching=False, enable_performance_optimization=False)
        server = PtolemiesMCPServer(config)
        
        # Mock components
        server.vector_store = AsyncMock()
        server.vector_store.semantic_search.return_value = []
        
        assert server.active_requests == 0
        
        # Simulate request handling
        await server._handle_semantic_search({"query": "test"})
        
        # Should be back to 0 after completion
        assert server.active_requests == 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])