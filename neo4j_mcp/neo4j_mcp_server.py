#!/usr/bin/env python3
"""
Neo4j MCP Server

A Model Context Protocol server that provides Neo4j graph database integration.
This server enables natural language interactions with Neo4j databases through
Claude Code and other MCP clients.
"""

import asyncio
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Union

import neo4j
import logfire
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    GetPromptRequest,
    GetPromptResult,
    ListPromptsRequest,
    ListPromptsResult,
    ListResourcesRequest,
    ListResourcesResult,
    ListToolsRequest,
    ListToolsResult,
    Prompt,
    PromptArgument,
    ReadResourceRequest,
    ReadResourceResult,
    Resource,
    TextContent,
    Tool,
)

# Configure logging and Logfire
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Logfire for Neo4j MCP
logfire.configure(send_to_logfire=False)  # Configure appropriately for production

class Neo4jDatabase:
    """Neo4j database connection and query execution."""
    
    def __init__(self, uri: str, username: str, password: str, database: str = "neo4j"):
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        self.driver = None
        self._connect()
    
    @logfire.instrument("neo4j_connect")
    def _connect(self):
        """Establish connection to Neo4j database."""
        with logfire.span("Connecting to Neo4j", uri=self.uri, database=self.database):
            try:
                logfire.info("Establishing Neo4j connection", uri=self.uri, username=self.username)
                
                self.driver = neo4j.GraphDatabase.driver(
                    self.uri, 
                    auth=(self.username, self.password)
                )
                
                # Test connection
                with self.driver.session(database=self.database) as session:
                    session.run("RETURN 1")
                
                logger.info(f"Connected to Neo4j database: {self.database}")
                logfire.info("Neo4j connection established successfully", database=self.database)
                
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j: {e}")
                logfire.error("Neo4j connection failed", error=str(e), uri=self.uri)
                raise
    
    @logfire.instrument("neo4j_execute_query") 
    def execute_query(self, query: str, parameters: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a Cypher query and return results."""
        if not self.driver:
            raise RuntimeError("No database connection")
        
        parameters = parameters or {}
        
        with logfire.span("Executing Cypher query", query=query[:100], parameter_count=len(parameters)):
            logfire.info("Starting Cypher query execution", 
                        query_length=len(query), 
                        has_parameters=len(parameters) > 0)
            
            try:
                with self.driver.session(database=self.database) as session:
                    result = session.run(query, parameters)
                
                # Extract results
                records = []
                for record in result:
                    records.append(dict(record))
                
                # Get summary information
                summary = result.consume()
                
                # Log query performance metrics
                logfire.info("Cypher query completed successfully",
                           result_count=len(records),
                           result_available_after=summary.result_available_after,
                           result_consumed_after=summary.result_consumed_after,
                           nodes_created=summary.counters.nodes_created,
                           relationships_created=summary.counters.relationships_created)
                
                return {
                    "records": records,
                    "summary": {
                        "query": query,
                        "parameters": parameters,
                        "result_count": len(records),
                        "result_available_after": summary.result_available_after,
                        "result_consumed_after": summary.result_consumed_after,
                        "server_info": {
                            "address": summary.server.address,
                            "protocol_version": str(summary.server.protocol_version),
                        },
                        "database": summary.database,
                        "query_type": summary.query_type,
                        "plan": summary.plan.arguments if summary.plan else None,
                        "profile": summary.profile.arguments if summary.profile else None,
                        "notifications": [n.description for n in summary.notifications] if summary.notifications else [],
                        "counters": {
                            "nodes_created": summary.counters.nodes_created,
                            "nodes_deleted": summary.counters.nodes_deleted,
                            "relationships_created": summary.counters.relationships_created,
                            "relationships_deleted": summary.counters.relationships_deleted,
                            "properties_set": summary.counters.properties_set,
                            "labels_added": summary.counters.labels_added,
                            "labels_removed": summary.counters.labels_removed,
                            "indexes_added": summary.counters.indexes_added,
                            "indexes_removed": summary.counters.indexes_removed,
                            "constraints_added": summary.counters.constraints_added,
                            "constraints_removed": summary.counters.constraints_removed,
                        }
                    }
                }
            except Exception as e:
                logger.error(f"Query execution failed: {e}")
                logfire.error("Cypher query execution failed", 
                            error=str(e), 
                            query=query[:100],
                            parameter_count=len(parameters))
                return {
                    "error": str(e),
                    "query": query,
                    "parameters": parameters
                }
    
    @logfire.instrument("neo4j_get_schema")
    def get_schema(self) -> Dict[str, Any]:
        """Get database schema information."""
        schema_info = {}
        
        with logfire.span("Retrieving Neo4j schema"):
            logfire.info("Starting schema retrieval")
            
            try:
                with self.driver.session(database=self.database) as session:
                    # Get node labels
                    result = session.run("CALL db.labels()")
                    schema_info["labels"] = [record["label"] for record in result]
                
                    # Get relationship types
                    result = session.run("CALL db.relationshipTypes()")
                    schema_info["relationship_types"] = [record["relationshipType"] for record in result]
                    
                    # Get property keys
                    result = session.run("CALL db.propertyKeys()")
                    schema_info["property_keys"] = [record["propertyKey"] for record in result]
                    
                    # Get indexes
                    result = session.run("SHOW INDEXES")
                    schema_info["indexes"] = [dict(record) for record in result]
                    
                    # Get constraints
                    result = session.run("SHOW CONSTRAINTS")
                    schema_info["constraints"] = [dict(record) for record in result]
                
                # Log schema statistics
                logfire.info("Schema retrieval completed successfully",
                           labels_count=len(schema_info.get("labels", [])),
                           relationship_types_count=len(schema_info.get("relationship_types", [])),
                           property_keys_count=len(schema_info.get("property_keys", [])),
                           indexes_count=len(schema_info.get("indexes", [])),
                           constraints_count=len(schema_info.get("constraints", [])))
                
            except Exception as e:
                logger.error(f"Schema retrieval failed: {e}")
                logfire.error("Schema retrieval failed", error=str(e))
                schema_info["error"] = str(e)
        
        return schema_info
    
    @logfire.instrument("neo4j_close")
    def close(self):
        """Close database connection."""
        with logfire.span("Closing Neo4j connection"):
            if self.driver:
                self.driver.close()
                logger.info("Neo4j connection closed")
                logfire.info("Neo4j connection closed successfully")
            else:
                logfire.warning("Attempted to close already closed Neo4j connection")


class Neo4jMCPServer:
    """Neo4j MCP Server implementation."""
    
    def __init__(self):
        self.server = Server("neo4j-mcp-server")
        self.db = None
        self._setup_handlers()
        self._initialize_database()
    
    @logfire.instrument("neo4j_mcp_initialize")
    def _initialize_database(self):
        """Initialize Neo4j database connection."""
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        username = os.getenv("NEO4J_USERNAME", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        database = os.getenv("NEO4J_DATABASE", "neo4j")
        
        with logfire.span("Initializing Neo4j MCP Server", uri=uri, database=database):
            logfire.info("Initializing Neo4j MCP Server", uri=uri, username=username, database=database)
            
            try:
                self.db = Neo4jDatabase(uri, username, password, database)
                logger.info("Neo4j MCP Server initialized successfully")
                logfire.info("Neo4j MCP Server initialization completed successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Neo4j connection: {e}")
                logfire.error("Neo4j MCP Server initialization failed", error=str(e))
                sys.exit(1)
    
    def _setup_handlers(self):
        """Set up MCP request handlers."""
        
        @self.server.list_tools()
        async def list_tools() -> ListToolsResult:
            return ListToolsResult(
                tools=[
                    Tool(
                        name="execute_cypher_query",
                        description="Execute a Cypher query against the Neo4j database",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "The Cypher query to execute"
                                },
                                "parameters": {
                                    "type": "object",
                                    "description": "Optional parameters for the query",
                                    "additionalProperties": True
                                }
                            },
                            "required": ["query"]
                        }
                    ),
                    Tool(
                        name="get_database_schema",
                        description="Get the schema information of the Neo4j database",
                        inputSchema={
                            "type": "object",
                            "properties": {}
                        }
                    ),
                    Tool(
                        name="create_node",
                        description="Create a new node in the Neo4j database",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "labels": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Labels for the node"
                                },
                                "properties": {
                                    "type": "object",
                                    "description": "Properties for the node",
                                    "additionalProperties": True
                                }
                            },
                            "required": ["labels"]
                        }
                    ),
                    Tool(
                        name="create_relationship",
                        description="Create a relationship between two nodes",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "from_node_query": {
                                    "type": "string",
                                    "description": "Cypher query to find the source node"
                                },
                                "to_node_query": {
                                    "type": "string",
                                    "description": "Cypher query to find the target node"
                                },
                                "relationship_type": {
                                    "type": "string",
                                    "description": "Type of the relationship"
                                },
                                "properties": {
                                    "type": "object",
                                    "description": "Properties for the relationship",
                                    "additionalProperties": True
                                }
                            },
                            "required": ["from_node_query", "to_node_query", "relationship_type"]
                        }
                    )
                ]
            )
        
        @self.server.call_tool()
        @logfire.instrument("neo4j_mcp_call_tool")
        async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            with logfire.span("MCP tool call", tool_name=name, arguments_count=len(arguments)):
                logfire.info("MCP tool call started", tool_name=name, has_arguments=len(arguments) > 0)
                
                try:
                    if name == "execute_cypher_query":
                        query = arguments.get("query")
                        parameters = arguments.get("parameters", {})
                        
                        if not query:
                            raise ValueError("Query is required")
                        
                        result = self.db.execute_query(query, parameters)
                        
                        logfire.info("Cypher query executed via MCP", 
                                   query_length=len(query),
                                   has_error="error" in result,
                                   result_count=result.get("summary", {}).get("result_count", 0))
                        
                        return CallToolResult(
                            content=[
                                TextContent(
                                    type="text",
                                    text=f"Query Results:\n{self._format_query_result(result)}"
                                )
                            ]
                        )
                    
                    elif name == "get_database_schema":
                        schema = self.db.get_schema()
                        
                        logfire.info("Database schema retrieved via MCP",
                                   has_error="error" in schema,
                                   labels_count=len(schema.get("labels", [])),
                                   relationship_types_count=len(schema.get("relationship_types", [])))
                        
                        return CallToolResult(
                            content=[
                                TextContent(
                                    type="text",
                                    text=f"Database Schema:\n{self._format_schema(schema)}"
                                )
                            ]
                        )
                    
                    elif name == "create_node":
                        labels = arguments.get("labels", [])
                        properties = arguments.get("properties", {})
                        
                        if not labels:
                            raise ValueError("At least one label is required")
                        
                        # Build CREATE query
                        labels_str = ":".join(labels)
                        props_str = self._format_properties(properties)
                        query = f"CREATE (n:{labels_str} {props_str}) RETURN n"
                        
                        result = self.db.execute_query(query)
                        
                        return CallToolResult(
                            content=[
                                TextContent(
                                    type="text",
                                    text=f"Node Created:\n{self._format_query_result(result)}"
                                )
                            ]
                        )
                    
                    elif name == "create_relationship":
                        from_query = arguments.get("from_node_query")
                        to_query = arguments.get("to_node_query")
                        rel_type = arguments.get("relationship_type")
                        properties = arguments.get("properties", {})
                        
                        if not all([from_query, to_query, rel_type]):
                            raise ValueError("All relationship parameters are required")
                        
                        # Build relationship creation query
                        props_str = self._format_properties(properties)
                        query = f"""
                        MATCH (a) WHERE {from_query}
                        MATCH (b) WHERE {to_query}
                        CREATE (a)-[r:{rel_type} {props_str}]->(b)
                        RETURN a, r, b
                        """
                        
                        result = self.db.execute_query(query)
                        
                        return CallToolResult(
                            content=[
                                TextContent(
                                    type="text",
                                    text=f"Relationship Created:\n{self._format_query_result(result)}"
                                )
                            ]
                        )
                    
                    else:
                        raise ValueError(f"Unknown tool: {name}")
                        
                except Exception as e:
                    logger.error(f"Tool execution failed: {e}")
                    logfire.error("MCP tool execution failed", 
                                tool_name=name, 
                                error=str(e), 
                                error_type=type(e).__name__)
                    
                    return CallToolResult(
                        content=[
                            TextContent(
                                type="text",
                                text=f"Error: {str(e)}"
                            )
                        ],
                        isError=True
                    )
                
                finally:
                    logfire.info("MCP tool call completed", tool_name=name)
        
        @self.server.list_resources()
        @logfire.instrument("neo4j_mcp_list_resources")
        async def list_resources() -> ListResourcesResult:
            return ListResourcesResult(
                resources=[
                    Resource(
                        uri="neo4j://schema",
                        name="Database Schema",
                        description="Neo4j database schema information",
                        mimeType="application/json"
                    ),
                    Resource(
                        uri="neo4j://connection",
                        name="Connection Info",
                        description="Neo4j connection information",
                        mimeType="application/json"
                    )
                ]
            )
        
        @self.server.read_resource()
        @logfire.instrument("neo4j_mcp_read_resource")
        async def read_resource(uri: str) -> ReadResourceResult:
            if uri == "neo4j://schema":
                schema = self.db.get_schema()
                return ReadResourceResult(
                    contents=[
                        TextContent(
                            type="text",
                            text=self._format_schema(schema)
                        )
                    ]
                )
            elif uri == "neo4j://connection":
                connection_info = {
                    "uri": self.db.uri,
                    "database": self.db.database,
                    "username": self.db.username,
                    "status": "connected" if self.db.driver else "disconnected"
                }
                return ReadResourceResult(
                    contents=[
                        TextContent(
                            type="text",
                            text=f"Connection Info:\n{self._format_dict(connection_info)}"
                        )
                    ]
                )
            else:
                raise ValueError(f"Unknown resource: {uri}")
        
        @self.server.list_prompts()
        @logfire.instrument("neo4j_mcp_list_prompts")
        async def list_prompts() -> ListPromptsResult:
            return ListPromptsResult(
                prompts=[
                    Prompt(
                        name="cypher_query_helper",
                        description="Help with Cypher query construction",
                        arguments=[
                            PromptArgument(
                                name="intent",
                                description="What you want to accomplish with the query",
                                required=True
                            )
                        ]
                    ),
                    Prompt(
                        name="graph_analysis",
                        description="Analyze graph structure and patterns",
                        arguments=[
                            PromptArgument(
                                name="focus",
                                description="What aspect of the graph to analyze",
                                required=True
                            )
                        ]
                    )
                ]
            )
        
        @self.server.get_prompt()
        @logfire.instrument("neo4j_mcp_get_prompt")
        async def get_prompt(name: str, arguments: Dict[str, str]) -> GetPromptResult:
            if name == "cypher_query_helper":
                intent = arguments.get("intent", "")
                schema = self.db.get_schema()
                
                prompt_text = f"""
                Help me write a Cypher query for: {intent}
                
                Available labels: {', '.join(schema.get('labels', []))}
                Available relationship types: {', '.join(schema.get('relationship_types', []))}
                Available properties: {', '.join(schema.get('property_keys', []))}
                
                Please provide a Cypher query that accomplishes this goal.
                """
                
                return GetPromptResult(
                    description="Cypher query construction assistance",
                    messages=[
                        {
                            "role": "user",
                            "content": {
                                "type": "text",
                                "text": prompt_text
                            }
                        }
                    ]
                )
            
            elif name == "graph_analysis":
                focus = arguments.get("focus", "")
                
                prompt_text = f"""
                Analyze the Neo4j graph with focus on: {focus}
                
                Consider:
                - Node distribution and patterns
                - Relationship patterns and density
                - Data quality and completeness
                - Performance considerations
                - Potential insights or anomalies
                
                Please provide an analysis query and interpretation approach.
                """
                
                return GetPromptResult(
                    description="Graph analysis guidance",
                    messages=[
                        {
                            "role": "user",
                            "content": {
                                "type": "text",
                                "text": prompt_text
                            }
                        }
                    ]
                )
            
            else:
                raise ValueError(f"Unknown prompt: {name}")
    
    def _format_query_result(self, result: Dict[str, Any]) -> str:
        """Format query result for display."""
        if "error" in result:
            return f"Error: {result['error']}"
        
        formatted = []
        
        # Add summary
        summary = result.get("summary", {})
        formatted.append(f"Query: {summary.get('query', 'N/A')}")
        formatted.append(f"Records returned: {summary.get('result_count', 0)}")
        
        if summary.get("counters"):
            counters = summary["counters"]
            changes = []
            for key, value in counters.items():
                if value > 0:
                    changes.append(f"{key}: {value}")
            if changes:
                formatted.append(f"Changes: {', '.join(changes)}")
        
        # Add records
        records = result.get("records", [])
        if records:
            formatted.append("\nRecords:")
            for i, record in enumerate(records[:10]):  # Limit to first 10 records
                formatted.append(f"  {i+1}: {record}")
            if len(records) > 10:
                formatted.append(f"  ... and {len(records) - 10} more records")
        
        return "\n".join(formatted)
    
    def _format_schema(self, schema: Dict[str, Any]) -> str:
        """Format schema information for display."""
        if "error" in schema:
            return f"Error retrieving schema: {schema['error']}"
        
        formatted = []
        
        labels = schema.get("labels", [])
        if labels:
            formatted.append(f"Labels ({len(labels)}): {', '.join(labels)}")
        
        rel_types = schema.get("relationship_types", [])
        if rel_types:
            formatted.append(f"Relationship Types ({len(rel_types)}): {', '.join(rel_types)}")
        
        properties = schema.get("property_keys", [])
        if properties:
            formatted.append(f"Property Keys ({len(properties)}): {', '.join(properties)}")
        
        indexes = schema.get("indexes", [])
        if indexes:
            formatted.append(f"\nIndexes ({len(indexes)}):")
            for idx in indexes:
                formatted.append(f"  - {idx.get('name', 'N/A')}: {idx.get('type', 'N/A')}")
        
        constraints = schema.get("constraints", [])
        if constraints:
            formatted.append(f"\nConstraints ({len(constraints)}):")
            for constraint in constraints:
                formatted.append(f"  - {constraint.get('name', 'N/A')}: {constraint.get('type', 'N/A')}")
        
        return "\n".join(formatted)
    
    def _format_properties(self, properties: Dict[str, Any]) -> str:
        """Format properties for Cypher query."""
        if not properties:
            return ""
        
        prop_pairs = []
        for key, value in properties.items():
            if isinstance(value, str):
                prop_pairs.append(f"{key}: '{value}'")
            else:
                prop_pairs.append(f"{key}: {value}")
        
        return "{" + ", ".join(prop_pairs) + "}"
    
    def _format_dict(self, data: Dict[str, Any]) -> str:
        """Format dictionary for display."""
        formatted = []
        for key, value in data.items():
            formatted.append(f"{key}: {value}")
        return "\n".join(formatted)
    
    @logfire.instrument("neo4j_mcp_run_server")
    async def run(self):
        """Run the MCP server."""
        with logfire.span("Neo4j MCP Server startup"):
            logfire.info("Starting Neo4j MCP Server")
            
            try:
                async with stdio_server() as (read_stream, write_stream):
                    logfire.info("MCP server streams initialized")
                    await self.server.run(
                        read_stream,
                        write_stream,
                        self.server.create_initialization_options()
                    )
            except Exception as e:
                logfire.error("MCP server run failed", error=str(e))
                raise
            finally:
                if self.db:
                    logfire.info("Closing Neo4j MCP Server")
                    self.db.close()


async def main():
    """Main entry point."""
    server = Neo4jMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())