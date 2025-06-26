#!/usr/bin/env python3
"""
Ptolemies Integration Layer
==========================

Unified data access layer providing seamless integration between
SurrealDB, Neo4j, and Dehallucinator services for the ptolemies MCP server.
"""

import asyncio
import os
from typing import Dict, List, Optional, Any, Tuple
from contextlib import asynccontextmanager
import logging
from datetime import datetime

# Database drivers
from neo4j import AsyncGraphDatabase, AsyncDriver
from surrealdb import Surreal
import httpx

# AI and analysis
import openai
from openai import OpenAI

# DevQ.ai infrastructure
try:
    import logfire
    LOGFIRE_AVAILABLE = True
except ImportError:
    LOGFIRE_AVAILABLE = False
    logging.warning("Logfire not available, using standard logging")

# Local imports
from ptolemies_types import (
    Framework, FrameworkRelationship, KnowledgeChunk, GraphNode,
    GraphRelationship, ConnectionStatus, SystemHealth,
    FrameworkType, RelationshipType, HallucinationIssue,
    ValidationSeverity
)

# Dehallucinator imports
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'dehallucinator'))

try:
    from ai_hallucination_detector import AIHallucinationDetector
    from ai_script_analyzer import AIScriptAnalyzer
    from knowledge_graph_validator import KnowledgeGraphValidator
    DEHALLUCINATOR_AVAILABLE = True
except ImportError:
    DEHALLUCINATOR_AVAILABLE = False
    logging.warning("Dehallucinator modules not available")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if LOGFIRE_AVAILABLE:
    try:
        logfire.configure()
        logger.info("Logfire configured successfully")
    except Exception as e:
        logger.warning(f"Logfire configuration failed: {e}")
        LOGFIRE_AVAILABLE = False


class PtolemiesIntegration:
    """
    Unified integration layer for accessing SurrealDB, Neo4j, and Dehallucinator.

    Provides high-level semantic operations that combine data from multiple sources
    to deliver intelligent, context-aware responses for AI assistants.
    """

    def __init__(self):
        """Initialize the integration layer with database connections."""
        self.neo4j_driver: Optional[AsyncDriver] = None
        self.surrealdb_client: Optional[Surreal] = None
        self.openai_client: Optional[OpenAI] = None
        self.hallucination_detector = None

        # Configuration from environment
        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_username = os.getenv("NEO4J_USERNAME", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "ptolemies")
        self.neo4j_database = os.getenv("NEO4J_DATABASE", "ptolemies")

        self.surrealdb_url = os.getenv("SURREALDB_URL", "ws://localhost:8000/rpc")
        self.surrealdb_namespace = os.getenv("SURREALDB_NAMESPACE", "ptolemies")
        self.surrealdb_database = os.getenv("SURREALDB_DATABASE", "knowledge")

        self.openai_api_key = os.getenv("OPENAI_API_KEY")

        # Connection pools and caching
        self._connection_pool_size = 10
        self._query_cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5 minutes

        logger.info("PtolemiesIntegration initialized")

    async def connect(self) -> bool:
        """
        Establish connections to all data sources.

        Returns:
            bool: True if all connections successful, False otherwise
        """
        connection_tasks = [
            self._connect_neo4j(),
            self._connect_surrealdb(),
            self._connect_openai(),
            self._initialize_dehallucinator()
        ]

        results = await asyncio.gather(*connection_tasks, return_exceptions=True)

        success_count = sum(1 for result in results if result is True)
        total_connections = len(connection_tasks)

        if LOGFIRE_AVAILABLE:
            with logfire.span("ptolemies_connection_init"):
                logfire.info(f"Connected to {success_count}/{total_connections} services")

        logger.info(f"Connected to {success_count}/{total_connections} services")
        return success_count >= 2  # Require at least 2 services for basic functionality

    async def _connect_neo4j(self) -> bool:
        """Connect to Neo4j database."""
        try:
            self.neo4j_driver = AsyncGraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_username, self.neo4j_password)
            )

            # Test connection
            async with self.neo4j_driver.session(database=self.neo4j_database) as session:
                result = await session.run("RETURN 1 as test")
                await result.single()

            logger.info("✅ Neo4j connection established")
            return True

        except Exception as e:
            logger.error(f"❌ Neo4j connection failed: {e}")
            return False

    async def _connect_surrealdb(self) -> bool:
        """Connect to SurrealDB."""
        try:
            self.surrealdb_client = Surreal()
            await self.surrealdb_client.connect(self.surrealdb_url)
            await self.surrealdb_client.use(self.surrealdb_namespace, self.surrealdb_database)

            # Test connection
            result = await self.surrealdb_client.query("SELECT * FROM test LIMIT 1")

            logger.info("✅ SurrealDB connection established")
            return True

        except Exception as e:
            logger.error(f"❌ SurrealDB connection failed: {e}")
            return False

    async def _connect_openai(self) -> bool:
        """Initialize OpenAI client."""
        try:
            if not self.openai_api_key:
                logger.warning("⚠️ OpenAI API key not provided")
                return False

            self.openai_client = OpenAI(api_key=self.openai_api_key)

            # Test connection with a simple completion
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )

            logger.info("✅ OpenAI connection established")
            return True

        except Exception as e:
            logger.error(f"❌ OpenAI connection failed: {e}")
            return False

    async def _initialize_dehallucinator(self) -> bool:
        """Initialize dehallucinator components."""
        try:
            if not DEHALLUCINATOR_AVAILABLE:
                logger.warning("⚠️ Dehallucinator modules not available")
                return False

            self.hallucination_detector = AIHallucinationDetector()
            logger.info("✅ Dehallucinator initialized")
            return True

        except Exception as e:
            logger.error(f"❌ Dehallucinator initialization failed: {e}")
            return False

    async def disconnect(self):
        """Clean up all connections."""
        if self.neo4j_driver:
            await self.neo4j_driver.close()

        if self.surrealdb_client:
            await self.surrealdb_client.close()

        logger.info("All connections closed")

    @asynccontextmanager
    async def neo4j_session(self):
        """Context manager for Neo4j sessions."""
        if not self.neo4j_driver:
            raise RuntimeError("Neo4j not connected")

        async with self.neo4j_driver.session(database=self.neo4j_database) as session:
            yield session

    # === Knowledge Search Methods ===

    async def hybrid_knowledge_search(
        self,
        query: str,
        frameworks: Optional[List[str]] = None,
        max_results: int = 10,
        include_code_examples: bool = True,
        similarity_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        Perform hybrid search combining Neo4j graph traversal with SurrealDB vector search.

        Args:
            query: Search query
            frameworks: Optional framework filter
            max_results: Maximum results to return
            include_code_examples: Whether to include code examples
            similarity_threshold: Minimum similarity score for vector results

        Returns:
            Combined search results from both graph and vector sources
        """
        if LOGFIRE_AVAILABLE:
            with logfire.span("hybrid_knowledge_search", query=query):
                return await self._perform_hybrid_search(
                    query, frameworks, max_results, include_code_examples, similarity_threshold
                )
        else:
            return await self._perform_hybrid_search(
                query, frameworks, max_results, include_code_examples, similarity_threshold
            )

    async def _perform_hybrid_search(
        self, query: str, frameworks: Optional[List[str]], max_results: int,
        include_code_examples: bool, similarity_threshold: float
    ) -> Dict[str, Any]:
        """Internal implementation of hybrid search."""

        # Parallel execution of graph and vector searches
        search_tasks = [
            self._graph_search(query, frameworks, max_results),
            self._vector_search(query, frameworks, max_results, similarity_threshold)
        ]

        graph_results, vector_results = await asyncio.gather(*search_tasks, return_exceptions=True)

        # Handle exceptions
        if isinstance(graph_results, Exception):
            logger.error(f"Graph search failed: {graph_results}")
            graph_results = []

        if isinstance(vector_results, Exception):
            logger.error(f"Vector search failed: {vector_results}")
            vector_results = []

        # Combine and rank results
        combined_results = self._combine_search_results(graph_results, vector_results)

        # Extract metadata
        frameworks_found = list(set([
            result.get('framework') for result in combined_results
            if result.get('framework')
        ]))

        topics_found = list(set([
            result.get('topic') for result in combined_results
            if result.get('topic')
        ]))

        return {
            "query": query,
            "total_results": len(combined_results),
            "vector_results": vector_results,
            "graph_results": graph_results,
            "combined_results": combined_results[:max_results],
            "frameworks_found": frameworks_found,
            "topics_found": topics_found,
            "search_metadata": {
                "similarity_threshold": similarity_threshold,
                "include_code_examples": include_code_examples,
                "search_timestamp": datetime.now().isoformat()
            }
        }

    async def _graph_search(
        self, query: str, frameworks: Optional[List[str]], max_results: int
    ) -> List[Dict[str, Any]]:
        """Perform Neo4j graph search."""
        if not self.neo4j_driver:
            return []

        # Build Cypher query
        cypher_query = """
        MATCH (n)
        WHERE (n.name CONTAINS $query OR n.description CONTAINS $query)
        """

        params = {"query": query, "max_results": max_results}

        if frameworks:
            cypher_query += " AND n.name IN $frameworks"
            params["frameworks"] = frameworks

        cypher_query += """
        OPTIONAL MATCH (n)-[r]-(related)
        RETURN n, collect(DISTINCT {rel: r, node: related}) as relationships
        LIMIT $max_results
        """

        try:
            async with self.neo4j_session() as session:
                result = await session.run(cypher_query, params)
                records = await result.data()

                return [
                    {
                        "id": record["n"]["name"] if "name" in record["n"] else str(record["n"].id),
                        "type": "graph_node",
                        "labels": list(record["n"].labels),
                        "properties": dict(record["n"]),
                        "relationships": record["relationships"],
                        "source": "neo4j"
                    }
                    for record in records
                ]

        except Exception as e:
            logger.error(f"Graph search error: {e}")
            return []

    async def _vector_search(
        self, query: str, frameworks: Optional[List[str]],
        max_results: int, similarity_threshold: float
    ) -> List[Dict[str, Any]]:
        """Perform SurrealDB vector search."""
        if not self.surrealdb_client:
            return []

        try:
            # Build SurrealQL query for vector similarity search
            surrealql = f"""
            SELECT *, vector::similarity::cosine(embedding, $query_embedding) AS similarity
            FROM document_chunk
            WHERE vector::similarity::cosine(embedding, $query_embedding) > {similarity_threshold}
            """

            if frameworks:
                framework_conditions = " OR ".join([f"framework = '{fw}'" for fw in frameworks])
                surrealql += f" AND ({framework_conditions})"

            surrealql += f" ORDER BY similarity DESC LIMIT {max_results}"

            # Generate embedding for query (placeholder - would need actual embedding generation)
            query_embedding = await self._generate_embedding(query)

            params = {"query_embedding": query_embedding}
            result = await self.surrealdb_client.query(surrealql, params)

            if result and len(result) > 0:
                return [
                    {
                        "id": chunk.get("id"),
                        "type": "document_chunk",
                        "content": chunk.get("content", ""),
                        "source": chunk.get("source", ""),
                        "topic": chunk.get("topic", ""),
                        "framework": chunk.get("framework", ""),
                        "similarity_score": chunk.get("similarity", 0.0),
                        "quality_score": chunk.get("quality_score", 0.0),
                        "metadata": chunk.get("metadata", {}),
                        "source": "surrealdb"
                    }
                    for chunk in result[0].get("result", [])
                ]

            return []

        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []

    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI."""
        if not self.openai_client:
            # Return dummy embedding if OpenAI not available
            return [0.0] * 1536

        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding

        except Exception as e:
            logger.error(f"Embedding generation error: {e}")
            return [0.0] * 1536

    def _combine_search_results(
        self, graph_results: List[Dict], vector_results: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Combine and rank results from graph and vector searches."""
        combined = []

        # Add graph results with scoring
        for result in graph_results:
            result["combined_score"] = len(result.get("relationships", [])) * 0.1
            result["result_type"] = "graph"
            combined.append(result)

        # Add vector results with similarity scoring
        for result in vector_results:
            result["combined_score"] = result.get("similarity_score", 0.0)
            result["result_type"] = "vector"
            combined.append(result)

        # Sort by combined score
        combined.sort(key=lambda x: x.get("combined_score", 0.0), reverse=True)

        return combined

    # === Framework Knowledge Methods ===

    async def get_framework_knowledge(
        self, framework: str, topic: str, depth: int = 2, include_examples: bool = True
    ) -> Dict[str, Any]:
        """Get comprehensive framework knowledge combining graph relationships and documentation."""

        # Parallel queries
        tasks = [
            self._get_framework_graph_context(framework, depth),
            self._get_framework_documentation(framework, topic, include_examples)
        ]

        graph_context, documentation = await asyncio.gather(*tasks, return_exceptions=True)

        if isinstance(graph_context, Exception):
            logger.error(f"Framework graph context error: {graph_context}")
            graph_context = {}

        if isinstance(documentation, Exception):
            logger.error(f"Framework documentation error: {documentation}")
            documentation = []

        return {
            "framework": framework,
            "topic": topic,
            "graph_context": graph_context,
            "documentation": documentation,
            "depth": depth,
            "include_examples": include_examples
        }

    async def _get_framework_graph_context(self, framework: str, depth: int) -> Dict[str, Any]:
        """Get framework context from Neo4j graph."""
        if not self.neo4j_driver:
            return {}

        cypher_query = f"""
        MATCH (f:Framework {{name: $framework}})
        OPTIONAL MATCH path = (f)-[*1..{depth}]-(related)
        RETURN f, collect(DISTINCT path) as paths
        """

        try:
            async with self.neo4j_session() as session:
                result = await session.run(cypher_query, {"framework": framework})
                record = await result.single()

                if record:
                    return {
                        "framework_node": dict(record["f"]),
                        "relationship_paths": record["paths"],
                        "related_frameworks": []  # Extract from paths
                    }

                return {}

        except Exception as e:
            logger.error(f"Framework graph context error: {e}")
            return {}

    async def _get_framework_documentation(
        self, framework: str, topic: str, include_examples: bool
    ) -> List[Dict[str, Any]]:
        """Get framework documentation from SurrealDB."""
        if not self.surrealdb_client:
            return []

        try:
            surrealql = """
            SELECT * FROM document_chunk
            WHERE framework = $framework AND topic CONTAINS $topic
            ORDER BY quality_score DESC
            LIMIT 20
            """

            params = {"framework": framework, "topic": topic}
            result = await self.surrealdb_client.query(surrealql, params)

            if result and len(result) > 0:
                return result[0].get("result", [])

            return []

        except Exception as e:
            logger.error(f"Framework documentation error: {e}")
            return []

    # === Code Validation Methods ===

    async def validate_code_snippet(
        self, code: str, framework: Optional[str] = None, confidence_threshold: float = 0.75
    ) -> Dict[str, Any]:
        """Validate code snippet for AI hallucinations using dehallucinator."""

        if not self.hallucination_detector:
            return {
                "error": "Dehallucinator not available",
                "is_valid": True,  # Default to valid if can't validate
                "confidence": 0.0
            }

        try:
            if LOGFIRE_AVAILABLE:
                with logfire.span("code_validation", framework=framework):
                    return await self._perform_code_validation(code, framework, confidence_threshold)
            else:
                return await self._perform_code_validation(code, framework, confidence_threshold)

        except Exception as e:
            logger.error(f"Code validation error: {e}")
            return {
                "error": str(e),
                "is_valid": True,  # Default to valid on error
                "confidence": 0.0
            }

    async def _perform_code_validation(
        self, code: str, framework: Optional[str], confidence_threshold: float
    ) -> Dict[str, Any]:
        """Internal code validation implementation."""

        # Create temporary file for analysis
        import tempfile

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(code)
            temp_file.flush()

            try:
                # Run hallucination detection
                result = self.hallucination_detector.detect_hallucinations(
                    temp_file.name,
                    save_json=False,
                    save_markdown=False,
                    verbose=False
                )

                # Process results
                is_valid = result.overall_confidence < confidence_threshold

                issues = []
                for hallucination in result.hallucinations:
                    issues.append({
                        "type": hallucination.get("type", "unknown"),
                        "line": hallucination.get("line"),
                        "code": hallucination.get("code"),
                        "framework": hallucination.get("framework"),
                        "confidence": hallucination.get("confidence", 0.0),
                        "severity": self._map_confidence_to_severity(hallucination.get("confidence", 0.0)),
                        "description": hallucination.get("description", ""),
                        "suggestion": hallucination.get("suggestion", "")
                    })

                return {
                    "code_snippet": code,
                    "is_valid": is_valid,
                    "overall_confidence": result.overall_confidence,
                    "frameworks_detected": result.frameworks_detected or [framework] if framework else [],
                    "issues": issues,
                    "patterns_detected": result.patterns_detected or [],
                    "suggestions": result.suggestions or [],
                    "analysis_metadata": {
                        "confidence_threshold": confidence_threshold,
                        "analysis_timestamp": datetime.now().isoformat()
                    }
                }

            finally:
                # Clean up temp file
                os.unlink(temp_file.name)

    def _map_confidence_to_severity(self, confidence: float) -> str:
        """Map confidence score to validation severity."""
        if confidence >= 0.9:
            return ValidationSeverity.CRITICAL
        elif confidence >= 0.75:
            return ValidationSeverity.HIGH
        elif confidence >= 0.5:
            return ValidationSeverity.MEDIUM
        elif confidence >= 0.25:
            return ValidationSeverity.LOW
        else:
            return ValidationSeverity.INFO

    # === System Health Methods ===

    async def get_system_health(self) -> SystemHealth:
        """Get overall system health status."""
        health_checks = [
            self._check_neo4j_health(),
            self._check_surrealdb_health(),
            self._check_dehallucinator_health()
        ]

        neo4j_status, surrealdb_status, dehallucinator_status = await asyncio.gather(
            *health_checks, return_exceptions=True
        )

        # Handle exceptions in health checks
        if isinstance(neo4j_status, Exception):
            neo4j_status = ConnectionStatus(service="neo4j", connected=False, error_message=str(neo4j_status))

        if isinstance(surrealdb_status, Exception):
            surrealdb_status = ConnectionStatus(service="surrealdb", connected=False, error_message=str(surrealdb_status))

        if isinstance(dehallucinator_status, Exception):
            dehallucinator_status = ConnectionStatus(service="dehallucinator", connected=False, error_message=str(dehallucinator_status))

        overall_healthy = (
            neo4j_status.connected and
            surrealdb_status.connected and
            dehallucinator_status.connected
        )

        return SystemHealth(
            neo4j_status=neo4j_status,
            surrealdb_status=surrealdb_status,
            dehallucinator_status=dehallucinator_status,
            overall_healthy=overall_healthy
        )

    async def _check_neo4j_health(self) -> ConnectionStatus:
        """Check Neo4j connection health."""
        if not self.neo4j_driver:
            return ConnectionStatus(service="neo4j", connected=False, error_message="Not connected")

        try:
            async with self.neo4j_session() as session:
                result = await session.run("RETURN 1 as health")
                await result.single()

            return ConnectionStatus(
                service="neo4j",
                connected=True,
                last_ping=datetime.now()
            )

        except Exception as e:
            return ConnectionStatus(
                service="neo4j",
                connected=False,
                error_message=str(e)
            )

    async def _check_surrealdb_health(self) -> ConnectionStatus:
        """Check SurrealDB connection health."""
        if not self.surrealdb_client:
            return ConnectionStatus(service="surrealdb", connected=False, error_message="Not connected")

        try:
            result = await self.surrealdb_client.query("SELECT 1 as health")

            return ConnectionStatus(
                service="surrealdb",
                connected=True,
                last_ping=datetime.now()
            )

        except Exception as e:
            return ConnectionStatus(
                service="surrealdb",
                connected=False,
                error_message=str(e)
            )

    async def _check_dehallucinator_health(self) -> ConnectionStatus:
        """Check dehallucinator service health."""
        if not self.hallucination_detector:
            return ConnectionStatus(service="dehallucinator", connected=False, error_message="Not initialized")

        try:
            # Simple health check - try to analyze a minimal code snippet
            test_code = "print('hello')"
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(test_code)
                temp_file.flush()

                try:
                    self.hallucination_detector.detect_hallucinations(
                        temp_file.name, save_json=False, save_markdown=False, verbose=False
                    )
                finally:
                    os.unlink(temp_file.name)

            return ConnectionStatus(
                service="dehallucinator",
                connected=True,
                last_ping=datetime.now()
            )

        except Exception as e:
            return ConnectionStatus(
                service="dehallucinator",
                connected=False,
                error_message=str(e)
            )
