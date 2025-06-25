#!/usr/bin/env python3
"""
Comprehensive Test Suite for Enhanced Ptolemies MCP Server Handlers
Tests all core handlers including search, retrieve, concept exploration, and pattern discovery.
"""

import pytest
import asyncio
import os
import sys
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path

# Set logfire config for testing
os.environ['LOGFIRE_IGNORE_NO_CONFIG'] = '1'

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Test imports
from ptolemies_mcp_server import PtolemiesMCPServer, PtolemiesMCPConfig
from surrealdb_integration import SearchResult, DocumentChunk
from neo4j_integration import GraphSearchResult, DocumentNode, ConceptNode
from hybrid_query_engine import HybridSearchResult, HybridQueryMetrics, QueryAnalysis, QueryType
import mcp.types as types

class TestPtolemiesMCPHandlers:
    """Test suite for all Ptolemies MCP server handlers."""

    @pytest.fixture
    def mock_vector_store(self):
        """Mock SurrealDB vector store."""
        store = AsyncMock()

        # Mock search results
        doc = DocumentChunk(
            id="test-doc-1",
            content="FastAPI is a modern web framework for Python",
            title="FastAPI Guide",
            source_name="FastAPI Docs",
            source_url="https://fastapi.tiangolo.com",
            topics=["fastapi", "python", "web"],
            quality_score=0.9,
            chunk_index=0,
            total_chunks=1,
            content_hash="abc123"
        )

        search_result = SearchResult(document=doc, similarity_score=0.95)
        store.semantic_search.return_value = [search_result]
        store.get_document_by_id.return_value = [doc]
        store.get_stats.return_value = {
            "total_documents": 150,
            "total_chunks": 300,
            "topics": ["fastapi", "python", "web", "database", "api"]
        }

        return store

    @pytest.fixture
    def mock_graph_store(self):
        """Mock Neo4j graph store."""
        store = AsyncMock()

        # Mock graph search results
        nodes = [
            {"id": "concept-1", "type": "concept", "name": "FastAPI", "category": "Framework"},
            {"id": "concept-2", "type": "concept", "name": "Python", "category": "Language"}
        ]

        relationships = [
            {
                "id": "rel-1",
                "from_node": "concept-1",
                "to_node": "concept-2",
                "type": "IMPLEMENTS",
                "strength": 0.9
            }
        ]

        result = GraphSearchResult(
            nodes=nodes,
            relationships=relationships,
            paths=[],
            query_metadata={"execution_time": 0.05}
        )

        store.graph_search.return_value = result
        store.get_stats.return_value = {
            "node_count": 77,
            "relationship_count": 150,
            "concept_count": 50
        }

        return store

    @pytest.fixture
    def mock_hybrid_engine(self):
        """Mock hybrid query engine."""
        engine = AsyncMock()

        # Mock hybrid search result
        hybrid_result = HybridSearchResult(
            id="hybrid-1",
            title="FastAPI Authentication",
            content="How to implement authentication in FastAPI",
            source_name="FastAPI Docs",
            source_url="https://fastapi.tiangolo.com/auth",
            semantic_score=0.9,
            graph_score=0.8,
            combined_score=0.85,
            rank=1,
            found_via="hybrid",
            topics=["fastapi", "auth"],
            related_concepts=["security", "oauth"]
        )

        metrics = HybridQueryMetrics(
            total_time_ms=150,
            semantic_time_ms=80,
            graph_time_ms=70,
            fusion_time_ms=10,
            semantic_results=5,
            graph_results=3,
            overlap_count=2,
            concept_expansions=1,
            query_analysis=QueryAnalysis(
                query_type=QueryType.HYBRID_BALANCED,
                concepts_detected=["fastapi", "authentication"],
                complexity_score=0.7,
                semantic_confidence=0.9,
                graph_confidence=0.8
            )
        )

        engine.search.return_value = ([hybrid_result], metrics)
        engine.get_query_suggestions.return_value = [
            "FastAPI authentication",
            "FastAPI OAuth",
            "FastAPI security"
        ]

        return engine

    @pytest.fixture
    def mock_crawl_service(self):
        """Mock crawl service."""
        service = AsyncMock()
        service.crawl_documentation_source.return_value = {
            "source_name": "Test Docs",
            "chunks_indexed": 5,
            "processing_time_ms": 1500,
            "concepts_extracted": 3,
            "relationships_created": 2
        }
        return service

    @pytest.fixture
    def mock_cache_layer(self):
        """Mock Redis cache layer."""
        cache = AsyncMock()
        cache.get.return_value = (None, False)  # No cache hit by default
        cache.set.return_value = True
        cache.get_cache_stats.return_value = {
            "hits": 10,
            "misses": 5,
            "hit_rate": 0.67
        }
        return cache

    @pytest.fixture
    def mcp_server(self, mock_vector_store, mock_graph_store, mock_hybrid_engine,
                   mock_crawl_service, mock_cache_layer):
        """Create MCP server with mocked components."""
        config = PtolemiesMCPConfig(
            enable_semantic_search=True,
            enable_graph_search=True,
            enable_hybrid_search=True,
            enable_caching=True
        )

        server = PtolemiesMCPServer(config)

        # Inject mocked components
        server.vector_store = mock_vector_store
        server.graph_store = mock_graph_store
        server.hybrid_engine = mock_hybrid_engine
        server.crawl_service = mock_crawl_service
        server.cache_layer = mock_cache_layer

        return server

    @pytest.mark.asyncio
    async def test_semantic_search_handler(self, mcp_server):
        """Test semantic search handler."""
        arguments = {
            "query": "FastAPI authentication",
            "limit": 10,
            "quality_threshold": 0.7
        }

        result = await mcp_server._handle_semantic_search(arguments)

        assert len(result) == 1
        assert isinstance(result[0], types.TextContent)

        response_data = json.loads(result[0].text)
        assert response_data["query"] == "FastAPI authentication"
        assert response_data["search_type"] == "semantic"
        assert response_data["results_count"] == 1
        assert len(response_data["results"]) == 1

        # Verify result structure
        doc_result = response_data["results"][0]
        assert doc_result["title"] == "FastAPI Guide"
        assert doc_result["similarity_score"] == 0.95
        assert "fastapi" in doc_result["topics"]

    @pytest.mark.asyncio
    async def test_graph_search_handler(self, mcp_server):
        """Test graph search handler."""
        arguments = {
            "query": "FastAPI",
            "search_type": "concept",
            "max_depth": 2,
            "limit": 20
        }

        result = await mcp_server._handle_graph_search(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["query"] == "FastAPI"
        assert response_data["search_type"] == "graph"
        assert response_data["nodes_count"] == 2
        assert response_data["relationships_count"] == 1
        assert len(response_data["nodes"]) == 2
        assert len(response_data["relationships"]) == 1

    @pytest.mark.asyncio
    async def test_hybrid_search_handler(self, mcp_server):
        """Test hybrid search handler."""
        arguments = {
            "query": "FastAPI authentication",
            "query_type": "hybrid_balanced",
            "limit": 10
        }

        result = await mcp_server._handle_hybrid_search(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["query"] == "FastAPI authentication"
        assert response_data["search_type"] == "hybrid"
        assert response_data["query_type"] == "hybrid_balanced"
        assert response_data["results_count"] == 1

        # Check metrics
        metrics = response_data["metrics"]
        assert metrics["total_time_ms"] == 150
        assert metrics["semantic_results"] == 5
        assert metrics["graph_results"] == 3

    @pytest.mark.asyncio
    async def test_retrieve_document_handler(self, mcp_server):
        """Test document retrieval handler."""
        arguments = {
            "document_id": "test-doc-1",
            "include_chunks": True,
            "include_metadata": True
        }

        result = await mcp_server._handle_retrieve_document(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["status"] == "found"
        assert response_data["document"]["id"] == "test-doc-1"
        assert response_data["document"]["title"] == "FastAPI Guide"
        assert "metadata" in response_data["document"]
        assert "content" in response_data["document"]

    @pytest.mark.asyncio
    async def test_retrieve_document_by_url(self, mcp_server):
        """Test document retrieval by URL."""
        arguments = {
            "url": "https://fastapi.tiangolo.com",
            "include_chunks": False,
            "include_metadata": True
        }

        result = await mcp_server._handle_retrieve_document(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["status"] == "found"
        assert response_data["document"]["source_url"] == "https://fastapi.tiangolo.com"
        assert "content" not in response_data["document"]  # include_chunks=False

    @pytest.mark.asyncio
    async def test_retrieve_document_not_found(self, mcp_server):
        """Test document retrieval when document not found."""
        # Mock empty search result
        mcp_server.vector_store.get_document_by_id.return_value = []

        arguments = {
            "document_id": "nonexistent-doc"
        }

        result = await mcp_server._handle_retrieve_document(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["status"] == "not_found"
        assert "nonexistent-doc" in response_data["message"]

    @pytest.mark.asyncio
    async def test_explore_concept_handler(self, mcp_server):
        """Test concept exploration handler."""
        arguments = {
            "concept_name": "FastAPI",
            "relationship_types": ["IMPLEMENTS", "RELATES_TO"],
            "max_depth": 2,
            "include_documents": True
        }

        result = await mcp_server._handle_explore_concept(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["concept_name"] == "FastAPI"
        assert response_data["exploration_depth"] == 2
        assert "related_concepts_count" in response_data
        assert "relationships_count" in response_data
        assert "related_documents" in response_data

    @pytest.mark.asyncio
    async def test_discover_patterns_topic_clusters(self, mcp_server):
        """Test pattern discovery for topic clusters."""
        arguments = {
            "pattern_type": "topic_clusters",
            "focus_area": "web development",
            "min_confidence": 0.7
        }

        result = await mcp_server._handle_discover_patterns(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["pattern_type"] == "topic_clusters"
        assert response_data["focus_area"] == "web development"
        assert response_data["min_confidence"] == 0.7
        assert "patterns" in response_data

    @pytest.mark.asyncio
    async def test_discover_patterns_concept_hierarchies(self, mcp_server):
        """Test pattern discovery for concept hierarchies."""
        arguments = {
            "pattern_type": "concept_hierarchies",
            "min_confidence": 0.8
        }

        result = await mcp_server._handle_discover_patterns(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["pattern_type"] == "concept_hierarchies"
        assert "patterns" in response_data

    @pytest.mark.asyncio
    async def test_discover_patterns_document_similarities(self, mcp_server):
        """Test pattern discovery for document similarities."""
        arguments = {
            "pattern_type": "document_similarities",
            "focus_area": "API documentation",
            "min_confidence": 0.6
        }

        result = await mcp_server._handle_discover_patterns(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["pattern_type"] == "document_similarities"
        assert "patterns" in response_data

    @pytest.mark.asyncio
    async def test_index_document_handler_url(self, mcp_server):
        """Test document indexing with URL."""
        arguments = {
            "url": "https://example.com/docs",
            "source_name": "Example Docs",
            "topics": ["example", "documentation"]
        }

        result = await mcp_server._handle_index_document(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["status"] == "success"
        assert response_data["source_name"] == "Test Docs"
        assert response_data["chunks_indexed"] == 5

    @pytest.mark.asyncio
    async def test_index_document_handler_content(self, mcp_server):
        """Test document indexing with direct content."""
        arguments = {
            "content": "This is test content for indexing",
            "title": "Test Document",
            "source_name": "Direct Content",
            "topics": ["test", "content"]
        }

        result = await mcp_server._handle_index_document(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        # Should handle content indexing (currently returns placeholder)
        assert "status" in response_data

    @pytest.mark.asyncio
    async def test_get_knowledge_stats_handler(self, mcp_server):
        """Test knowledge base statistics handler."""
        arguments = {
            "include_performance": True,
            "include_cache": True
        }

        result = await mcp_server._handle_get_knowledge_stats(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert "server_info" in response_data
        assert "vector_store" in response_data
        assert "graph_store" in response_data
        assert "cache" in response_data

        # Check server info
        server_info = response_data["server_info"]
        assert server_info["name"] == "ptolemies-knowledge"
        assert server_info["version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_get_query_suggestions_handler(self, mcp_server):
        """Test query suggestions handler."""
        arguments = {
            "partial_query": "FastAPI",
            "limit": 5
        }

        result = await mcp_server._handle_get_query_suggestions(arguments)

        assert len(result) == 1
        response_data = json.loads(result[0].text)

        assert response_data["partial_query"] == "FastAPI"
        assert len(response_data["suggestions"]) == 3
        assert "FastAPI authentication" in response_data["suggestions"]

    @pytest.mark.asyncio
    async def test_error_handling_missing_arguments(self, mcp_server):
        """Test error handling when required arguments are missing."""
        # Test semantic search without query
        with pytest.raises(KeyError):
            await mcp_server._handle_semantic_search({})

        # Test retrieve document without ID or URL
        result = await mcp_server._handle_retrieve_document({})
        response_data = json.loads(result[0].text)
        assert "error" in response_data["error"].lower()

    @pytest.mark.asyncio
    async def test_error_handling_component_not_initialized(self):
        """Test error handling when components are not initialized."""
        config = PtolemiesMCPConfig()
        server = PtolemiesMCPServer(config)

        # Test with uninitialized vector store
        arguments = {"query": "test"}

        with pytest.raises(RuntimeError, match="Vector store not initialized"):
            await server._handle_semantic_search(arguments)

        with pytest.raises(RuntimeError, match="Graph store not initialized"):
            await server._handle_graph_search(arguments)

        with pytest.raises(RuntimeError, match="Hybrid engine not initialized"):
            await server._handle_hybrid_search(arguments)

    @pytest.mark.asyncio
    async def test_caching_functionality(self, mcp_server):
        """Test caching functionality in search handlers."""
        # Configure cache to return a hit
        cached_result = {
            "query": "FastAPI",
            "search_type": "semantic",
            "results_count": 1,
            "results": [{"cached": True}]
        }
        mcp_server.cache_layer.get.return_value = (cached_result, True)

        arguments = {"query": "FastAPI", "limit": 10}
        result = await mcp_server._handle_semantic_search(arguments)

        response_data = json.loads(result[0].text)
        assert response_data["results"][0]["cached"] is True

        # Verify cache was checked
        mcp_server.cache_layer.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_complex_concept_exploration(self, mcp_server):
        """Test complex concept exploration with multiple relationship types."""
        # Setup complex graph result
        complex_nodes = [
            {"id": "fastapi", "type": "concept", "name": "FastAPI"},
            {"id": "python", "type": "concept", "name": "Python"},
            {"id": "web", "type": "concept", "name": "Web Development"},
            {"id": "auth", "type": "concept", "name": "Authentication"}
        ]

        complex_relationships = [
            {"from_node": "fastapi", "to_node": "python", "type": "IMPLEMENTS", "strength": 0.9},
            {"from_node": "fastapi", "to_node": "web", "type": "RELATES_TO", "strength": 0.8},
            {"from_node": "auth", "to_node": "fastapi", "type": "DEPENDS_ON", "strength": 0.7}
        ]

        complex_result = GraphSearchResult(
            nodes=complex_nodes,
            relationships=complex_relationships,
            paths=[],
            query_metadata={"execution_time": 0.08}
        )

        mcp_server.graph_store.graph_search.return_value = complex_result

        arguments = {
            "concept_name": "FastAPI",
            "relationship_types": ["IMPLEMENTS", "RELATES_TO", "DEPENDS_ON"],
            "max_depth": 3,
            "include_documents": True
        }

        result = await mcp_server._handle_explore_concept(arguments)
        response_data = json.loads(result[0].text)

        assert response_data["related_concepts_count"] >= 3
        assert response_data["relationships_count"] >= 3
        assert len(response_data["related_documents"]) >= 1

    @pytest.mark.asyncio
    async def test_pattern_discovery_edge_cases(self, mcp_server):
        """Test pattern discovery with edge cases."""
        # Test with empty vector store
        mcp_server.vector_store.get_stats.return_value = {"topics": []}

        arguments = {
            "pattern_type": "topic_clusters",
            "min_confidence": 0.9
        }

        result = await mcp_server._handle_discover_patterns(arguments)
        response_data = json.loads(result[0].text)

        assert response_data["patterns_found"] == 0
        assert response_data["patterns"] == []

    @pytest.mark.asyncio
    async def test_performance_optimization_integration(self, mcp_server):
        """Test integration with performance optimizer."""
        # Mock performance optimizer
        performance_optimizer = AsyncMock()
        performance_optimizer.cached_operation.return_value = ([], True)
        mcp_server.performance_optimizer = performance_optimizer

        arguments = {"query": "performance test", "limit": 5}
        result = await mcp_server._handle_semantic_search(arguments)

        # Verify performance optimizer was used
        performance_optimizer.cached_operation.assert_called_once()

        response_data = json.loads(result[0].text)
        assert response_data["query"] == "performance test"

    def test_server_initialization(self):
        """Test server initialization with different configurations."""
        # Test default configuration
        server1 = PtolemiesMCPServer()
        assert server1.config.enable_semantic_search is True
        assert server1.config.enable_graph_search is True
        assert server1.config.enable_hybrid_search is True

        # Test custom configuration
        custom_config = PtolemiesMCPConfig(
            enable_semantic_search=False,
            enable_graph_search=True,
            enable_hybrid_search=False,
            default_search_limit=25
        )

        server2 = PtolemiesMCPServer(custom_config)
        assert server2.config.enable_semantic_search is False
        assert server2.config.enable_graph_search is True
        assert server2.config.enable_hybrid_search is False
        assert server2.config.default_search_limit == 25

    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self, mcp_server):
        """Test concurrent request handling with semaphore."""
        # Create multiple concurrent requests
        arguments = {"query": f"concurrent test", "limit": 5}

        tasks = []
        for i in range(5):
            task = mcp_server._handle_semantic_search(arguments)
            tasks.append(task)

        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should complete successfully
        assert len(results) == 5
        assert all(not isinstance(r, Exception) for r in results)

        # Each should return valid response
        for result in results:
            assert len(result) == 1
            response_data = json.loads(result[0].text)
            assert response_data["query"] == "concurrent test"

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
