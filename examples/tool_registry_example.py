#!/usr/bin/env python3
"""
Example: Using the MCP Tool Registry System
Demonstrates how to register custom tools and use them with the MCP server.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_tool_registry import (
    MCPToolRegistry, 
    ToolMetadata, 
    ToolCategory, 
    BaseMCPTool,
    create_tool_spec,
    register_mcp_tool
)
from ptolemies_mcp_server import PtolemiesMCPServer, PtolemiesMCPConfig
import mcp.types as types

# Example 1: Simple function-based tool
async def calculator_tool(arguments):
    """Simple calculator tool."""
    operation = arguments.get("operation", "add")
    a = arguments.get("a", 0)
    b = arguments.get("b", 0)
    
    result = 0
    if operation == "add":
        result = a + b
    elif operation == "subtract":
        result = a - b
    elif operation == "multiply":
        result = a * b
    elif operation == "divide":
        result = a / b if b != 0 else 0
    
    return [types.TextContent(
        type="text",
        text=json.dumps({
            "operation": operation,
            "operands": [a, b],
            "result": result
        }, indent=2)
    )]

# Example 2: Class-based tool using BaseMCPTool
class WeatherTool(BaseMCPTool):
    """Mock weather tool for demonstration."""
    
    def __init__(self):
        metadata = ToolMetadata(
            name="weather_lookup",
            description="Get weather information for a location",
            category=ToolCategory.UTILITIES,
            version="1.1.0",
            author="Example Developer",
            rate_limit=60,  # 60 requests per minute
            timeout_seconds=10
        )
        super().__init__(metadata)
        
        # Mock weather data
        self.weather_data = {
            "san francisco": {"temp": 68, "condition": "foggy"},
            "new york": {"temp": 72, "condition": "sunny"},
            "london": {"temp": 61, "condition": "rainy"},
            "tokyo": {"temp": 75, "condition": "partly cloudy"}
        }
    
    async def execute(self, arguments):
        location = arguments.get("location", "").lower()
        
        if location in self.weather_data:
            weather = self.weather_data[location]
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "location": location.title(),
                    "temperature_f": weather["temp"],
                    "condition": weather["condition"],
                    "timestamp": "2024-12-21T10:00:00Z"
                }, indent=2)
            )]
        else:
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "error": f"Weather data not available for {location}",
                    "available_locations": list(self.weather_data.keys())
                }, indent=2)
            )]
    
    def get_tool_spec(self):
        return create_tool_spec(
            "weather_lookup",
            "Get current weather information for a location",
            {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city or location to get weather for"
                    }
                },
                "required": ["location"]
            }
        )
    
    def validate_arguments(self, arguments):
        return "location" in arguments and isinstance(arguments["location"], str)

async def main():
    """Main example function."""
    print("🔧 MCP Tool Registry Example")
    print("=" * 40)
    
    # Create a tool registry
    registry = MCPToolRegistry()
    
    # Example 1: Register a simple function-based tool
    print("\n1. Registering Calculator Tool...")
    
    calculator_spec = create_tool_spec(
        "calculator",
        "Perform basic mathematical operations",
        {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide"],
                    "description": "Mathematical operation to perform"
                },
                "a": {"type": "number", "description": "First operand"},
                "b": {"type": "number", "description": "Second operand"}
            },
            "required": ["operation", "a", "b"]
        }
    )
    
    calculator_metadata = ToolMetadata(
        name="calculator",
        description="Basic arithmetic calculator",
        category=ToolCategory.UTILITIES,
        version="1.0.0"
    )
    
    success = registry.register_tool(
        "calculator",
        calculator_tool,
        calculator_spec,
        calculator_metadata
    )
    print(f"Calculator tool registered: {success}")
    
    # Example 2: Register a class-based tool
    print("\n2. Registering Weather Tool...")
    
    weather_tool = WeatherTool()
    success = registry.register_tool(
        "weather_lookup",
        weather_tool,
        weather_tool.get_tool_spec(),
        weather_tool.metadata
    )
    print(f"Weather tool registered: {success}")
    
    # Example 3: Using the decorator approach
    print("\n3. Registering Decorator-based Tool...")
    
    @register_mcp_tool(
        registry,
        "joke_generator",
        "Generate programming jokes",
        ToolCategory.UTILITIES,
        {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "enum": ["python", "javascript", "general"],
                    "description": "Topic for the joke",
                    "default": "general"
                }
            }
        },
        version="1.0.0",
        author="Example Developer"
    )
    async def joke_generator(arguments):
        topic = arguments.get("topic", "general")
        
        jokes = {
            "python": "Why do Python programmers prefer snakes? Because they don't like Java!",
            "javascript": "Why do JavaScript developers wear glasses? Because they can't C#!",
            "general": "Why do programmers hate nature? It has too many bugs!"
        }
        
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "topic": topic,
                "joke": jokes.get(topic, jokes["general"])
            }, indent=2)
        )]
    
    print("Joke generator tool registered via decorator")
    
    # List all registered tools
    print("\n4. Listing All Registered Tools...")
    tools = registry.list_tools()
    for tool in tools:
        print(f"  - {tool['name']}: {tool['description']} (Category: {tool['category']})")
    
    # Test tool execution
    print("\n5. Testing Tool Execution...")
    
    # Test calculator
    print("\nTesting Calculator (10 + 5):")
    result = await registry.execute_tool("calculator", {
        "operation": "add",
        "a": 10,
        "b": 5
    })
    print(result[0].text)
    
    # Test weather tool
    print("\nTesting Weather Tool (San Francisco):")
    result = await registry.execute_tool("weather_lookup", {
        "location": "san francisco"
    })
    print(result[0].text)
    
    # Test joke generator
    print("\nTesting Joke Generator (Python topic):")
    result = await registry.execute_tool("joke_generator", {
        "topic": "python"
    })
    print(result[0].text)
    
    # Get registry statistics
    print("\n6. Registry Statistics...")
    stats = registry.get_registry_stats()
    print(f"Total tools: {stats['registry_info']['total_tools']}")
    print(f"Active tools: {stats['registry_info']['active_tools']}")
    print(f"Total calls: {stats['usage_summary']['total_calls']}")
    print(f"Success rate: {stats['usage_summary']['overall_success_rate']:.1f}%")
    
    # Example 4: Integration with MCP Server
    print("\n7. Integration with MCP Server...")
    
    # Create MCP server with tool registry enabled
    config = PtolemiesMCPConfig(
        enable_dynamic_tools=True,
        enable_semantic_search=False,  # Disable for this example
        enable_graph_search=False,
        enable_hybrid_search=False
    )
    
    mcp_server = PtolemiesMCPServer(config)
    
    # Register our custom tools with the MCP server
    print("Registering custom tools with MCP server...")
    
    mcp_server.register_custom_tool(
        "calculator",
        calculator_tool,
        calculator_spec,
        calculator_metadata
    )
    
    mcp_server.register_custom_tool(
        "weather_lookup",
        weather_tool,
        weather_tool.get_tool_spec(),
        weather_tool.metadata
    )
    
    # Get tool information
    print("\nTool information from MCP server:")
    calculator_info = mcp_server.get_tool_info("calculator")
    if calculator_info:
        print(f"Calculator tool: {calculator_info['metadata']['description']}")
        print(f"Usage stats: {calculator_info['usage_stats']['total_calls']} calls")
    
    # List tools by category
    print("\nTools by category:")
    utility_tools = mcp_server.list_tools_by_category("utilities")
    for tool in utility_tools:
        print(f"  - {tool['name']}: {tool['description']}")
    
    print("\n✅ Tool Registry Example Complete!")
    print("\nKey Features Demonstrated:")
    print("- Function-based tool registration")
    print("- Class-based tool with validation")
    print("- Decorator-based tool registration")
    print("- Tool execution and error handling")
    print("- Registry statistics and monitoring")
    print("- Integration with MCP server")
    print("- Rate limiting and timeouts")
    print("- Tool categorization and filtering")

if __name__ == "__main__":
    asyncio.run(main())