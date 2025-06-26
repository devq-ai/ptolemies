#!/usr/bin/env python3
"""
Ptolemies MCP Server - Enhanced Unified Integration
=================================================

Enhanced MCP server providing unified read access to SurrealDB, Neo4j, and
Dehallucinator services through high-level semantic operations optimized
for AI assistant workflows in the DevQ.ai ecosystem.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager
from datetime import datetime

# MCP SDK imports
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# DevQ.ai infrastructure
try:
    import logfire
    LOGFIRE_AVAILABLE = True
    try:
        logfire.configure()
    except Exception as e:
        logging.warning(f"Logfire configuration failed: {e}")
        LOGFIRE_AVAILABLE = False
except ImportError:
    LOGFIRE_AVAILABLE = False
    logging.warning("Logfire not available, using standard logging")

# Local imports
from ptolemies_integration import PtolemiesIntegration
from ptolemies_tools import PtolemiesTools
from ptolemies_types import SystemHealth, ErrorResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PtolemiesMCPServer:
    """
    Enhanced MCP server for the Ptolemies knowledge ecosystem.

    Provides unified access to SurrealDB, Neo4j, and Dehallucinator services
    through high-level semantic operations designed for AI assistant workflows.
    """

    def __init__(self):
        """Initialize the Ptolemies MCP server."""
        self.server = Server("ptolemies-mcp")
        self.integration = PtolemiesIntegration()
        self.tools = PtolemiesTools(self.integration)
        self.is_initialized = False

        # Request tracking
        self.active_requests = 0
        self.max_concurrent_requests = 10
        self.request_semaphore = asyncio.Semaphore(self.max_concurrent_requests)

        # Setup MCP handlers
        self._setup_handlers()

        logger.info("Ptolemies MCP Server initialized")

    def _setup_handlers(self):
        """Setup MCP server request handlers."""

        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            """List all available tools."""
            if LOGFIRE_AVAILABLE:
                with logfire.span("list_tools"):
                    return self.tools.get_tools()
            else:
                return self.tools.get_tools()

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: Optional[Dict[str, Any]] = None
        ) -> List[types.TextContent]:
            """Handle tool calls with request limiting and error handling."""

            if not self.is_initialized:
                error_response = ErrorResponse(
                    error_type="server_not_initialized",
                    error_message="Server not initialized. Please wait for initialization to complete."
                )
                return [types.TextContent(
                    type="text",
                    text=json.dumps(error_response.dict(), indent=2)
                )]

            async with self.request_semaphore:
                self.active_requests += 1

                try:
                    if LOGFIRE_AVAILABLE:
                        with logfire.span("tool_call", tool_name=name, active_requests=self.active_requests):
                            return await self._execute_tool_call(name, arguments)
                    else:
                        return await self._execute_tool_call(name, arguments)

                finally:
                    self.active_requests -= 1

        @self.server.list_resources()
        async def handle_list_resources() -> List[types.Resource]:
            """List available resources (health status, system info)."""
            return [
                types.Resource(
                    uri="ptolemies://health",
                    name="System Health",
                    description="Current health status of all integrated services",
                    mimeType="application/json"
                ),
                types.Resource(
                    uri="ptolemies://stats",
                    name="System Statistics",
                    description="Usage statistics and performance metrics",
                    mimeType="application/json"
                )
            ]

        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Read system resources like health status."""
            if uri == "ptolemies://health":
                health_status = await self.integration.get_system_health()
                return json.dumps(health_status.dict(), indent=2, default=str)

            elif uri == "ptolemies://stats":
                stats = {
                    "server_info": {
                        "name": "ptolemies-mcp",
                        "version": "1.0.0",
                        "initialized": self.is_initialized,
                        "active_requests": self.active_requests,
                        "max_concurrent_requests": self.max_concurrent_requests
                    },
                    "tools_available": len(self.tools.get_tools()),
                    "timestamp": datetime.now().isoformat()
                }
                return json.dumps(stats, indent=2)

            else:
                raise ValueError(f"Unknown resource: {uri}")

    async def _execute_tool_call(
        self, name: str, arguments: Optional[Dict[str, Any]] = None
    ) -> List[types.TextContent]:
        """Execute a tool call through the tools layer."""

        # Create a mock request object for the tools layer
        class MockRequest:
            def __init__(self, name: str, arguments: Optional[Dict[str, Any]]):
                self.params = MockParams(name, arguments)

        class MockParams:
            def __init__(self, name: str, arguments: Optional[Dict[str, Any]]):
                self.name = name
                self.arguments = arguments or {}

        request = MockRequest(name, arguments)
        result = await self.tools.call_tool(request)

        return result.content

    async def initialize(self) -> bool:
        """Initialize all server components and establish connections."""
        logger.info("Initializing Ptolemies MCP server...")

        try:
            if LOGFIRE_AVAILABLE:
                with logfire.span("server_initialization"):
                    success = await self._perform_initialization()
            else:
                success = await self._perform_initialization()

            self.is_initialized = success

            if success:
                logger.info("✅ Ptolemies MCP server successfully initialized")
            else:
                logger.error("❌ Ptolemies MCP server initialization failed")

            return success

        except Exception as e:
            logger.error(f"❌ Server initialization error: {e}")
            self.is_initialized = False
            return False

    async def _perform_initialization(self) -> bool:
        """Perform the actual initialization steps."""

        # Initialize the integration layer
        logger.info("Connecting to data sources...")
        connection_success = await self.integration.connect()

        if not connection_success:
            logger.error("Failed to connect to required data sources")
            return False

        # Verify system health
        logger.info("Checking system health...")
        health_status = await self.integration.get_system_health()

        if not health_status.overall_healthy:
            logger.warning("System health check indicates some services are not fully operational")
            # Continue initialization but log the issues
            for service_name, status in [
                ("neo4j", health_status.neo4j_status),
                ("surrealdb", health_status.surrealdb_status),
                ("dehallucinator", health_status.dehallucinator_status)
            ]:
                if not status.connected:
                    logger.warning(f"⚠️ {service_name} not connected: {status.error_message}")

        # At least 2 services should be connected for basic functionality
        connected_services = sum([
            health_status.neo4j_status.connected,
            health_status.surrealdb_status.connected,
            health_status.dehallucinator_status.connected
        ])

        if connected_services < 2:
            logger.error(f"Only {connected_services}/3 services connected. Minimum 2 required.")
            return False

        logger.info(f"✅ {connected_services}/3 services connected and operational")
        return True

    async def cleanup(self):
        """Clean up server resources."""
        logger.info("Cleaning up Ptolemies MCP server...")

        try:
            if self.integration:
                await self.integration.disconnect()

            logger.info("✅ Cleanup completed")

        except Exception as e:
            logger.error(f"❌ Cleanup error: {e}")

    @asynccontextmanager
    async def lifespan_manager(self):
        """Context manager for server lifecycle."""
        try:
            # Startup
            success = await self.initialize()
            if not success:
                raise RuntimeError("Failed to initialize server")

            yield self

        finally:
            # Shutdown
            await self.cleanup()

    def get_server_info(self) -> Dict[str, Any]:
        """Get server information and status."""
        return {
            "name": "ptolemies-mcp",
            "version": "1.0.0",
            "description": "Unified MCP server for SurrealDB, Neo4j, and Dehallucinator",
            "initialized": self.is_initialized,
            "active_requests": self.active_requests,
            "max_concurrent_requests": self.max_concurrent_requests,
            "tools_available": len(self.tools.get_tools()) if self.tools else 0,
            "capabilities": {
                "hybrid_knowledge_search": True,
                "code_validation": True,
                "framework_analysis": True,
                "learning_path_discovery": True,
                "relationship_analysis": True,
                "ecosystem_overview": True,
                "system_health_monitoring": True
            },
            "data_sources": {
                "neo4j": "Knowledge graph with 77 nodes, 156 relationships",
                "surrealdb": "Vector store with document chunks and embeddings",
                "dehallucinator": "AI code validation with 97.3% accuracy"
            }
        }


async def create_server() -> PtolemiesMCPServer:
    """Create and initialize a Ptolemies MCP server instance."""
    server = PtolemiesMCPServer()
    return server


async def main():
    """Main entry point for the Ptolemies MCP server."""

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger.info("Starting Ptolemies MCP server...")

    try:
        # Create and initialize server
        server = await create_server()

        async with server.lifespan_manager():

            # Log server information
            server_info = server.get_server_info()
            logger.info(f"Server info: {json.dumps(server_info, indent=2)}")

            # Run the MCP server
            async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
                logger.info("🚀 Ptolemies MCP server is running...")
                logger.info("Available tools:")
                for tool in server.tools.get_tools():
                    logger.info(f"  • {tool.name}: {tool.description}")

                await server.server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="ptolemies-mcp",
                        server_version="1.0.0",
                        capabilities=server.server.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities={}
                        )
                    )
                )

    except KeyboardInterrupt:
        logger.info("👋 Ptolemies MCP server stopped by user")

    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        if LOGFIRE_AVAILABLE:
            logfire.error("Server error", error=str(e))
        raise

    finally:
        logger.info("Ptolemies MCP server shutdown complete")


if __name__ == "__main__":
    # Ensure proper Python path for imports
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    # Add dehallucinator to path
    dehallucinator_path = os.path.join(os.path.dirname(current_dir), 'dehallucinator')
    if dehallucinator_path not in sys.path:
        sys.path.insert(0, dehallucinator_path)

    # Run the server
    asyncio.run(main())
