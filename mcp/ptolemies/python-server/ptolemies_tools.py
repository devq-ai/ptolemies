#!/usr/bin/env python3
"""
Ptolemies MCP Tools
==================

MCP tool definitions for the unified ptolemies server providing semantic
access to SurrealDB, Neo4j, and Dehallucinator services.
"""

from typing import Dict, List, Optional, Any
import json
import logging
from datetime import datetime

# MCP SDK imports
from mcp.types import Tool, TextContent, CallToolRequest, CallToolResult

# Local imports
from ptolemies_integration import PtolemiesIntegration
from ptolemies_types import ErrorResponse

# DevQ.ai infrastructure
try:
    import logfire
    LOGFIRE_AVAILABLE = True
except ImportError:
    LOGFIRE_AVAILABLE = False

logger = logging.getLogger(__name__)


class PtolemiesTools:
    """
    MCP tools for the ptolemies server.

    Provides high-level semantic operations that combine data from
    SurrealDB, Neo4j, and Dehallucinator services.
    """

    def __init__(self, integration: PtolemiesIntegration):
        """Initialize tools with integration layer."""
        self.integration = integration

        # Tool definitions
        self.tools = self._define_tools()

        logger.info("PtolemiesTools initialized with %d tools", len(self.tools))

    def _define_tools(self) -> List[Tool]:
        """Define all available MCP tools."""
        return [
            # Knowledge Search & Retrieval Tools
            Tool(
                name="hybrid-knowledge-search",
                description="Perform hybrid search combining Neo4j graph traversal with SurrealDB vector search for comprehensive knowledge retrieval",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for knowledge discovery"
                        },
                        "frameworks": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of frameworks to filter results"
                        },
                        "max_results": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 50,
                            "default": 10,
                            "description": "Maximum number of results to return"
                        },
                        "include_code_examples": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include code examples in search results"
                        },
                        "similarity_threshold": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "default": 0.7,
                            "description": "Minimum similarity score for vector search results"
                        }
                    },
                    "required": ["query"]
                }
            ),

            Tool(
                name="framework-knowledge-query",
                description="Query specific framework knowledge with relationship context from Neo4j and relevant documentation from SurrealDB",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "framework": {
                            "type": "string",
                            "description": "Framework name to query"
                        },
                        "topic": {
                            "type": "string",
                            "description": "Specific topic within the framework"
                        },
                        "depth": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 5,
                            "default": 2,
                            "description": "Relationship traversal depth in the knowledge graph"
                        },
                        "include_examples": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include code examples and documentation"
                        }
                    },
                    "required": ["framework", "topic"]
                }
            ),

            Tool(
                name="learning-path-discovery",
                description="Discover learning progression paths between frameworks using Neo4j relationship analysis",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "start_framework": {
                            "type": "string",
                            "description": "Starting framework for the learning path"
                        },
                        "end_framework": {
                            "type": "string",
                            "description": "Target framework for the learning path"
                        },
                        "include_prerequisites": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include prerequisite analysis in the path"
                        },
                        "difficulty_preference": {
                            "type": "string",
                            "enum": ["beginner", "intermediate", "advanced", "any"],
                            "default": "any",
                            "description": "Preferred difficulty level for the learning path"
                        }
                    },
                    "required": ["start_framework", "end_framework"]
                }
            ),

            # Code Validation & Analysis Tools
            Tool(
                name="validate-code-snippet",
                description="Validate code snippet for AI hallucinations using the dehallucinator service with knowledge graph validation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Code snippet to validate for hallucinations"
                        },
                        "framework": {
                            "type": "string",
                            "description": "Expected framework context for validation"
                        },
                        "confidence_threshold": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "default": 0.75,
                            "description": "Minimum confidence threshold for flagging issues"
                        },
                        "include_suggestions": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include improvement suggestions in the response"
                        }
                    },
                    "required": ["code"]
                }
            ),

            Tool(
                name="analyze-framework-usage",
                description="Analyze code for framework usage patterns and provide suggestions based on validated knowledge",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Code snippet to analyze for framework usage patterns"
                        },
                        "detect_patterns": {
                            "type": "boolean",
                            "default": True,
                            "description": "Detect common usage patterns in the code"
                        },
                        "suggest_improvements": {
                            "type": "boolean",
                            "default": True,
                            "description": "Provide improvement suggestions based on best practices"
                        }
                    },
                    "required": ["code"]
                }
            ),

            # Relationship Discovery Tools
            Tool(
                name="framework-dependencies",
                description="Analyze framework dependencies and relationships from the Neo4j knowledge graph",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "framework": {
                            "type": "string",
                            "description": "Framework to analyze for dependencies"
                        },
                        "include_transitive": {
                            "type": "boolean",
                            "default": False,
                            "description": "Include transitive (indirect) dependencies"
                        },
                        "max_depth": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 10,
                            "default": 3,
                            "description": "Maximum traversal depth for dependency analysis"
                        }
                    },
                    "required": ["framework"]
                }
            ),

            Tool(
                name="topic-relationships",
                description="Discover topic relationships and related concepts across the knowledge graph",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "Topic to analyze for relationships"
                        },
                        "relationship_types": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["IMPLEMENTS", "DEPENDS_ON", "DOCUMENTED_BY", "CONTAINS", "RELATED_TO", "INHERITS_FROM", "USES"]
                            },
                            "description": "Specific relationship types to include in analysis"
                        },
                        "max_results": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 50,
                            "default": 20,
                            "description": "Maximum number of relationships to return"
                        }
                    },
                    "required": ["topic"]
                }
            ),

            # Meta-Analysis Tools
            Tool(
                name="knowledge-coverage-analysis",
                description="Analyze documentation coverage and knowledge gaps for a specific framework across all data sources",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "framework": {
                            "type": "string",
                            "description": "Framework to analyze for knowledge coverage"
                        }
                    },
                    "required": ["framework"]
                }
            ),

            Tool(
                name="ecosystem-overview",
                description="Provide comprehensive overview of the DevQ.ai ecosystem including frameworks, relationships, and capabilities",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": ["backend", "frontend", "database", "tool", "library", "all"],
                            "default": "all",
                            "description": "Framework category to focus on for the overview"
                        }
                    }
                }
            ),

            # System Health Tools
            Tool(
                name="system-health-check",
                description="Check the health status of all integrated services (Neo4j, SurrealDB, Dehallucinator)",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            )
        ]

    async def call_tool(self, request: CallToolRequest) -> CallToolResult:
        """Handle MCP tool calls."""
        try:
            if LOGFIRE_AVAILABLE:
                with logfire.span("ptolemies_tool_call", tool_name=request.params.name):
                    return await self._execute_tool(request)
            else:
                return await self._execute_tool(request)

        except Exception as e:
            logger.error(f"Tool call error for {request.params.name}: {e}")

            error_response = ErrorResponse(
                error_type="tool_execution_error",
                error_message=str(e),
                error_details={"tool_name": request.params.name}
            )

            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps(error_response.dict(), indent=2)
                )]
            )

    async def _execute_tool(self, request: CallToolRequest) -> CallToolResult:
        """Execute the requested tool."""
        tool_name = request.params.name
        args = request.params.arguments or {}

        # Route to appropriate tool handler
        if tool_name == "hybrid-knowledge-search":
            result = await self._hybrid_knowledge_search(args)
        elif tool_name == "framework-knowledge-query":
            result = await self._framework_knowledge_query(args)
        elif tool_name == "learning-path-discovery":
            result = await self._learning_path_discovery(args)
        elif tool_name == "validate-code-snippet":
            result = await self._validate_code_snippet(args)
        elif tool_name == "analyze-framework-usage":
            result = await self._analyze_framework_usage(args)
        elif tool_name == "framework-dependencies":
            result = await self._framework_dependencies(args)
        elif tool_name == "topic-relationships":
            result = await self._topic_relationships(args)
        elif tool_name == "knowledge-coverage-analysis":
            result = await self._knowledge_coverage_analysis(args)
        elif tool_name == "ecosystem-overview":
            result = await self._ecosystem_overview(args)
        elif tool_name == "system-health-check":
            result = await self._system_health_check(args)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps(result, indent=2, default=str)
            )]
        )

    # === Tool Implementation Methods ===

    async def _hybrid_knowledge_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Implement hybrid knowledge search tool."""
        query = args.get("query", "")
        frameworks = args.get("frameworks")
        max_results = args.get("max_results", 10)
        include_code_examples = args.get("include_code_examples", True)
        similarity_threshold = args.get("similarity_threshold", 0.7)

        result = await self.integration.hybrid_knowledge_search(
            query=query,
            frameworks=frameworks,
            max_results=max_results,
            include_code_examples=include_code_examples,
            similarity_threshold=similarity_threshold
        )

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "source": "ptolemies-mcp",
            "tool": "hybrid-knowledge-search",
            **result
        }

    async def _framework_knowledge_query(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Implement framework knowledge query tool."""
        framework = args.get("framework", "")
        topic = args.get("topic", "")
        depth = args.get("depth", 2)
        include_examples = args.get("include_examples", True)

        result = await self.integration.get_framework_knowledge(
            framework=framework,
            topic=topic,
            depth=depth,
            include_examples=include_examples
        )

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "source": "ptolemies-mcp",
            "tool": "framework-knowledge-query",
            **result
        }

    async def _learning_path_discovery(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Implement learning path discovery tool."""
        start_framework = args.get("start_framework", "")
        end_framework = args.get("end_framework", "")
        include_prerequisites = args.get("include_prerequisites", True)
        difficulty_preference = args.get("difficulty_preference", "any")

        # This would be implemented with Neo4j path-finding algorithms
        # For now, return a placeholder structure
        result = {
            "start_framework": start_framework,
            "end_framework": end_framework,
            "path_length": 0,
            "total_steps": 0,
            "estimated_duration": "To be implemented",
            "difficulty_rating": difficulty_preference,
            "learning_steps": [],
            "alternative_paths": [],
            "prerequisites": [],
            "note": "Learning path discovery implementation in progress"
        }

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "source": "ptolemies-mcp",
            "tool": "learning-path-discovery",
            **result
        }

    async def _validate_code_snippet(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Implement code validation tool."""
        code = args.get("code", "")
        framework = args.get("framework")
        confidence_threshold = args.get("confidence_threshold", 0.75)
        include_suggestions = args.get("include_suggestions", True)

        result = await self.integration.validate_code_snippet(
            code=code,
            framework=framework,
            confidence_threshold=confidence_threshold
        )

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "source": "ptolemies-mcp",
            "tool": "validate-code-snippet",
            **result
        }

    async def _analyze_framework_usage(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Implement framework usage analysis tool."""
        code = args.get("code", "")
        detect_patterns = args.get("detect_patterns", True)
        suggest_improvements = args.get("suggest_improvements", True)

        # This would integrate with enhanced dehallucinator analysis
        # For now, return a basic structure
        result = {
            "code_snippet": code,
            "frameworks_used": [],
            "usage_patterns": [],
            "best_practices": [],
            "potential_issues": [],
            "improvement_suggestions": [],
            "confidence_score": 0.0,
            "note": "Framework usage analysis implementation in progress"
        }

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "source": "ptolemies-mcp",
            "tool": "analyze-framework-usage",
            **result
        }

    async def _framework_dependencies(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Implement framework dependencies analysis tool."""
        framework = args.get("framework", "")
        include_transitive = args.get("include_transitive", False)
        max_depth = args.get("max_depth", 3)

        # This would query Neo4j for dependency relationships
        # For now, return a placeholder structure
        result = {
            "root_framework": framework,
            "total_dependencies": 0,
            "direct_dependencies": 0,
            "transitive_dependencies": 0,
            "dependency_nodes": [],
            "dependency_relationships": [],
            "circular_dependencies": [],
            "analysis_depth": max_depth,
            "note": "Framework dependencies analysis implementation in progress"
        }

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "source": "ptolemies-mcp",
            "tool": "framework-dependencies",
            **result
        }

    async def _topic_relationships(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Implement topic relationships analysis tool."""
        topic = args.get("topic", "")
        relationship_types = args.get("relationship_types")
        max_results = args.get("max_results", 20)

        # This would query Neo4j for topic relationships
        # For now, return a placeholder structure
        result = {
            "topic": topic,
            "related_topics": [],
            "frameworks_associated": [],
            "documentation_coverage": 0.0,
            "knowledge_density": 0.0,
            "note": "Topic relationships analysis implementation in progress"
        }

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "source": "ptolemies-mcp",
            "tool": "topic-relationships",
            **result
        }

    async def _knowledge_coverage_analysis(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Implement knowledge coverage analysis tool."""
        framework = args.get("framework", "")

        # This would analyze coverage across SurrealDB and Neo4j
        # For now, return a placeholder structure
        result = {
            "framework": framework,
            "coverage_metrics": {
                "framework": framework,
                "total_documentation_chunks": 0,
                "unique_topics_covered": 0,
                "average_quality_score": 0.0,
                "documentation_completeness": 0.0,
                "last_updated": None
            },
            "knowledge_gaps": [],
            "comparison_frameworks": [],
            "recommendations": [],
            "note": "Knowledge coverage analysis implementation in progress"
        }

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "source": "ptolemies-mcp",
            "tool": "knowledge-coverage-analysis",
            **result
        }

    async def _ecosystem_overview(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Implement ecosystem overview tool."""
        category = args.get("category", "all")

        # This would provide comprehensive ecosystem statistics
        # For now, return a placeholder structure
        result = {
            "stats": {
                "total_frameworks": 0,
                "frameworks_by_type": {},
                "total_relationships": 0,
                "relationships_by_type": {},
                "total_documentation_chunks": 0,
                "average_quality_score": 0.0,
                "most_connected_frameworks": [],
                "trending_topics": []
            },
            "featured_frameworks": [],
            "framework_categories": {},
            "learning_paths": [],
            "recent_updates": [],
            "health_metrics": {},
            "note": "Ecosystem overview implementation in progress"
        }

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "source": "ptolemies-mcp",
            "tool": "ecosystem-overview",
            "category": category,
            **result
        }

    async def _system_health_check(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Implement system health check tool."""
        health_status = await self.integration.get_system_health()

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "source": "ptolemies-mcp",
            "tool": "system-health-check",
            "neo4j_status": health_status.neo4j_status.dict(),
            "surrealdb_status": health_status.surrealdb_status.dict(),
            "dehallucinator_status": health_status.dehallucinator_status.dict(),
            "overall_healthy": health_status.overall_healthy,
            "last_check": health_status.last_check.isoformat()
        }

    def get_tools(self) -> List[Tool]:
        """Return list of available tools."""
        return self.tools
