#!/usr/bin/env python3
"""
Functional Test Suite for Ptolemies MCP Server Handlers
Simplified tests to verify core handler functionality is implemented correctly.
"""

import pytest
import asyncio
import os
import sys
import json
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

# Set logfire config for testing
os.environ['LOGFIRE_IGNORE_NO_CONFIG'] = '1'

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ptolemies_mcp_server import PtolemiesMCPServer, PtolemiesMCPConfig

class TestMCPFunctional:
    """Functional tests for MCP server handlers."""

    def test_server_initialization(self):
        """Test that server initializes successfully."""
        config = PtolemiesMCPConfig()
        server = PtolemiesMCPServer(config)

        assert server.config.server_name == "ptolemies-knowledge"
        assert server.config.server_version == "1.0.0"
        assert server.config.enable_semantic_search is True
        assert server.config.enable_graph_search is True
        assert server.config.enable_hybrid_search is True

    def test_handler_methods_exist(self):
        """Test that all required handler methods exist."""
        server = PtolemiesMCPServer()

        # Core search handlers
        assert hasattr(server, '_handle_semantic_search')
        assert hasattr(server, '_handle_graph_search')
        assert hasattr(server, '_handle_hybrid_search')

        # Document management handlers
        assert hasattr(server, '_handle_index_document')
        assert hasattr(server, '_handle_retrieve_document')

        # Advanced handlers
        assert hasattr(server, '_handle_explore_concept')
        assert hasattr(server, '_handle_discover_patterns')

        # Utility handlers
        assert hasattr(server, '_handle_get_knowledge_stats')
        assert hasattr(server, '_handle_get_query_suggestions')

    @pytest.mark.asyncio
    async def test_semantic_search_handler_error_without_store(self):
        """Test semantic search handler error when vector store not initialized."""
        server = PtolemiesMCPServer()
        arguments = {"query": "test query"}

        with pytest.raises(RuntimeError, match="Vector store not initialized"):
            await server._handle_semantic_search(arguments)

    @pytest.mark.asyncio
    async def test_graph_search_handler_error_without_store(self):
        """Test graph search handler error when graph store not initialized."""
        server = PtolemiesMCPServer()
        arguments = {"query": "test query"}

        with pytest.raises(RuntimeError, match="Graph store not initialized"):
            await server._handle_graph_search(arguments)

    @pytest.mark.asyncio
    async def test_hybrid_search_handler_error_without_engine(self):
        """Test hybrid search handler error when hybrid engine not initialized."""
        server = PtolemiesMCPServer()
        arguments = {"query": "test query"}

        with pytest.raises(RuntimeError, match="Hybrid engine not initialized"):
            await server._handle_hybrid_search(arguments)

    @pytest.mark.asyncio
    async def test_retrieve_document_handler_validation(self):
        """Test retrieve document handler input validation."""
        server = PtolemiesMCPServer()

        # Test without required arguments
        result = await server._handle_retrieve_document({})
        response_text = result[0].text
        response_data = json.loads(response_text)

        assert "error" in response_data
        assert "Either 'document_id' or 'url' must be provided" in response_data["error"]

    @pytest.mark.asyncio
    async def test_index_document_handler_validation(self):
        """Test index document handler input validation."""
        server = PtolemiesMCPServer()

        # Test without required arguments
        result = await server._handle_index_document({})
        response_text = result[0].text
        response_data = json.loads(response_text)

        assert "error" in response_data
        assert "Either 'url' or 'content' must be provided" in response_data["error"]

    @pytest.mark.asyncio
    async def test_get_knowledge_stats_handler_without_components(self):
        """Test knowledge stats handler when components not initialized."""
        server = PtolemiesMCPServer()
        arguments = {"include_performance": True, "include_cache": True}

        result = await server._handle_get_knowledge_stats(arguments)
        response_text = result[0].text
        response_data = json.loads(response_text)

        assert "server_info" in response_data
        assert response_data["server_info"]["name"] == "ptolemies-knowledge"

        # Components should show as not initialized (no errors since they're optional)
        # Vector store and graph store won't be in response if not initialized

    @pytest.mark.asyncio
    async def test_semantic_search_with_mocked_store(self):
        """Test semantic search with mocked vector store."""
        server = PtolemiesMCPServer()

        # Create mock vector store
        mock_store = AsyncMock()

        # Mock document chunk (simplified structure)
        mock_doc = Mock()
        mock_doc.id = "test-doc-1"
        mock_doc.title = "Test Document"
        mock_doc.content = "Test content about FastAPI"
        mock_doc.source_name = "Test Source"
        mock_doc.source_url = "https://test.com"
        mock_doc.topics = ["fastapi", "test"]
        mock_doc.quality_score = 0.9
        mock_doc.chunk_index = 0
        mock_doc.total_chunks = 1

        # Mock search result
        mock_result = Mock()
        mock_result.document = mock_doc
        mock_result.similarity_score = 0.95

        mock_store.semantic_search.return_value = [mock_result]
        server.vector_store = mock_store

        # Test the handler
        arguments = {
            "query": "FastAPI test",
            "limit": 10,
            "quality_threshold": 0.5
        }

        result = await server._handle_semantic_search(arguments)
        response_text = result[0].text
        response_data = json.loads(response_text)

        assert response_data["query"] == "FastAPI test"
        assert response_data["search_type"] == "semantic"
        assert response_data["results_count"] == 1
        assert len(response_data["results"]) == 1

        # Verify result structure
        doc_result = response_data["results"][0]
        assert doc_result["id"] == "test-doc-1"
        assert doc_result["title"] == "Test Document"
        assert doc_result["similarity_score"] == 0.95

    @pytest.mark.asyncio
    async def test_pattern_discovery_handlers_exist(self):
        """Test that pattern discovery methods exist and can be called."""
        server = PtolemiesMCPServer()

        # Test topic clusters discovery
        patterns = await server._discover_topic_clusters("test", 0.7)
        assert isinstance(patterns, list)

        # Test concept hierarchies discovery
        patterns = await server._discover_concept_hierarchies("test", 0.7)
        assert isinstance(patterns, list)

        # Test document similarities discovery
        patterns = await server._discover_document_similarities("test", 0.7)
        assert isinstance(patterns, list)

        # Test temporal patterns discovery
        patterns = await server._discover_temporal_patterns("test", 0.7)
        assert isinstance(patterns, list)

    @pytest.mark.asyncio
    async def test_discover_patterns_handler(self):
        """Test pattern discovery handler with different pattern types."""
        server = PtolemiesMCPServer()

        # Test topic clusters
        arguments = {
            "pattern_type": "topic_clusters",
            "min_confidence": 0.7
        }

        result = await server._handle_discover_patterns(arguments)
        response_text = result[0].text
        response_data = json.loads(response_text)

        assert response_data["pattern_type"] == "topic_clusters"
        assert response_data["min_confidence"] == 0.7
        assert "patterns" in response_data

        # Test invalid pattern type
        arguments = {
            "pattern_type": "invalid_pattern",
            "min_confidence": 0.7
        }

        result = await server._handle_discover_patterns(arguments)
        response_text = result[0].text
        response_data = json.loads(response_text)

        assert "error" in response_data

    def test_tool_registry_methods(self):
        """Test tool registry management methods."""
        server = PtolemiesMCPServer()

        # Test tool registry methods exist
        assert hasattr(server, 'register_custom_tool')
        assert hasattr(server, 'unregister_tool')
        assert hasattr(server, 'set_tool_status')
        assert hasattr(server, 'get_tool_info')
        assert hasattr(server, 'list_tools_by_category')
        assert hasattr(server, 'get_tool_registry_stats')

    def test_configuration_options(self):
        """Test different configuration options."""
        # Test disabled features
        config = PtolemiesMCPConfig(
            enable_semantic_search=False,
            enable_graph_search=False,
            enable_hybrid_search=False,
            enable_caching=False,
            enable_dynamic_tools=False
        )

        server = PtolemiesMCPServer(config)

        assert server.config.enable_semantic_search is False
        assert server.config.enable_graph_search is False
        assert server.config.enable_hybrid_search is False
        assert server.config.enable_caching is False
        assert server.tool_registry is None

    @pytest.mark.asyncio
    async def test_component_initialization_and_cleanup(self):
        """Test component initialization and cleanup methods."""
        server = PtolemiesMCPServer()

        # Test initialization method exists
        assert hasattr(server, 'initialize_components')

        # Test cleanup method exists
        assert hasattr(server, 'cleanup')

        # Test cleanup doesn't fail when components aren't initialized
        await server.cleanup()  # Should not raise exception

    def test_factory_function_exists(self):
        """Test that factory function exists."""
        from ptolemies_mcp_server import create_mcp_server

        assert callable(create_mcp_server)

    @pytest.mark.asyncio
    async def test_error_handling_in_handlers(self):
        """Test error handling in various handlers."""
        server = PtolemiesMCPServer()

        # Test retrieve document with missing vector store
        arguments = {"document_id": "test"}

        with pytest.raises(RuntimeError):
            await server._handle_retrieve_document(arguments)

        # Test explore concept with missing graph store
        arguments = {"concept_name": "test"}

        with pytest.raises(RuntimeError):
            await server._handle_explore_concept(arguments)

    def test_request_semaphore_initialization(self):
        """Test that request semaphore is properly initialized."""
        config = PtolemiesMCPConfig(max_concurrent_requests=5)
        server = PtolemiesMCPServer(config)

        assert server.request_semaphore._value == 5
        assert server.active_requests == 0

    @pytest.mark.asyncio
    async def test_tool_call_handler_structure(self):
        """Test that tool call handler has proper structure."""
        server = PtolemiesMCPServer()

        # Mock the server's call_tool handler
        assert hasattr(server.server, '_handlers')

        # Test that key handlers are properly mapped in _setup_handlers
        # This verifies the handler routing logic exists
        handler_method_names = [
            '_handle_semantic_search',
            '_handle_graph_search',
            '_handle_hybrid_search',
            '_handle_index_document',
            '_handle_retrieve_document',
            '_handle_explore_concept',
            '_handle_discover_patterns',
            '_handle_get_knowledge_stats',
            '_handle_get_query_suggestions'
        ]

        for method_name in handler_method_names:
            assert hasattr(server, method_name)
            assert callable(getattr(server, method_name))

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
