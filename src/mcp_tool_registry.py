#!/usr/bin/env python3
"""
MCP Tool Registration System for Ptolemies
Dynamic tool registration and management system for MCP server capabilities.
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Callable, Union, Type
from dataclasses import dataclass, asdict
from enum import Enum
from abc import ABC, abstractmethod
import inspect
from pathlib import Path

import mcp.types as types
import logfire

# Configure Logfire
logfire.configure(send_to_logfire=False)

class ToolCategory(Enum):
    """Categories for MCP tools."""
    SEARCH = "search"
    INDEXING = "indexing"
    ANALYTICS = "analytics"
    MANAGEMENT = "management"
    UTILITIES = "utilities"
    CUSTOM = "custom"

class ToolStatus(Enum):
    """Status of registered tools."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISABLED = "disabled"
    ERROR = "error"

@dataclass
class ToolMetadata:
    """Metadata for registered tools."""
    name: str
    description: str
    category: ToolCategory
    version: str = "1.0.0"
    author: Optional[str] = None
    tags: List[str] = None
    requires_auth: bool = False
    rate_limit: Optional[int] = None  # requests per minute
    timeout_seconds: int = 30
    cache_ttl_seconds: Optional[int] = None
    dependencies: List[str] = None
    experimental: bool = False
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.dependencies is None:
            self.dependencies = []

@dataclass
class ToolUsageStats:
    """Usage statistics for tools."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_execution_time_ms: float = 0.0
    avg_execution_time_ms: float = 0.0
    last_called_at: Optional[float] = None
    last_error: Optional[str] = None
    rate_limit_hits: int = 0

@dataclass
class RegisteredTool:
    """Represents a registered MCP tool."""
    tool_spec: types.Tool
    handler: Callable
    metadata: ToolMetadata
    status: ToolStatus = ToolStatus.ACTIVE
    registered_at: float = None
    usage_stats: ToolUsageStats = None
    config: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.registered_at is None:
            self.registered_at = time.time()
        if self.usage_stats is None:
            self.usage_stats = ToolUsageStats()
        if self.config is None:
            self.config = {}

class BaseMCPTool(ABC):
    """Base class for MCP tools."""
    
    def __init__(self, metadata: ToolMetadata):
        self.metadata = metadata
        self.usage_stats = ToolUsageStats()
        self.config = {}
    
    @abstractmethod
    async def execute(self, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Execute the tool with given arguments."""
        pass
    
    @abstractmethod
    def get_tool_spec(self) -> types.Tool:
        """Get the MCP tool specification."""
        pass
    
    def validate_arguments(self, arguments: Dict[str, Any]) -> bool:
        """Validate tool arguments."""
        return True
    
    def get_usage_stats(self) -> ToolUsageStats:
        """Get tool usage statistics."""
        return self.usage_stats

class MCPToolRegistry:
    """Registry for managing MCP tools dynamically."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.tools: Dict[str, RegisteredTool] = {}
        self.tool_instances: Dict[str, BaseMCPTool] = {}
        self.rate_limiters: Dict[str, Dict[str, Any]] = {}
        self.config_file = config_file
        self.registry_start_time = time.time()
        
        # Load configuration if provided
        if config_file and Path(config_file).exists():
            self._load_configuration()
    
    @logfire.instrument("register_tool")
    def register_tool(
        self,
        name: str,
        handler: Union[Callable, BaseMCPTool],
        tool_spec: types.Tool,
        metadata: ToolMetadata,
        config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Register a new MCP tool."""
        try:
            with logfire.span("Registering MCP tool", tool_name=name):
                # Validate tool name uniqueness
                if name in self.tools:
                    logfire.warning("Tool already registered", tool_name=name)
                    return False
                
                # Validate handler
                if isinstance(handler, BaseMCPTool):
                    actual_handler = handler.execute
                    self.tool_instances[name] = handler
                else:
                    actual_handler = handler
                
                if not callable(actual_handler):
                    raise ValueError(f"Handler for tool '{name}' is not callable")
                
                # Validate tool spec
                if not isinstance(tool_spec, types.Tool):
                    raise ValueError(f"Tool spec for '{name}' must be a types.Tool instance")
                
                # Create registered tool
                registered_tool = RegisteredTool(
                    tool_spec=tool_spec,
                    handler=actual_handler,
                    metadata=metadata,
                    config=config or {}
                )
                
                # Initialize rate limiter if needed
                if metadata.rate_limit:
                    self.rate_limiters[name] = {
                        "requests": [],
                        "limit": metadata.rate_limit
                    }
                
                # Store tool
                self.tools[name] = registered_tool
                
                logfire.info("Tool registered successfully", 
                           tool_name=name,
                           category=metadata.category.value,
                           version=metadata.version)
                
                return True
                
        except Exception as e:
            logfire.error("Failed to register tool", tool_name=name, error=str(e))
            return False
    
    @logfire.instrument("unregister_tool")
    def unregister_tool(self, name: str) -> bool:
        """Unregister an MCP tool."""
        try:
            if name not in self.tools:
                logfire.warning("Tool not found for unregistration", tool_name=name)
                return False
            
            # Remove tool and associated data
            del self.tools[name]
            if name in self.tool_instances:
                del self.tool_instances[name]
            if name in self.rate_limiters:
                del self.rate_limiters[name]
            
            logfire.info("Tool unregistered successfully", tool_name=name)
            return True
            
        except Exception as e:
            logfire.error("Failed to unregister tool", tool_name=name, error=str(e))
            return False
    
    @logfire.instrument("get_tool_specs")
    def get_tool_specs(self, category: Optional[ToolCategory] = None) -> List[types.Tool]:
        """Get tool specifications for MCP server."""
        try:
            tool_specs = []
            
            for name, registered_tool in self.tools.items():
                # Filter by category if specified
                if category and registered_tool.metadata.category != category:
                    continue
                
                # Only include active tools
                if registered_tool.status == ToolStatus.ACTIVE:
                    tool_specs.append(registered_tool.tool_spec)
            
            logfire.info("Retrieved tool specs", 
                       total_tools=len(tool_specs),
                       category=category.value if category else "all")
            
            return tool_specs
            
        except Exception as e:
            logfire.error("Failed to get tool specs", error=str(e))
            return []
    
    @logfire.instrument("execute_tool")
    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Execute a registered tool."""
        if name not in self.tools:
            raise ValueError(f"Tool '{name}' is not registered")
        
        registered_tool = self.tools[name]
        
        # Check tool status
        if registered_tool.status != ToolStatus.ACTIVE:
            raise RuntimeError(f"Tool '{name}' is not active (status: {registered_tool.status.value})")
        
        # Check rate limiting
        if not self._check_rate_limit(name):
            registered_tool.usage_stats.rate_limit_hits += 1
            raise RuntimeError(f"Rate limit exceeded for tool '{name}'")
        
        start_time = time.time()
        try:
            with logfire.span("Executing tool", tool_name=name):
                # Validate arguments if tool instance available
                if name in self.tool_instances:
                    tool_instance = self.tool_instances[name]
                    if not tool_instance.validate_arguments(arguments):
                        raise ValueError(f"Invalid arguments for tool '{name}'")
                
                # Execute tool with timeout
                try:
                    result = await asyncio.wait_for(
                        registered_tool.handler(arguments),
                        timeout=registered_tool.metadata.timeout_seconds
                    )
                except asyncio.TimeoutError:
                    raise RuntimeError(f"Tool '{name}' execution timed out")
                
                # Update success statistics
                execution_time_ms = (time.time() - start_time) * 1000
                self._update_tool_stats(name, execution_time_ms, success=True)
                
                logfire.info("Tool executed successfully",
                           tool_name=name,
                           execution_time_ms=execution_time_ms)
                
                return result
                
        except Exception as e:
            # Update failure statistics
            execution_time_ms = (time.time() - start_time) * 1000
            self._update_tool_stats(name, execution_time_ms, success=False, error=str(e))
            
            logfire.error("Tool execution failed",
                        tool_name=name,
                        error=str(e),
                        execution_time_ms=execution_time_ms)
            
            raise
    
    def _check_rate_limit(self, tool_name: str) -> bool:
        """Check if tool execution is within rate limits."""
        if tool_name not in self.rate_limiters:
            return True
        
        rate_limiter = self.rate_limiters[tool_name]
        current_time = time.time()
        
        # Remove requests older than 1 minute
        rate_limiter["requests"] = [
            req_time for req_time in rate_limiter["requests"]
            if current_time - req_time < 60
        ]
        
        # Check if under limit
        if len(rate_limiter["requests"]) >= rate_limiter["limit"]:
            return False
        
        # Add current request
        rate_limiter["requests"].append(current_time)
        return True
    
    def _update_tool_stats(self, tool_name: str, execution_time_ms: float, success: bool, error: Optional[str] = None):
        """Update tool usage statistics."""
        if tool_name not in self.tools:
            return
        
        stats = self.tools[tool_name].usage_stats
        
        stats.total_calls += 1
        stats.total_execution_time_ms += execution_time_ms
        stats.last_called_at = time.time()
        
        if success:
            stats.successful_calls += 1
        else:
            stats.failed_calls += 1
            stats.last_error = error
        
        # Update average execution time
        if stats.total_calls > 0:
            stats.avg_execution_time_ms = stats.total_execution_time_ms / stats.total_calls
    
    @logfire.instrument("set_tool_status")
    def set_tool_status(self, name: str, status: ToolStatus) -> bool:
        """Set tool status."""
        try:
            if name not in self.tools:
                logfire.warning("Tool not found for status update", tool_name=name)
                return False
            
            self.tools[name].status = status
            
            logfire.info("Tool status updated", 
                       tool_name=name, 
                       new_status=status.value)
            
            return True
            
        except Exception as e:
            logfire.error("Failed to update tool status", 
                        tool_name=name, 
                        error=str(e))
            return False
    
    @logfire.instrument("update_tool_config")
    def update_tool_config(self, name: str, config: Dict[str, Any]) -> bool:
        """Update tool configuration."""
        try:
            if name not in self.tools:
                logfire.warning("Tool not found for config update", tool_name=name)
                return False
            
            self.tools[name].config.update(config)
            
            logfire.info("Tool config updated", 
                       tool_name=name, 
                       config_keys=list(config.keys()))
            
            return True
            
        except Exception as e:
            logfire.error("Failed to update tool config", 
                        tool_name=name, 
                        error=str(e))
            return False
    
    def get_tool_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive tool information."""
        if name not in self.tools:
            return None
        
        registered_tool = self.tools[name]
        
        return {
            "name": name,
            "metadata": asdict(registered_tool.metadata),
            "status": registered_tool.status.value,
            "registered_at": registered_tool.registered_at,
            "usage_stats": asdict(registered_tool.usage_stats),
            "config": registered_tool.config,
            "tool_spec": {
                "name": registered_tool.tool_spec.name,
                "description": registered_tool.tool_spec.description,
                "input_schema": registered_tool.tool_spec.inputSchema
            }
        }
    
    def list_tools(self, category: Optional[ToolCategory] = None, status: Optional[ToolStatus] = None) -> List[Dict[str, Any]]:
        """List all registered tools with optional filtering."""
        tools_info = []
        
        for name, registered_tool in self.tools.items():
            # Apply filters
            if category and registered_tool.metadata.category != category:
                continue
            if status and registered_tool.status != status:
                continue
            
            tools_info.append({
                "name": name,
                "description": registered_tool.metadata.description,
                "category": registered_tool.metadata.category.value,
                "version": registered_tool.metadata.version,
                "status": registered_tool.status.value,
                "total_calls": registered_tool.usage_stats.total_calls,
                "success_rate": (
                    registered_tool.usage_stats.successful_calls / 
                    max(registered_tool.usage_stats.total_calls, 1)
                ) * 100,
                "avg_execution_time_ms": registered_tool.usage_stats.avg_execution_time_ms
            })
        
        return tools_info
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry-wide statistics."""
        total_tools = len(self.tools)
        active_tools = sum(1 for tool in self.tools.values() if tool.status == ToolStatus.ACTIVE)
        
        category_counts = {}
        for tool in self.tools.values():
            category = tool.metadata.category.value
            category_counts[category] = category_counts.get(category, 0) + 1
        
        total_calls = sum(tool.usage_stats.total_calls for tool in self.tools.values())
        total_successful_calls = sum(tool.usage_stats.successful_calls for tool in self.tools.values())
        
        return {
            "registry_info": {
                "total_tools": total_tools,
                "active_tools": active_tools,
                "inactive_tools": total_tools - active_tools,
                "uptime_seconds": time.time() - self.registry_start_time
            },
            "category_distribution": category_counts,
            "usage_summary": {
                "total_calls": total_calls,
                "total_successful_calls": total_successful_calls,
                "overall_success_rate": (total_successful_calls / max(total_calls, 1)) * 100
            }
        }
    
    def _load_configuration(self):
        """Load tool configurations from file."""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            logfire.info("Tool registry configuration loaded", 
                       config_file=self.config_file)
                       
        except Exception as e:
            logfire.error("Failed to load tool registry configuration", 
                        config_file=self.config_file, 
                        error=str(e))
    
    def save_configuration(self):
        """Save current tool configurations to file."""
        if not self.config_file:
            return False
        
        try:
            config = {
                "tools": {
                    name: {
                        "metadata": asdict(tool.metadata),
                        "status": tool.status.value,
                        "config": tool.config
                    }
                    for name, tool in self.tools.items()
                }
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2, default=str)
            
            logfire.info("Tool registry configuration saved", 
                       config_file=self.config_file)
            return True
            
        except Exception as e:
            logfire.error("Failed to save tool registry configuration", 
                        config_file=self.config_file, 
                        error=str(e))
            return False

# Utility functions for tool registration
def create_tool_spec(
    name: str,
    description: str,
    input_schema: Dict[str, Any]
) -> types.Tool:
    """Helper function to create MCP tool specification."""
    return types.Tool(
        name=name,
        description=description,
        inputSchema=input_schema
    )

def tool_metadata(
    name: str,
    description: str,
    category: ToolCategory,
    **kwargs
) -> ToolMetadata:
    """Helper function to create tool metadata."""
    return ToolMetadata(
        name=name,
        description=description,
        category=category,
        **kwargs
    )

# Decorator for easy tool registration
def register_mcp_tool(
    registry: MCPToolRegistry,
    name: str,
    description: str,
    category: ToolCategory,
    input_schema: Dict[str, Any],
    **metadata_kwargs
):
    """Decorator for registering MCP tools."""
    def decorator(func):
        tool_spec = create_tool_spec(name, description, input_schema)
        metadata = tool_metadata(name, description, category, **metadata_kwargs)
        
        registry.register_tool(name, func, tool_spec, metadata)
        return func
    
    return decorator

if __name__ == "__main__":
    # Example usage
    async def main():
        # Create registry
        registry = MCPToolRegistry()
        
        # Example tool metadata
        metadata = ToolMetadata(
            name="example_search",
            description="Example search tool",
            category=ToolCategory.SEARCH,
            version="1.0.0",
            rate_limit=10
        )
        
        # Example tool spec
        tool_spec = types.Tool(
            name="example_search",
            description="Example search tool",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        )
        
        # Example handler
        async def example_handler(arguments):
            query = arguments["query"]
            return [types.TextContent(
                type="text",
                text=f"Search results for: {query}"
            )]
        
        # Register tool
        success = registry.register_tool("example_search", example_handler, tool_spec, metadata)
        print(f"Tool registered: {success}")
        
        # Execute tool
        result = await registry.execute_tool("example_search", {"query": "test"})
        print(f"Tool result: {result}")
        
        # Get registry stats
        stats = registry.get_registry_stats()
        print(f"Registry stats: {stats}")
    
    asyncio.run(main())