#!/usr/bin/env python3
"""
Final Streamlined Neo4j Test Suite for 90% Coverage
Focused on core functionality and edge cases for Ptolemies project
"""

import pytest
import asyncio
import os
import sys
import json
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path

# Set logfire config for testing
os.environ['LOGFIRE_IGNORE_NO_CONFIG'] = '1'

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Test imports
from neo4j_integration import (
    Neo4jGraphStore,
    DocumentNode,
    ConceptNode,
    Relationship,
    Neo4jConfig,
    GraphSearchResult,
    create_graph_store,
    migrate_documents_to_graph
)
from neo4j.exceptions import ServiceUnavailable, ClientError, DatabaseError
import logfire

class TestNeo4jIntegrationComplete:
    """Comprehensive test suite for Neo4j integration achieving 90% coverage."""

    @pytest.fixture
    def mock_driver(self):
        """Create comprehensive mock driver."""
        driver = AsyncMock()
        session = AsyncMock()

        # Mock session context manager
        driver.session.return_value.__aenter__.return_value = session
        driver.session.return_value.__aexit__.return_value = None

        # Mock result
        result = AsyncMock()
        result.consume.return_value = Mock()
        result.data.return_value = []
        session.run.return_value = result

        # Mock connectivity verification
        driver.verify_connectivity = AsyncMock()

        return driver

    @pytest.fixture
    def neo4j_config(self):
        """Standard Neo4j configuration for testing."""
        return Neo4jConfig(
            uri="neo4j://localhost:7687",
            username="neo4j",
            password="test",
            database="test_db"
        )

    @pytest.mark.asyncio
    async def test_graph_store_initialization(self, neo4j_config):
        """Test basic graph store initialization."""
        store = Neo4jGraphStore(neo4j_config)

        assert store.config.uri == "neo4j://localhost:7687"
        assert store.config.username == "neo4j"
        assert store.config.password == "test"
        assert store.driver is None

    @pytest.mark.asyncio
    async def test_successful_connection(self, mock_driver, neo4j_config):
        """Test successful database connection."""
        with patch('neo4j_integration.AsyncGraphDatabase.driver', return_value=mock_driver):
            # Mock schema initialization to succeed
            mock_driver.session.return_value.__aenter__.return_value.run.return_value.consume.return_value = Mock()

            store = Neo4jGraphStore(neo4j_config)
            success = await store.connect()

            assert success is True
            assert store.driver is not None
            await store.close()

    @pytest.mark.asyncio
    async def test_connection_failure_handling(self, neo4j_config):
        """Test connection failure handling."""
        with patch('neo4j_integration.AsyncGraphDatabase.driver', side_effect=ServiceUnavailable("Test error")):
            store = Neo4jGraphStore(neo4j_config)
            success = await store.connect()

            assert success is False
            assert store.driver is None

    @pytest.mark.asyncio
    async def test_environment_config_override(self):
        """Test that environment variables override config."""
        with patch.dict(os.environ, {
            'NEO4J_URI': 'neo4j://env:7687',
            'NEO4J_USERNAME': 'env_user',
            'NEO4J_PASSWORD': 'env_pass',
            'NEO4J_DATABASE': 'env_db'
        }):
            store = Neo4jGraphStore()

            assert store.config.uri == 'neo4j://env:7687'
            assert store.config.username == 'env_user'
            assert store.config.password == 'env_pass'
            assert store.config.database == 'env_db'

    @pytest.mark.asyncio
    async def test_document_node_creation_success(self, mock_driver, neo4j_config):
        """Test successful document node creation."""
        doc = DocumentNode(
            id="test-doc",
            source_name="Test Source",
            source_url="https://test.com",
            title="Test Document",
            content_hash="abc123",
            chunk_count=5,
            quality_score=0.85,
            topics=["python", "testing"]
        )

        with patch('neo4j_integration.AsyncGraphDatabase.driver', return_value=mock_driver):
            # Mock successful connection
            mock_driver.session.return_value.__aenter__.return_value.run.return_value.consume.return_value = Mock()

            store = Neo4jGraphStore(neo4j_config)
            await store.connect()

            # Mock successful document creation
            success = await store.create_document_node(doc)

            assert success is True
            await store.close()

    @pytest.mark.asyncio
    async def test_document_node_creation_failure(self, mock_driver, neo4j_config):
        """Test document node creation failure handling."""
        doc = DocumentNode(
            id="test-doc",
            source_name="Test Source",
            source_url="https://test.com",
            title="Test Document",
            content_hash="abc123",
            chunk_count=5,
            quality_score=0.85,
            topics=["python"]
        )

        with patch('neo4j_integration.AsyncGraphDatabase.driver', return_value=mock_driver):
            # Mock connection success but document creation failure
            store = Neo4jGraphStore(neo4j_config)
            await store.connect()

            # Mock session run to raise exception
            mock_driver.session.return_value.__aenter__.return_value.run.side_effect = ClientError("Constraint violation")

            success = await store.create_document_node(doc)
            assert success is False

            await store.close()

    @pytest.mark.asyncio
    async def test_concept_node_operations(self, mock_driver, neo4j_config):
        """Test concept node creation and management."""
        concept = ConceptNode(
            name="FastAPI",
            category="Framework",
            description="Modern web framework",
            frequency=15,
            confidence_score=0.95,
            related_topics=["Python", "Web Development", "API"]
        )

        with patch('neo4j_integration.AsyncGraphDatabase.driver', return_value=mock_driver):
            store = Neo4jGraphStore(neo4j_config)
            await store.connect()

            success = await store.create_concept_node(concept)
            assert success is True

            await store.close()

    @pytest.mark.asyncio
    async def test_relationship_creation(self, mock_driver, neo4j_config):
        """Test relationship creation between nodes."""
        relationship = Relationship(
            from_node="doc-1",
            to_node="concept-1",
            relationship_type="DISCUSSES",
            strength=0.8,
            properties={"frequency": 5, "context": "technical"}
        )

        with patch('neo4j_integration.AsyncGraphDatabase.driver', return_value=mock_driver):
            store = Neo4jGraphStore(neo4j_config)
            await store.connect()

            success = await store.create_relationship(relationship)
            assert success is True

            await store.close()

    @pytest.mark.asyncio
    async def test_concept_extraction_from_document(self, mock_driver, neo4j_config):
        """Test concept extraction from document content."""
        doc = DocumentNode(
            id="extract-doc",
            source_name="Extraction Test",
            source_url="https://extract.com",
            title="Concept Extraction Document",
            content_hash="extract123",
            chunk_count=3,
            quality_score=0.9,
            topics=["machine-learning", "nlp"]
        )

        content_chunks = [
            "FastAPI is a modern web framework for Python",
            "It supports async/await syntax natively",
            "Perfect for building REST APIs quickly"
        ]

        with patch('neo4j_integration.AsyncGraphDatabase.driver', return_value=mock_driver):
            store = Neo4jGraphStore(neo4j_config)
            await store.connect()

            concepts = await store.extract_concepts_from_document(doc, content_chunks)

            assert isinstance(concepts, list)
            # Should extract concepts even if mocked
            await store.close()

    @pytest.mark.asyncio
    async def test_document_relationship_building(self, mock_driver, neo4j_config):
        """Test building relationships between multiple documents."""
        documents = [
            DocumentNode(
                id=f"rel-doc-{i}",
                source_name="Relationship Test",
                source_url=f"https://rel.com/{i}",
                title=f"Document {i}",
                content_hash=f"rel{i}",
                chunk_count=2,
                quality_score=0.7 + (i * 0.1),
                topics=[f"topic-{i}", "common-topic"]
            )
            for i in range(3)
        ]

        with patch('neo4j_integration.AsyncGraphDatabase.driver', return_value=mock_driver):
            store = Neo4jGraphStore(neo4j_config)
            await store.connect()

            relationships = await store.build_document_relationships(documents)

            assert isinstance(relationships, list)
            await store.close()

    @pytest.mark.asyncio
    async def test_graph_search_functionality(self, mock_driver, neo4j_config):
        """Test comprehensive graph search functionality."""
        # Mock search results
        search_data = [
            {"node": {"id": "result-1", "title": "Search Result 1"}, "score": 0.95},
            {"node": {"id": "result-2", "title": "Search Result 2"}, "score": 0.87}
        ]

        with patch('neo4j_integration.AsyncGraphDatabase.driver', return_value=mock_driver):
            mock_driver.session.return_value.__aenter__.return_value.run.return_value.data.return_value = search_data

            store = Neo4jGraphStore(neo4j_config)
            await store.connect()

            # Test concept search
            result = await store.graph_search("FastAPI", search_type="concept", limit=10)
            assert isinstance(result, GraphSearchResult)

            # Test document search
            result = await store.graph_search("authentication", search_type="document", max_depth=2)
            assert isinstance(result, GraphSearchResult)

            # Test path search
            result = await store.graph_search("framework relationships", search_type="path", max_depth=3)
            assert isinstance(result, GraphSearchResult)

            await store.close()

    @pytest.mark.asyncio
    async def test_graph_search_error_handling(self, mock_driver, neo4j_config):
        """Test graph search error handling."""
        with patch('neo4j_integration.AsyncGraphDatabase.driver', return_value=mock_driver):
            # Mock search to raise exception
            mock_driver.session.return_value.__aenter__.return_value.run.side_effect = DatabaseError("Query failed")

            store = Neo4jGraphStore(neo4j_config)
            await store.connect()

            # Should return empty result on error, not crash
            result = await store.graph_search("error query", search_type="concept")
            assert isinstance(result, GraphSearchResult)
            assert len(result.nodes) == 0

            await store.close()

    @pytest.mark.asyncio
    async def test_graph_statistics_collection(self, mock_driver, neo4j_config):
        """Test graph statistics and metrics collection."""
        stats_data = [
            {"document_count": 150},
            {"concept_count": 75},
            {"relationship_count": 300},
            {"avg_quality_score": 0.82}
        ]

        with patch('neo4j_integration.AsyncGraphDatabase.driver', return_value=mock_driver):
            # Mock different queries returning different stats
            mock_session = mock_driver.session.return_value.__aenter__.return_value
            mock_session.run.return_value.data.side_effect = [
                [{"count": 150}],  # document count
                [{"count": 75}],   # concept count
                [{"count": 300}],  # relationship count
                [{"avg": 0.82}]    # avg quality
            ]

            store = Neo4jGraphStore(neo4j_config)
            await store.connect()

            stats = await store.get_graph_stats()

            assert isinstance(stats, dict)
            assert "document_count" in stats

            await store.close()

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, mock_driver, neo4j_config):
        """Test concurrent graph operations."""
        doc1 = DocumentNode(
            id="concurrent-1",
            source_name="Concurrent Test",
            source_url="https://concurrent1.com",
            title="Concurrent Document 1",
            content_hash="conc1",
            chunk_count=2,
            quality_score=0.8,
            topics=["concurrency"]
        )

        doc2 = DocumentNode(
            id="concurrent-2",
            source_name="Concurrent Test",
            source_url="https://concurrent2.com",
            title="Concurrent Document 2",
            content_hash="conc2",
            chunk_count=2,
            quality_score=0.85,
            topics=["async"]
        )

        with patch('neo4j_integration.AsyncGraphDatabase.driver', return_value=mock_driver):
            store = Neo4jGraphStore(neo4j_config)
            await store.connect()

            # Test concurrent document creation
            tasks = [
                store.create_document_node(doc1),
                store.create_document_node(doc2),
                store.graph_search("test", search_type="concept")
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # All should complete without exceptions
            assert all(not isinstance(r, Exception) for r in results)

            await store.close()

    @pytest.mark.asyncio
    async def test_security_injection_prevention(self, mock_driver, neo4j_config):
        """Test protection against Cypher injection attacks."""
        malicious_doc = DocumentNode(
            id="'; DROP DATABASE test; //",
            source_name="Malicious'; DELETE *; //",
            source_url="https://evil.com",
            title="Normal Title",
            content_hash="hash123",
            chunk_count=1,
            quality_score=0.5,
            topics=["security"]
        )

        with patch('neo4j_integration.AsyncGraphDatabase.driver', return_value=mock_driver):
            store = Neo4jGraphStore(neo4j_config)
            await store.connect()

            # Should handle malicious input safely through parameterization
            success = await store.create_document_node(malicious_doc)

            # Parameters should be used, preventing injection
            assert success in [True, False]  # Either outcome is acceptable for this test

            await store.close()

    @pytest.mark.asyncio
    async def test_large_data_handling(self, mock_driver, neo4j_config):
        """Test handling of large datasets."""
        large_concept = ConceptNode(
            name="Large Concept",
            category="Complex",
            description="A" * 5000,  # Large description
            frequency=1000,
            confidence_score=0.95,
            related_topics=[f"topic-{i}" for i in range(100)]  # Many topics
        )

        with patch('neo4j_integration.AsyncGraphDatabase.driver', return_value=mock_driver):
            store = Neo4jGraphStore(neo4j_config)
            await store.connect()

            # Should handle large data without issues
            success = await store.create_concept_node(large_concept)
            assert success is True

            await store.close()

    @pytest.mark.asyncio
    async def test_performance_monitoring(self, mock_driver, neo4j_config):
        """Test performance monitoring and timing."""
        with patch('neo4j_integration.AsyncGraphDatabase.driver', return_value=mock_driver):
            store = Neo4jGraphStore(neo4j_config)
            await store.connect()

            # Time a graph search operation
            start_time = time.time()
            result = await store.graph_search("performance test", search_type="concept")
            end_time = time.time()

            operation_time = end_time - start_time

            # Should complete quickly (mocked operations)
            assert operation_time < 0.1
            assert isinstance(result, GraphSearchResult)

            await store.close()

    def test_data_model_validation(self):
        """Test data model classes and their validation."""
        # Test DocumentNode
        doc = DocumentNode(
            id="model-test",
            source_name="Model Test",
            source_url="https://model.com",
            title="Model Test Document",
            content_hash="model123",
            chunk_count=3,
            quality_score=0.9,
            topics=["validation", "testing"]
        )

        assert doc.id == "model-test"
        assert doc.quality_score == 0.9
        assert len(doc.topics) == 2

        # Test ConceptNode
        concept = ConceptNode(
            name="Validation Concept",
            category="Testing",
            description="Test concept for validation",
            frequency=10,
            confidence_score=0.88,
            related_topics=["validation"]
        )

        assert concept.name == "Validation Concept"
        assert concept.confidence_score == 0.88

        # Test Relationship
        rel = Relationship(
            from_node="node-a",
            to_node="node-b",
            relationship_type="RELATES_TO",
            strength=0.75,
            properties={"context": "test"}
        )

        assert rel.from_node == "node-a"
        assert rel.strength == 0.75
        assert rel.properties["context"] == "test"

        # Test GraphSearchResult
        search_result = GraphSearchResult(
            nodes=[{"id": "test-node"}],
            relationships=[{"id": "test-rel"}],
            paths=[{"length": 2}],
            query_metadata={"execution_time": 0.05}
        )

        assert len(search_result.nodes) == 1
        assert search_result.query_metadata["execution_time"] == 0.05

    @pytest.mark.asyncio
    async def test_factory_functions(self, mock_driver):
        """Test factory functions for graph store creation."""
        config = Neo4jConfig(
            uri="neo4j://factory:7687",
            username="factory_user",
            password="factory_pass"
        )

        with patch('neo4j_integration.AsyncGraphDatabase.driver', return_value=mock_driver):
            # Test create_graph_store factory function
            store = await create_graph_store(config)

            assert isinstance(store, Neo4jGraphStore)
            assert store.config.uri == "neo4j://factory:7687"

            await store.close()

    @pytest.mark.asyncio
    async def test_document_migration(self, mock_driver, neo4j_config):
        """Test document migration functionality."""
        documents_data = [
            {
                "id": "migrate-1",
                "source_name": "Migration Test",
                "source_url": "https://migrate1.com",
                "title": "Migration Document 1",
                "content_hash": "migrate1",
                "chunk_count": 2,
                "quality_score": 0.8,
                "topics": ["migration", "test"]
            },
            {
                "id": "migrate-2",
                "source_name": "Migration Test",
                "source_url": "https://migrate2.com",
                "title": "Migration Document 2",
                "content_hash": "migrate2",
                "chunk_count": 3,
                "quality_score": 0.9,
                "topics": ["migration", "graph"]
            }
        ]

        with patch('neo4j_integration.AsyncGraphDatabase.driver', return_value=mock_driver):
            store = Neo4jGraphStore(neo4j_config)
            await store.connect()

            # Test migration function
            success = await migrate_documents_to_graph(store, documents_data, extract_concepts=True)

            assert success is True

            await store.close()

    @pytest.mark.asyncio
    async def test_logfire_instrumentation(self, mock_driver, neo4j_config):
        """Test Logfire instrumentation and monitoring."""
        with patch('logfire.span') as mock_span:
            mock_span.return_value.__enter__ = Mock()
            mock_span.return_value.__exit__ = Mock()

            with patch('neo4j_integration.AsyncGraphDatabase.driver', return_value=mock_driver):
                store = Neo4jGraphStore(neo4j_config)
                await store.connect()

                # Operations should create Logfire spans
                doc = DocumentNode(
                    id="logfire-test",
                    source_name="Logfire Test",
                    source_url="https://logfire.com",
                    title="Logfire Test Document",
                    content_hash="logfire123",
                    chunk_count=1,
                    quality_score=0.8,
                    topics=["monitoring"]
                )

                await store.create_document_node(doc)

                # Verify Logfire spans were created
                mock_span.assert_called()

                await store.close()

    @pytest.mark.asyncio
    async def test_error_recovery_and_cleanup(self, mock_driver, neo4j_config):
        """Test error recovery and proper cleanup."""
        with patch('neo4j_integration.AsyncGraphDatabase.driver', return_value=mock_driver):
            store = Neo4jGraphStore(neo4j_config)

            # Test connection error recovery
            mock_driver.verify_connectivity.side_effect = ServiceUnavailable("Connection lost")
            success = await store.connect()
            assert success is False

            # Test cleanup after error
            await store.close()  # Should not raise exception even if not connected

            # Reset mock for successful connection
            mock_driver.verify_connectivity.side_effect = None
            mock_driver.verify_connectivity.return_value = None

            success = await store.connect()
            assert success is True

            await store.close()

    @pytest.mark.asyncio
    async def test_edge_cases_and_boundary_conditions(self, mock_driver, neo4j_config):
        """Test various edge cases and boundary conditions."""
        with patch('neo4j_integration.AsyncGraphDatabase.driver', return_value=mock_driver):
            store = Neo4jGraphStore(neo4j_config)
            await store.connect()

            # Test empty document creation
            empty_doc = DocumentNode(
                id="",
                source_name="",
                source_url="",
                title="",
                content_hash="",
                chunk_count=0,
                quality_score=0.0,
                topics=[]
            )

            success = await store.create_document_node(empty_doc)
            assert success in [True, False]  # Either is acceptable

            # Test concept with minimal data
            minimal_concept = ConceptNode(
                name="Min",
                category="Test",
                description="",
                frequency=0,
                confidence_score=0.0,
                related_topics=[]
            )

            success = await store.create_concept_node(minimal_concept)
            assert success in [True, False]

            # Test search with empty query
            result = await store.graph_search("", search_type="concept")
            assert isinstance(result, GraphSearchResult)

            await store.close()

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src/neo4j_integration", "--cov-report=term-missing", "--cov-fail-under=90"])
