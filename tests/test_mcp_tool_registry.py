#!/usr/bin/env python3
"""
Test suite for MCP Tool Registration System
"""

import pytest
import asyncio
import json
import time
import os
import sys
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
from tempfile import NamedTemporaryFile

# Set logfire config for testing
os.environ['LOGFIRE_IGNORE_NO_CONFIG'] = '1'

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_tool_registry import (
    MCPToolRegistry,
    ToolMetadata,
    ToolUsageStats,
    RegisteredTool,
    BaseMCPTool,
    ToolCategory,
    ToolStatus,
    create_tool_spec,
    tool_metadata,
    register_mcp_tool
)

import mcp.types as types

class TestToolMetadata:
    """Test tool metadata functionality."""
    
    def test_tool_metadata_creation(self):
        """Test tool metadata creation with defaults."""
        metadata = ToolMetadata(
            name="test_tool",
            description="Test tool description",
            category=ToolCategory.SEARCH
        )
        
        assert metadata.name == "test_tool"
        assert metadata.description == "Test tool description"
        assert metadata.category == ToolCategory.SEARCH
        assert metadata.version == "1.0.0"
        assert metadata.author is None
        assert metadata.tags == []
        assert metadata.requires_auth is False
        assert metadata.rate_limit is None
        assert metadata.timeout_seconds == 30
        assert metadata.cache_ttl_seconds is None
        assert metadata.dependencies == []
        assert metadata.experimental is False
    
    def test_tool_metadata_custom_values(self):
        """Test tool metadata with custom values."""
        metadata = ToolMetadata(
            name="custom_tool",
            description="Custom tool",
            category=ToolCategory.ANALYTICS,
            version="2.1.0",
            author="Test Author",
            tags=["search", "analytics"],
            requires_auth=True,
            rate_limit=100,
            timeout_seconds=60,
            cache_ttl_seconds=3600,
            dependencies=["tool1", "tool2"],
            experimental=True
        )
        
        assert metadata.name == "custom_tool"
        assert metadata.version == "2.1.0"
        assert metadata.author == "Test Author"
        assert metadata.tags == ["search", "analytics"]
        assert metadata.requires_auth is True
        assert metadata.rate_limit == 100
        assert metadata.timeout_seconds == 60
        assert metadata.cache_ttl_seconds == 3600
        assert metadata.dependencies == ["tool1", "tool2"]
        assert metadata.experimental is True

class TestToolUsageStats:
    """Test tool usage statistics."""
    
    def test_usage_stats_defaults(self):
        """Test default usage statistics."""
        stats = ToolUsageStats()
        
        assert stats.total_calls == 0
        assert stats.successful_calls == 0
        assert stats.failed_calls == 0
        assert stats.total_execution_time_ms == 0.0
        assert stats.avg_execution_time_ms == 0.0
        assert stats.last_called_at is None
        assert stats.last_error is None
        assert stats.rate_limit_hits == 0
    
    def test_usage_stats_custom_values(self):
        """Test usage statistics with custom values."""
        stats = ToolUsageStats(
            total_calls=100,
            successful_calls=95,
            failed_calls=5,
            total_execution_time_ms=50000.0,
            avg_execution_time_ms=500.0,
            last_called_at=time.time(),
            last_error="Test error",
            rate_limit_hits=3
        )
        
        assert stats.total_calls == 100
        assert stats.successful_calls == 95
        assert stats.failed_calls == 5
        assert stats.total_execution_time_ms == 50000.0
        assert stats.avg_execution_time_ms == 500.0
        assert stats.last_called_at is not None
        assert stats.last_error == "Test error"
        assert stats.rate_limit_hits == 3

class TestRegisteredTool:
    """Test registered tool functionality."""
    
    def test_registered_tool_creation(self):
        """Test registered tool creation with defaults."""
        tool_spec = types.Tool(
            name="test_tool",
            description="Test tool",
            inputSchema={"type": "object"}
        )
        
        async def handler(args):
            return []
        
        metadata = ToolMetadata(
            name="test_tool",
            description="Test tool",
            category=ToolCategory.SEARCH
        )
        
        registered_tool = RegisteredTool(
            tool_spec=tool_spec,
            handler=handler,
            metadata=metadata
        )
        
        assert registered_tool.tool_spec == tool_spec
        assert registered_tool.handler == handler
        assert registered_tool.metadata == metadata
        assert registered_tool.status == ToolStatus.ACTIVE
        assert registered_tool.registered_at is not None
        assert isinstance(registered_tool.usage_stats, ToolUsageStats)
        assert registered_tool.config == {}

class MockMCPTool(BaseMCPTool):
    """Mock MCP tool for testing."""
    
    def __init__(self, name: str = "mock_tool"):
        metadata = ToolMetadata(
            name=name,
            description="Mock tool for testing",
            category=ToolCategory.UTILITIES
        )
        super().__init__(metadata)
        self.execute_called = False
        self.validate_called = False
    
    async def execute(self, arguments):
        self.execute_called = True
        return [types.TextContent(
            type="text",
            text=f"Mock result for args: {arguments}"
        )]
    
    def get_tool_spec(self):
        return types.Tool(
            name=self.metadata.name,
            description=self.metadata.description,
            inputSchema={
                "type": "object",
                "properties": {
                    "input": {"type": "string"}
                }
            }
        )
    
    def validate_arguments(self, arguments):
        self.validate_called = True
        return "input" in arguments

class TestBaseMCPTool:
    """Test base MCP tool functionality."""
    
    def test_base_tool_creation(self):
        """Test base tool creation."""
        tool = MockMCPTool("test_tool")
        
        assert tool.metadata.name == "test_tool"
        assert tool.metadata.description == "Mock tool for testing"
        assert tool.metadata.category == ToolCategory.UTILITIES
        assert isinstance(tool.usage_stats, ToolUsageStats)
        assert tool.config == {}
    
    @pytest.mark.asyncio
    async def test_base_tool_execute(self):
        """Test base tool execute method."""
        tool = MockMCPTool()
        
        result = await tool.execute({"input": "test"})
        
        assert tool.execute_called is True
        assert len(result) == 1
        assert isinstance(result[0], types.TextContent)
        assert "Mock result" in result[0].text
    
    def test_base_tool_validate(self):
        """Test base tool validation."""
        tool = MockMCPTool()
        
        # Valid arguments
        valid = tool.validate_arguments({"input": "test"})
        assert valid is True
        assert tool.validate_called is True
        
        # Invalid arguments
        tool.validate_called = False
        invalid = tool.validate_arguments({"wrong": "test"})
        assert invalid is False
        assert tool.validate_called is True
    
    def test_base_tool_get_spec(self):
        """Test base tool spec retrieval."""
        tool = MockMCPTool("spec_tool")
        
        spec = tool.get_tool_spec()
        
        assert isinstance(spec, types.Tool)
        assert spec.name == "spec_tool"
        assert spec.description == "Mock tool for testing"

class TestMCPToolRegistry:
    """Test MCP tool registry functionality."""
    
    @pytest.fixture
    def registry(self):
        """Create test registry."""
        return MCPToolRegistry()
    
    @pytest.fixture
    def sample_tool_spec(self):
        """Create sample tool spec."""
        return types.Tool(
            name="sample_tool",
            description="Sample tool for testing",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }
        )
    
    @pytest.fixture
    def sample_metadata(self):
        """Create sample metadata."""
        return ToolMetadata(
            name="sample_tool",
            description="Sample tool for testing",
            category=ToolCategory.SEARCH,
            version="1.0.0"
        )
    
    @pytest.fixture
    def sample_handler(self):
        """Create sample handler."""
        async def handler(arguments):
            return [types.TextContent(
                type="text",
                text=f"Result: {arguments.get('query', 'no query')}"
            )]
        return handler
    
    def test_registry_initialization(self, registry):
        """Test registry initialization."""
        assert isinstance(registry.tools, dict)
        assert len(registry.tools) == 0
        assert isinstance(registry.tool_instances, dict)
        assert isinstance(registry.rate_limiters, dict)
        assert registry.config_file is None
        assert registry.registry_start_time > 0
    
    def test_registry_with_config_file(self):
        """Test registry initialization with config file."""
        with NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"tools": {}}, f)
            config_file = f.name
        
        try:
            registry = MCPToolRegistry(config_file=config_file)
            assert registry.config_file == config_file
        finally:
            os.unlink(config_file)
    
    def test_register_tool_success(self, registry, sample_tool_spec, sample_metadata, sample_handler):
        """Test successful tool registration."""
        success = registry.register_tool(
            "sample_tool",
            sample_handler,
            sample_tool_spec,
            sample_metadata
        )
        
        assert success is True
        assert "sample_tool" in registry.tools
        
        registered_tool = registry.tools["sample_tool"]
        assert registered_tool.tool_spec == sample_tool_spec
        assert registered_tool.handler == sample_handler
        assert registered_tool.metadata == sample_metadata
        assert registered_tool.status == ToolStatus.ACTIVE
    
    def test_register_tool_with_base_tool(self, registry):
        """Test registering a BaseMCPTool instance."""
        tool_instance = MockMCPTool("base_tool")
        tool_spec = tool_instance.get_tool_spec()
        
        success = registry.register_tool(
            "base_tool",
            tool_instance,
            tool_spec,
            tool_instance.metadata
        )
        
        assert success is True
        assert "base_tool" in registry.tools
        assert "base_tool" in registry.tool_instances
        assert registry.tool_instances["base_tool"] == tool_instance
    
    def test_register_tool_duplicate_name(self, registry, sample_tool_spec, sample_metadata, sample_handler):
        """Test registering tool with duplicate name."""
        # Register first tool
        success1 = registry.register_tool(
            "duplicate_tool",
            sample_handler,
            sample_tool_spec,
            sample_metadata
        )
        assert success1 is True
        
        # Try to register with same name
        success2 = registry.register_tool(
            "duplicate_tool",
            sample_handler,
            sample_tool_spec,
            sample_metadata
        )
        assert success2 is False
    
    def test_register_tool_with_rate_limit(self, registry, sample_tool_spec, sample_handler):
        """Test registering tool with rate limit."""
        metadata = ToolMetadata(
            name="rate_limited_tool",
            description="Rate limited tool",
            category=ToolCategory.SEARCH,
            rate_limit=10
        )
        
        success = registry.register_tool(
            "rate_limited_tool",
            sample_handler,
            sample_tool_spec,
            metadata
        )
        
        assert success is True
        assert "rate_limited_tool" in registry.rate_limiters
        assert registry.rate_limiters["rate_limited_tool"]["limit"] == 10
    
    def test_unregister_tool_success(self, registry, sample_tool_spec, sample_metadata, sample_handler):
        """Test successful tool unregistration."""
        # Register tool first
        registry.register_tool("test_tool", sample_handler, sample_tool_spec, sample_metadata)
        assert "test_tool" in registry.tools
        
        # Unregister tool
        success = registry.unregister_tool("test_tool")
        
        assert success is True
        assert "test_tool" not in registry.tools
    
    def test_unregister_tool_not_found(self, registry):
        """Test unregistering non-existent tool."""
        success = registry.unregister_tool("nonexistent_tool")
        assert success is False
    
    def test_get_tool_specs_all(self, registry, sample_tool_spec, sample_metadata, sample_handler):
        """Test getting all tool specs."""
        # Register multiple tools
        registry.register_tool("tool1", sample_handler, sample_tool_spec, sample_metadata)
        
        metadata2 = ToolMetadata(
            name="tool2",
            description="Tool 2",
            category=ToolCategory.ANALYTICS
        )
        registry.register_tool("tool2", sample_handler, sample_tool_spec, metadata2)
        
        tool_specs = registry.get_tool_specs()
        
        assert len(tool_specs) == 2
        assert all(isinstance(spec, types.Tool) for spec in tool_specs)
    
    def test_get_tool_specs_by_category(self, registry, sample_tool_spec, sample_metadata, sample_handler):
        """Test getting tool specs filtered by category."""
        # Register tools in different categories
        registry.register_tool("search_tool", sample_handler, sample_tool_spec, sample_metadata)
        
        analytics_metadata = ToolMetadata(
            name="analytics_tool",
            description="Analytics tool",
            category=ToolCategory.ANALYTICS
        )
        registry.register_tool("analytics_tool", sample_handler, sample_tool_spec, analytics_metadata)
        
        search_specs = registry.get_tool_specs(ToolCategory.SEARCH)
        analytics_specs = registry.get_tool_specs(ToolCategory.ANALYTICS)
        
        assert len(search_specs) == 1
        assert len(analytics_specs) == 1
    
    def test_get_tool_specs_inactive_excluded(self, registry, sample_handler):
        """Test that inactive tools are excluded from tool specs."""
        # Create separate tool specs
        active_spec = types.Tool(
            name="active_tool",
            description="Active tool for testing",
            inputSchema={"type": "object", "properties": {"query": {"type": "string"}}}
        )
        inactive_spec = types.Tool(
            name="inactive_tool",
            description="Inactive tool for testing",
            inputSchema={"type": "object", "properties": {"query": {"type": "string"}}}
        )
        
        active_metadata = ToolMetadata(
            name="active_tool",
            description="Active tool",
            category=ToolCategory.SEARCH
        )
        inactive_metadata = ToolMetadata(
            name="inactive_tool",
            description="Inactive tool",
            category=ToolCategory.SEARCH
        )
        
        registry.register_tool("active_tool", sample_handler, active_spec, active_metadata)
        registry.register_tool("inactive_tool", sample_handler, inactive_spec, inactive_metadata)
        
        # Make second tool inactive
        registry.set_tool_status("inactive_tool", ToolStatus.INACTIVE)
        
        tool_specs = registry.get_tool_specs()
        
        assert len(tool_specs) == 1
        assert tool_specs[0].name == "active_tool"
    
    @pytest.mark.asyncio
    async def test_execute_tool_success(self, registry, sample_tool_spec, sample_metadata, sample_handler):
        """Test successful tool execution."""
        registry.register_tool("test_tool", sample_handler, sample_tool_spec, sample_metadata)
        
        result = await registry.execute_tool("test_tool", {"query": "test query"})
        
        assert len(result) == 1
        assert isinstance(result[0], types.TextContent)
        assert "test query" in result[0].text
        
        # Check usage stats updated
        stats = registry.tools["test_tool"].usage_stats
        assert stats.total_calls == 1
        assert stats.successful_calls == 1
        assert stats.failed_calls == 0
    
    @pytest.mark.asyncio
    async def test_execute_tool_not_registered(self, registry):
        """Test executing non-registered tool."""
        with pytest.raises(ValueError, match="Tool 'nonexistent' is not registered"):
            await registry.execute_tool("nonexistent", {})
    
    @pytest.mark.asyncio
    async def test_execute_tool_inactive(self, registry, sample_tool_spec, sample_metadata, sample_handler):
        """Test executing inactive tool."""
        registry.register_tool("inactive_tool", sample_handler, sample_tool_spec, sample_metadata)
        registry.set_tool_status("inactive_tool", ToolStatus.INACTIVE)
        
        with pytest.raises(RuntimeError, match="Tool 'inactive_tool' is not active"):
            await registry.execute_tool("inactive_tool", {})
    
    @pytest.mark.asyncio
    async def test_execute_tool_with_validation(self, registry):
        """Test tool execution with argument validation."""
        tool_instance = MockMCPTool("validation_tool")
        tool_spec = tool_instance.get_tool_spec()
        
        registry.register_tool(
            "validation_tool",
            tool_instance,
            tool_spec,
            tool_instance.metadata
        )
        
        # Valid arguments
        result = await registry.execute_tool("validation_tool", {"input": "test"})
        assert len(result) == 1
        assert tool_instance.validate_called is True
        
        # Invalid arguments should raise error
        with pytest.raises(ValueError, match="Invalid arguments"):
            await registry.execute_tool("validation_tool", {"wrong": "test"})
    
    @pytest.mark.asyncio
    async def test_execute_tool_timeout(self, registry):
        """Test tool execution timeout."""
        async def slow_handler(arguments):
            await asyncio.sleep(2)  # Longer than timeout
            return []
        
        metadata = ToolMetadata(
            name="slow_tool",
            description="Slow tool",
            category=ToolCategory.UTILITIES,
            timeout_seconds=0.1  # Very short timeout
        )
        
        tool_spec = types.Tool(name="slow_tool", description="Slow tool", inputSchema={})
        
        registry.register_tool("slow_tool", slow_handler, tool_spec, metadata)
        
        with pytest.raises(RuntimeError, match="execution timed out"):
            await registry.execute_tool("slow_tool", {})
    
    @pytest.mark.asyncio
    async def test_execute_tool_rate_limit(self, registry):
        """Test tool execution rate limiting."""
        async def fast_handler(arguments):
            return [types.TextContent(type="text", text="result")]
        
        metadata = ToolMetadata(
            name="rate_limited",
            description="Rate limited tool",
            category=ToolCategory.UTILITIES,
            rate_limit=2  # Very low limit
        )
        
        tool_spec = types.Tool(name="rate_limited", description="Rate limited", inputSchema={})
        
        registry.register_tool("rate_limited", fast_handler, tool_spec, metadata)
        
        # First two calls should succeed
        await registry.execute_tool("rate_limited", {})
        await registry.execute_tool("rate_limited", {})
        
        # Third call should hit rate limit
        with pytest.raises(RuntimeError, match="Rate limit exceeded"):
            await registry.execute_tool("rate_limited", {})
    
    def test_set_tool_status(self, registry, sample_tool_spec, sample_metadata, sample_handler):
        """Test setting tool status."""
        registry.register_tool("status_tool", sample_handler, sample_tool_spec, sample_metadata)
        
        success = registry.set_tool_status("status_tool", ToolStatus.INACTIVE)
        
        assert success is True
        assert registry.tools["status_tool"].status == ToolStatus.INACTIVE
    
    def test_set_tool_status_not_found(self, registry):
        """Test setting status for non-existent tool."""
        success = registry.set_tool_status("nonexistent", ToolStatus.INACTIVE)
        assert success is False
    
    def test_update_tool_config(self, registry, sample_tool_spec, sample_metadata, sample_handler):
        """Test updating tool configuration."""
        registry.register_tool("config_tool", sample_handler, sample_tool_spec, sample_metadata)
        
        new_config = {"setting1": "value1", "setting2": 42}
        success = registry.update_tool_config("config_tool", new_config)
        
        assert success is True
        assert registry.tools["config_tool"].config == new_config
    
    def test_update_tool_config_not_found(self, registry):
        """Test updating config for non-existent tool."""
        success = registry.update_tool_config("nonexistent", {})
        assert success is False
    
    def test_get_tool_info(self, registry, sample_tool_spec, sample_metadata, sample_handler):
        """Test getting tool information."""
        registry.register_tool("info_tool", sample_handler, sample_tool_spec, sample_metadata)
        
        info = registry.get_tool_info("info_tool")
        
        assert info is not None
        assert info["name"] == "info_tool"
        assert "metadata" in info
        assert "status" in info
        assert "usage_stats" in info
        assert "config" in info
        assert "tool_spec" in info
    
    def test_get_tool_info_not_found(self, registry):
        """Test getting info for non-existent tool."""
        info = registry.get_tool_info("nonexistent")
        assert info is None
    
    def test_list_tools(self, registry, sample_tool_spec, sample_handler):
        """Test listing tools."""
        # Register tools in different categories
        search_metadata = ToolMetadata(
            name="search_tool",
            description="Search tool",
            category=ToolCategory.SEARCH
        )
        analytics_metadata = ToolMetadata(
            name="analytics_tool",
            description="Analytics tool",
            category=ToolCategory.ANALYTICS
        )
        
        registry.register_tool("search_tool", sample_handler, sample_tool_spec, search_metadata)
        registry.register_tool("analytics_tool", sample_handler, sample_tool_spec, analytics_metadata)
        
        # List all tools
        all_tools = registry.list_tools()
        assert len(all_tools) == 2
        
        # List by category
        search_tools = registry.list_tools(category=ToolCategory.SEARCH)
        assert len(search_tools) == 1
        assert search_tools[0]["name"] == "search_tool"
        
        # List by status
        registry.set_tool_status("analytics_tool", ToolStatus.INACTIVE)
        active_tools = registry.list_tools(status=ToolStatus.ACTIVE)
        assert len(active_tools) == 1
        assert active_tools[0]["name"] == "search_tool"
    
    def test_get_registry_stats(self, registry, sample_tool_spec, sample_metadata, sample_handler):
        """Test getting registry statistics."""
        # Register some tools
        registry.register_tool("tool1", sample_handler, sample_tool_spec, sample_metadata)
        
        analytics_metadata = ToolMetadata(
            name="tool2",
            description="Tool 2",
            category=ToolCategory.ANALYTICS
        )
        registry.register_tool("tool2", sample_handler, sample_tool_spec, analytics_metadata)
        
        stats = registry.get_registry_stats()
        
        assert "registry_info" in stats
        assert "category_distribution" in stats
        assert "usage_summary" in stats
        
        registry_info = stats["registry_info"]
        assert registry_info["total_tools"] == 2
        assert registry_info["active_tools"] == 2
        assert registry_info["inactive_tools"] == 0
        
        category_dist = stats["category_distribution"]
        assert category_dist.get("search", 0) == 1
        assert category_dist.get("analytics", 0) == 1
    
    def test_save_configuration(self, registry, sample_tool_spec, sample_metadata, sample_handler):
        """Test saving configuration."""
        with NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_file = f.name
        
        try:
            registry.config_file = config_file
            registry.register_tool("save_tool", sample_handler, sample_tool_spec, sample_metadata)
            
            success = registry.save_configuration()
            
            assert success is True
            assert Path(config_file).exists()
            
            # Verify saved content
            with open(config_file, 'r') as f:
                saved_config = json.load(f)
            
            assert "tools" in saved_config
            assert "save_tool" in saved_config["tools"]
            
        finally:
            if Path(config_file).exists():
                os.unlink(config_file)

class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_create_tool_spec(self):
        """Test creating tool specification."""
        spec = create_tool_spec(
            "test_tool",
            "Test tool description",
            {"type": "object", "properties": {"input": {"type": "string"}}}
        )
        
        assert isinstance(spec, types.Tool)
        assert spec.name == "test_tool"
        assert spec.description == "Test tool description"
        assert spec.inputSchema["type"] == "object"
    
    def test_tool_metadata_helper(self):
        """Test tool metadata helper function."""
        metadata = tool_metadata(
            "helper_tool",
            "Helper tool description",
            ToolCategory.UTILITIES,
            version="2.0.0",
            author="Test Author"
        )
        
        assert isinstance(metadata, ToolMetadata)
        assert metadata.name == "helper_tool"
        assert metadata.description == "Helper tool description"
        assert metadata.category == ToolCategory.UTILITIES
        assert metadata.version == "2.0.0"
        assert metadata.author == "Test Author"
    
    def test_register_mcp_tool_decorator(self):
        """Test MCP tool registration decorator."""
        registry = MCPToolRegistry()
        
        @register_mcp_tool(
            registry,
            "decorated_tool",
            "Decorated tool",
            ToolCategory.UTILITIES,
            {"type": "object", "properties": {"input": {"type": "string"}}}
        )
        async def decorated_tool_handler(arguments):
            return [types.TextContent(type="text", text="decorated result")]
        
        assert "decorated_tool" in registry.tools
        assert registry.tools["decorated_tool"].metadata.name == "decorated_tool"
        assert registry.tools["decorated_tool"].metadata.category == ToolCategory.UTILITIES

if __name__ == "__main__":
    pytest.main([__file__, "-v"])