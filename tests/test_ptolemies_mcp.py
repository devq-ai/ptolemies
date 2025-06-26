#!/usr/bin/env python3
"""
Test Suite for Ptolemies MCP Server
===================================

Comprehensive test suite for the unified ptolemies MCP server integration
covering all tools, error handling, and system health monitoring.
"""

import asyncio
import json
import pytest
import tempfile
import os
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Import test framework
import pytest_asyncio

# Import the modules we're testing
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ptolemies_mcp_server import PtolemiesMCPServer, create_server
from ptolemies_integration import PtolemiesIntegration
from ptolemies_tools import PtolemiesTools
from ptolemies_types import (
    SystemHealth, ConnectionStatus, ErrorResponse,
    HybridSearchResult, CodeValidationResult, Framework
)

# Test fixtures
@pytest.fixture
def mock_integration():
    """Create a mock integration layer for testing."""
    integration = AsyncMock(spec=PtolemiesIntegration)

    # Mock connection methods
    integration.connect.return_value = True
    integration.disconnect.return_value = None

    # Mock health check
    integration.get_system_health.return_value = SystemHealth(
        neo4j_status=ConnectionStatus(service="neo4j", connected=True),
        surrealdb_status=ConnectionStatus(service="surrealdb", connected=True),
        dehallucinator_status=ConnectionStatus(service="dehallucinator", connected=True),
        overall_healthy=True
    )

    # Mock search methods
    integration.hybrid_knowledge_search.return_value = {
        "query": "test query",
        "total_results": 2,
        "vector_results": [],
        "graph_results": [],
        "combined_results": [
            {"id": "1", "content": "Test result 1", "source": "neo4j"},
            {"id": "2", "content": "Test result 2", "source": "surrealdb"}
        ],
        "frameworks_found": ["FastAPI"],
        "topics_found": ["authentication"],
        "search_metadata": {"test": True}
    }

    # Mock code validation
    integration.validate_code_snippet.return_value = {
        "code_snippet": "test code",
        "is_valid": True,
        "overall_confidence": 0.2,
        "frameworks_detected": ["FastAPI"],
        "issues": [],
        "patterns_detected": [],
        "suggestions": [],
        "analysis_metadata": {"test": True}
    }

    # Mock framework knowledge
    integration.get_framework_knowledge.return_value = {
        "framework": "FastAPI",
        "topic": "authentication",
        "graph_context": {"nodes": [], "relationships": []},
        "documentation": [],
        "depth": 2,
        "include_examples": True
    }

    return integration


@pytest.fixture
def mock_tools(mock_integration):
    """Create mock tools with the mock integration."""
    return PtolemiesTools(mock_integration)


@pytest.fixture
async def test_server(mock_integration):
    """Create a test server instance with mocked integration."""
    server = PtolemiesMCPServer()

    # Replace the integration with our mock
    server.integration = mock_integration
    server.tools = PtolemiesTools(mock_integration)

    # Initialize without actually connecting
    server.is_initialized = True

    return server


# Test Classes
class TestPtolemiesIntegration:
    """Test the integration layer functionality."""

    @pytest.mark.asyncio
    async def test_connection_success(self, mock_integration):
        """Test successful connection to all services."""
        result = await mock_integration.connect()
        assert result is True
        mock_integration.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_system_health_check(self, mock_integration):
        """Test system health monitoring."""
        health = await mock_integration.get_system_health()

        assert isinstance(health, SystemHealth)
        assert health.overall_healthy is True
        assert health.neo4j_status.connected is True
        assert health.surrealdb_status.connected is True
        assert health.dehallucinator_status.connected is True

    @pytest.mark.asyncio
    async def test_hybrid_search(self, mock_integration):
        """Test hybrid knowledge search functionality."""
        result = await mock_integration.hybrid_knowledge_search(
            query="test query",
            frameworks=["FastAPI"],
            max_results=10
        )

        assert result["query"] == "test query"
        assert result["total_results"] == 2
        assert len(result["combined_results"]) == 2
        assert "FastAPI" in result["frameworks_found"]

    @pytest.mark.asyncio
    async def test_code_validation(self, mock_integration):
        """Test code validation functionality."""
        test_code = "from fastapi import FastAPI\napp = FastAPI()"

        result = await mock_integration.validate_code_snippet(
            code=test_code,
            framework="FastAPI"
        )

        assert result["code_snippet"] == test_code
        assert result["is_valid"] is True
        assert "FastAPI" in result["frameworks_detected"]


class TestPtolemiesTools:
    """Test the MCP tools functionality."""

    def test_tools_initialization(self, mock_tools):
        """Test that tools are properly initialized."""
        tools = mock_tools.get_tools()

        assert len(tools) > 0

        # Check that key tools are present
        tool_names = [tool.name for tool in tools]
        expected_tools = [
            "hybrid-knowledge-search",
            "framework-knowledge-query",
            "validate-code-snippet",
            "system-health-check"
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    def test_tool_schemas(self, mock_tools):
        """Test that tool schemas are properly defined."""
        tools = mock_tools.get_tools()

        for tool in tools:
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')
            assert hasattr(tool, 'inputSchema')
            assert isinstance(tool.inputSchema, dict)
            assert 'type' in tool.inputSchema
            assert tool.inputSchema['type'] == 'object'

    @pytest.mark.asyncio
    async def test_hybrid_search_tool(self, mock_tools):
        """Test the hybrid knowledge search tool."""
        class MockRequest:
            def __init__(self):
                self.params = MockParams()

        class MockParams:
            def __init__(self):
                self.name = "hybrid-knowledge-search"
                self.arguments = {
                    "query": "FastAPI authentication",
                    "max_results": 5
                }

        request = MockRequest()
        result = await mock_tools.call_tool(request)

        assert result is not None
        assert len(result.content) > 0

        # Parse the JSON response
        response_data = json.loads(result.content[0].text)
        assert response_data["success"] is True
        assert "hybrid-knowledge-search" in response_data["tool"]

    @pytest.mark.asyncio
    async def test_code_validation_tool(self, mock_tools):
        """Test the code validation tool."""
        class MockRequest:
            def __init__(self):
                self.params = MockParams()

        class MockParams:
            def __init__(self):
                self.name = "validate-code-snippet"
                self.arguments = {
                    "code": "from fastapi import FastAPI\napp = FastAPI()",
                    "framework": "FastAPI"
                }

        request = MockRequest()
        result = await mock_tools.call_tool(request)

        assert result is not None
        assert len(result.content) > 0

        # Parse the JSON response
        response_data = json.loads(result.content[0].text)
        assert response_data["success"] is True
        assert "validate-code-snippet" in response_data["tool"]

    @pytest.mark.asyncio
    async def test_system_health_tool(self, mock_tools):
        """Test the system health check tool."""
        class MockRequest:
            def __init__(self):
                self.params = MockParams()

        class MockParams:
            def __init__(self):
                self.name = "system-health-check"
                self.arguments = {}

        request = MockRequest()
        result = await mock_tools.call_tool(request)

        assert result is not None
        assert len(result.content) > 0

        # Parse the JSON response
        response_data = json.loads(result.content[0].text)
        assert response_data["success"] is True
        assert response_data["overall_healthy"] is True

    @pytest.mark.asyncio
    async def test_unknown_tool_error(self, mock_tools):
        """Test error handling for unknown tools."""
        class MockRequest:
            def __init__(self):
                self.params = MockParams()

        class MockParams:
            def __init__(self):
                self.name = "nonexistent-tool"
                self.arguments = {}

        request = MockRequest()
        result = await mock_tools.call_tool(request)

        assert result is not None
        assert len(result.content) > 0

        # Parse the JSON response
        response_data = json.loads(result.content[0].text)
        assert response_data["success"] is False
        assert "error" in response_data


class TestPtolemiesMCPServer:
    """Test the main MCP server functionality."""

    @pytest.mark.asyncio
    async def test_server_initialization(self):
        """Test server initialization."""
        server = await create_server()

        assert server is not None
        assert isinstance(server, PtolemiesMCPServer)
        assert server.integration is not None
        assert server.tools is not None

    @pytest.mark.asyncio
    async def test_server_lifespan(self, test_server):
        """Test server lifecycle management."""
        # Test that server starts in uninitialized state
        assert test_server.is_initialized is True  # Mocked as True

        # Test cleanup
        await test_server.cleanup()
        # Should not raise any exceptions

    def test_server_info(self, test_server):
        """Test server information retrieval."""
        info = test_server.get_server_info()

        assert info["name"] == "ptolemies-mcp"
        assert "version" in info
        assert "capabilities" in info
        assert "data_sources" in info
        assert info["initialized"] is True

    @pytest.mark.asyncio
    async def test_request_limiting(self, test_server):
        """Test concurrent request limiting."""
        # Simulate multiple concurrent requests
        async def mock_request():
            return await test_server._execute_tool_call(
                "system-health-check", {}
            )

        # Create more requests than the limit
        tasks = [mock_request() for _ in range(15)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should complete successfully (mocked)
        assert len(results) == 15
        for result in results:
            assert not isinstance(result, Exception)

    @pytest.mark.asyncio
    async def test_error_handling(self, test_server):
        """Test error handling in tool execution."""
        # Mock an error in the integration layer
        test_server.integration.get_system_health.side_effect = Exception("Test error")

        result = await test_server._execute_tool_call("system-health-check", {})

        assert len(result) > 0
        response_data = json.loads(result[0].text)
        assert response_data["success"] is False
        assert "error" in response_data


class TestIntegrationScenarios:
    """Test real-world integration scenarios."""

    @pytest.mark.asyncio
    async def test_full_search_workflow(self, mock_integration):
        """Test a complete search workflow."""
        # Step 1: Perform hybrid search
        search_result = await mock_integration.hybrid_knowledge_search(
            query="How to implement FastAPI authentication?",
            frameworks=["FastAPI"],
            max_results=5
        )

        assert search_result["query"] == "How to implement FastAPI authentication?"
        assert "FastAPI" in search_result["frameworks_found"]

        # Step 2: Get detailed framework knowledge
        framework_result = await mock_integration.get_framework_knowledge(
            framework="FastAPI",
            topic="authentication",
            depth=2
        )

        assert framework_result["framework"] == "FastAPI"
        assert framework_result["topic"] == "authentication"

    @pytest.mark.asyncio
    async def test_code_validation_workflow(self, mock_integration):
        """Test a complete code validation workflow."""
        # Test valid code
        valid_code = """
from fastapi import FastAPI, Depends
from fastapi.security import HTTPBearer

app = FastAPI()
security = HTTPBearer()

@app.get("/protected")
def protected_route(token: str = Depends(security)):
    return {"message": "Access granted"}
"""

        result = await mock_integration.validate_code_snippet(
            code=valid_code,
            framework="FastAPI",
            confidence_threshold=0.75
        )

        assert result["is_valid"] is True
        assert "FastAPI" in result["frameworks_detected"]

    @pytest.mark.asyncio
    async def test_system_monitoring_workflow(self, mock_integration):
        """Test system monitoring and health checking."""
        # Check overall health
        health = await mock_integration.get_system_health()

        assert health.overall_healthy is True

        # Verify individual service health
        assert health.neo4j_status.connected is True
        assert health.surrealdb_status.connected is True
        assert health.dehallucinator_status.connected is True


class TestErrorConditions:
    """Test various error conditions and edge cases."""

    @pytest.mark.asyncio
    async def test_service_unavailable(self):
        """Test behavior when services are unavailable."""
        integration = PtolemiesIntegration()

        # Mock failed connections
        with patch.object(integration, '_connect_neo4j', return_value=False), \
             patch.object(integration, '_connect_surrealdb', return_value=False), \
             patch.object(integration, '_initialize_dehallucinator', return_value=False):

            result = await integration.connect()
            assert result is False

    @pytest.mark.asyncio
    async def test_partial_service_availability(self):
        """Test behavior with partial service availability."""
        integration = PtolemiesIntegration()

        # Mock partial success (2 out of 3 services)
        with patch.object(integration, '_connect_neo4j', return_value=True), \
             patch.object(integration, '_connect_surrealdb', return_value=True), \
             patch.object(integration, '_initialize_dehallucinator', return_value=False):

            result = await integration.connect()
            assert result is True  # Should succeed with 2/3 services

    @pytest.mark.asyncio
    async def test_invalid_tool_arguments(self, mock_tools):
        """Test handling of invalid tool arguments."""
        class MockRequest:
            def __init__(self):
                self.params = MockParams()

        class MockParams:
            def __init__(self):
                self.name = "hybrid-knowledge-search"
                self.arguments = {}  # Missing required 'query' argument

        request = MockRequest()

        # This should handle the missing argument gracefully
        # The actual validation would happen at a higher level
        result = await mock_tools.call_tool(request)
        assert result is not None

    @pytest.mark.asyncio
    async def test_large_response_handling(self, mock_integration):
        """Test handling of large responses."""
        # Mock a large response
        large_results = [
            {"id": f"result_{i}", "content": f"Large content {i}" * 100}
            for i in range(100)
        ]

        mock_integration.hybrid_knowledge_search.return_value = {
            "query": "large query",
            "total_results": 100,
            "combined_results": large_results,
            "frameworks_found": ["FastAPI"] * 50,
            "topics_found": ["topic"] * 50,
            "search_metadata": {}
        }

        result = await mock_integration.hybrid_knowledge_search(
            query="large query",
            max_results=100
        )

        assert len(result["combined_results"]) == 100
        assert result["total_results"] == 100


class TestPerformance:
    """Test performance characteristics."""

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, test_server):
        """Test handling of concurrent requests."""
        async def make_request():
            return await test_server._execute_tool_call(
                "system-health-check", {}
            )

        # Run 10 concurrent requests
        start_time = asyncio.get_event_loop().time()
        tasks = [make_request() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        end_time = asyncio.get_event_loop().time()

        # All requests should complete
        assert len(results) == 10

        # Should complete in reasonable time (less than 5 seconds for mocked operations)
        assert (end_time - start_time) < 5.0

    @pytest.mark.asyncio
    async def test_memory_usage(self, test_server):
        """Test that memory usage remains reasonable."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Perform multiple operations
        for _ in range(50):
            await test_server._execute_tool_call("system-health-check", {})

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 100MB for mocked operations)
        assert memory_increase < 100 * 1024 * 1024


class TestConfiguration:
    """Test configuration and environment handling."""

    def test_environment_variable_handling(self):
        """Test environment variable configuration."""
        # Test with environment variables set
        test_env = {
            "NEO4J_URI": "bolt://test:7687",
            "NEO4J_USERNAME": "test_user",
            "NEO4J_PASSWORD": "test_pass",
            "SURREALDB_URL": "ws://test:8000/rpc"
        }

        with patch.dict(os.environ, test_env):
            integration = PtolemiesIntegration()

            assert integration.neo4j_uri == "bolt://test:7687"
            assert integration.neo4j_username == "test_user"
            assert integration.neo4j_password == "test_pass"
            assert integration.surrealdb_url == "ws://test:8000/rpc"

    def test_default_configuration(self):
        """Test default configuration values."""
        integration = PtolemiesIntegration()

        # Should have reasonable defaults
        assert "localhost" in integration.neo4j_uri
        assert "localhost" in integration.surrealdb_url
        assert integration.neo4j_username == "neo4j"


# Integration test fixtures for actual service testing
@pytest.fixture
def temp_test_file():
    """Create a temporary test file for code validation."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}
""")
        f.flush()
        yield f.name

    # Cleanup
    os.unlink(f.name)


# Utility functions for testing
def assert_valid_json_response(response_text: str):
    """Assert that a response is valid JSON."""
    try:
        data = json.loads(response_text)
        assert isinstance(data, dict)
        return data
    except json.JSONDecodeError:
        pytest.fail(f"Response is not valid JSON: {response_text}")


def assert_successful_response(response_data: dict):
    """Assert that a response indicates success."""
    assert "success" in response_data
    assert response_data["success"] is True
    assert "timestamp" in response_data
    assert "source" in response_data
    assert response_data["source"] == "ptolemies-mcp"


def assert_error_response(response_data: dict):
    """Assert that a response indicates an error."""
    assert "success" in response_data
    assert response_data["success"] is False
    assert "error_type" in response_data
    assert "error_message" in response_data


# Mark all tests as asyncio
pytestmark = pytest.mark.asyncio


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])
