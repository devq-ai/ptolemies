#!/usr/bin/env python3
"""
Test suite for Neo4j Graph Integration
"""

import pytest
import asyncio
import os
import sys
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
from typing import List

# Set logfire config for testing
os.environ['LOGFIRE_IGNORE_NO_CONFIG'] = '1'

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from neo4j_integration import (
    Neo4jGraphStore,
    Neo4jConfig,
    DocumentNode,
    ConceptNode,
    Relationship,
    GraphSearchResult,
    create_graph_store,
    migrate_documents_to_graph
)

class TestNeo4jConfig:
    """Test Neo4j configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = Neo4jConfig()
        
        assert config.uri == "bolt://localhost:7687"
        assert config.username == "neo4j"
        assert config.password == "password"
        assert config.database == "ptolemies"
        assert config.max_connection_lifetime == 3600
        assert config.max_connection_pool_size == 50
        assert config.connection_acquisition_timeout == 60
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = Neo4jConfig(
            uri="bolt://custom:7687",
            username="custom_user",
            password="custom_pass",
            database="custom_db",
            max_connection_lifetime=1800
        )
        
        assert config.uri == "bolt://custom:7687"
        assert config.username == "custom_user"
        assert config.password == "custom_pass"
        assert config.database == "custom_db"
        assert config.max_connection_lifetime == 1800

class TestDocumentNode:
    """Test DocumentNode dataclass."""
    
    def test_document_node_creation(self):
        """Test document node creation with required fields."""
        doc = DocumentNode(
            id="doc_1",
            source_name="FastAPI",
            source_url="https://fastapi.tiangolo.com",
            title="Getting Started",
            content_hash="abc123",
            chunk_count=5,
            quality_score=0.95,
            topics=["web", "python", "api"]
        )
        
        assert doc.id == "doc_1"
        assert doc.source_name == "FastAPI"
        assert doc.quality_score == 0.95
        assert doc.topics == ["web", "python", "api"]
        assert doc.created_at is None  # Optional field
        assert doc.updated_at is None  # Optional field

class TestConceptNode:
    """Test ConceptNode dataclass."""
    
    def test_concept_node_creation(self):
        """Test concept node creation."""
        concept = ConceptNode(
            name="Authentication",
            category="Security",
            description="User verification system",
            frequency=15,
            confidence_score=0.85,
            related_topics=["security", "auth", "user"]
        )
        
        assert concept.name == "Authentication"
        assert concept.category == "Security"
        assert concept.frequency == 15
        assert concept.confidence_score == 0.85
        assert concept.related_topics == ["security", "auth", "user"]

class TestRelationship:
    """Test Relationship dataclass."""
    
    def test_relationship_creation(self):
        """Test relationship creation."""
        rel = Relationship(
            from_node="doc_1",
            to_node="Authentication",
            relationship_type="CONTAINS_CONCEPT",
            strength=0.9,
            properties={"frequency": 10, "category": "Security"}
        )
        
        assert rel.from_node == "doc_1"
        assert rel.to_node == "Authentication"
        assert rel.relationship_type == "CONTAINS_CONCEPT"
        assert rel.strength == 0.9
        assert rel.properties["frequency"] == 10

class TestGraphSearchResult:
    """Test GraphSearchResult dataclass."""
    
    def test_graph_search_result_creation(self):
        """Test graph search result creation."""
        result = GraphSearchResult(
            nodes=[{"id": "doc_1", "title": "Test"}],
            relationships=[{"type": "RELATED_TO", "strength": 0.8}],
            paths=[{"length": 2, "nodes": []}],
            query_metadata={"search_time_ms": 150.5}
        )
        
        assert len(result.nodes) == 1
        assert len(result.relationships) == 1
        assert len(result.paths) == 1
        assert result.query_metadata["search_time_ms"] == 150.5

class TestNeo4jGraphStore:
    """Test Neo4j graph store implementation."""
    
    @pytest.fixture
    def config(self):
        """Test configuration."""
        return Neo4jConfig(database="test_ptolemies")
    
    @pytest.fixture
    def mock_driver(self):
        """Mock Neo4j driver."""
        mock_driver = AsyncMock()
        mock_driver.verify_connectivity = AsyncMock()
        mock_driver.close = AsyncMock()
        return mock_driver
    
    @pytest.fixture
    def mock_session(self):
        """Mock Neo4j session."""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.run = AsyncMock()
        return mock_session
    
    def test_graph_store_initialization(self, config):
        """Test graph store initialization."""
        store = Neo4jGraphStore(config)
        
        assert store.config == config
        assert store.driver is None
    
    @patch.dict(os.environ, {
        "NEO4J_URI": "bolt://test:7687",
        "NEO4J_USERNAME": "testuser",
        "NEO4J_PASSWORD": "testpass",
        "NEO4J_DATABASE": "testdb"
    })
    def test_config_from_environment(self):
        """Test configuration from environment variables."""
        store = Neo4jGraphStore()
        
        assert store.config.uri == "bolt://test:7687"
        assert store.config.username == "testuser"
        assert store.config.password == "testpass"
        assert store.config.database == "testdb"
    
    @pytest.mark.asyncio
    @patch('neo4j_integration.AsyncGraphDatabase.driver')
    async def test_connect_success(self, mock_driver_class, config, mock_driver, mock_session):
        """Test successful Neo4j connection."""
        mock_driver_class.return_value = mock_driver
        mock_driver.session.return_value = mock_session
        
        # Mock the session context manager properly
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        store = Neo4jGraphStore(config)
        result = await store.connect()
        
        assert result is True
        assert store.driver == mock_driver
        mock_driver.verify_connectivity.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('neo4j_integration.AsyncGraphDatabase.driver')
    async def test_connect_failure(self, mock_driver_class, config):
        """Test Neo4j connection failure."""
        mock_driver = AsyncMock()
        mock_driver.verify_connectivity.side_effect = Exception("Connection failed")
        mock_driver_class.return_value = mock_driver
        
        store = Neo4jGraphStore(config)
        result = await store.connect()
        
        assert result is False
        assert store.driver is None
    
    @pytest.mark.asyncio
    async def test_create_document_node(self, config, mock_driver, mock_session):
        """Test creating document node."""
        store = Neo4jGraphStore(config)
        store.driver = mock_driver
        mock_driver.session.return_value = mock_session
        
        # Mock the session context manager properly
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        mock_result = AsyncMock()
        mock_record = {"document_id": "doc_1"}
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result
        
        doc = DocumentNode(
            id="doc_1",
            source_name="Test",
            source_url="https://test.com",
            title="Test Document",
            content_hash="hash123",
            chunk_count=3,
            quality_score=0.8,
            topics=["test"]
        )
        
        result = await store.create_document_node(doc)
        
        assert result is True
        mock_session.run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_document_node_no_driver(self, config):
        """Test creating document node without driver connection."""
        store = Neo4jGraphStore(config)
        
        doc = DocumentNode(
            id="doc_1",
            source_name="Test",
            source_url="https://test.com",
            title="Test Document",
            content_hash="hash123",
            chunk_count=3,
            quality_score=0.8,
            topics=["test"]
        )
        
        with pytest.raises(RuntimeError, match="Not connected to Neo4j"):
            await store.create_document_node(doc)
    
    @pytest.mark.asyncio
    async def test_create_concept_node(self, config, mock_driver, mock_session):
        """Test creating concept node."""
        store = Neo4jGraphStore(config)
        store.driver = mock_driver
        mock_driver.session.return_value = mock_session
        
        # Mock the session context manager properly
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        mock_result = AsyncMock()
        mock_record = {"concept_name": "Authentication"}
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result
        
        concept = ConceptNode(
            name="Authentication",
            category="Security",
            description="User verification",
            frequency=10,
            confidence_score=0.9,
            related_topics=["security", "auth"]
        )
        
        result = await store.create_concept_node(concept)
        
        assert result is True
        mock_session.run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_relationship(self, config, mock_driver, mock_session):
        """Test creating relationship."""
        store = Neo4jGraphStore(config)
        store.driver = mock_driver
        mock_driver.session.return_value = mock_session
        
        # Mock the session context manager properly
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        mock_result = AsyncMock()
        mock_record = {"relationship_type": "CONTAINS_CONCEPT"}
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result
        
        rel = Relationship(
            from_node="doc_1",
            to_node="Authentication",
            relationship_type="CONTAINS_CONCEPT",
            strength=0.8,
            properties={"frequency": 5}
        )
        
        result = await store.create_relationship(rel)
        
        assert result is True
        mock_session.run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_extract_concepts_from_document(self, config):
        """Test concept extraction from document."""
        store = Neo4jGraphStore(config)
        
        doc = DocumentNode(
            id="doc_1",
            source_name="FastAPI",
            source_url="https://fastapi.tiangolo.com",
            title="FastAPI Authentication",
            content_hash="hash123",
            chunk_count=2,
            quality_score=0.9,
            topics=["authentication", "api", "security"]
        )
        
        content_chunks = [
            "FastAPI provides built-in authentication middleware for securing API endpoints.",
            "The authentication system includes JWT tokens and OAuth2 integration."
        ]
        
        concepts = await store.extract_concepts_from_document(doc, content_chunks)
        
        assert len(concepts) > 0
        
        # Check for expected concepts
        concept_names = [c.name for c in concepts]
        assert "Authentication" in concept_names or "FastAPI" in concept_names
        
        # Verify concept properties
        for concept in concepts:
            assert concept.frequency > 0
            assert 0.0 <= concept.confidence_score <= 1.0
            assert isinstance(concept.related_topics, list)
    
    @pytest.mark.asyncio
    async def test_build_document_relationships(self, config):
        """Test building relationships between documents."""
        store = Neo4jGraphStore(config)
        
        docs = [
            DocumentNode(
                id="doc_1",
                source_name="FastAPI",
                source_url="https://fastapi.tiangolo.com/auth",
                title="Authentication",
                content_hash="hash1",
                chunk_count=2,
                quality_score=0.9,
                topics=["authentication", "security"]
            ),
            DocumentNode(
                id="doc_2",
                source_name="FastAPI",
                source_url="https://fastapi.tiangolo.com/middleware",
                title="Middleware",
                content_hash="hash2",
                chunk_count=3,
                quality_score=0.8,
                topics=["middleware", "security"]
            ),
            DocumentNode(
                id="doc_3",
                source_name="Django",
                source_url="https://django.com",
                title="Authentication",
                content_hash="hash3",
                chunk_count=1,
                quality_score=0.7,
                topics=["authentication", "web"]
            )
        ]
        
        relationships = await store.build_document_relationships(docs)
        
        assert len(relationships) > 0
        
        # Check for shared topic relationships
        topic_rels = [r for r in relationships if r.relationship_type == "RELATED_TO"]
        assert len(topic_rels) > 0
        
        # Check for same source relationships
        source_rels = [r for r in relationships if r.relationship_type == "PART_OF_SAME_SOURCE"]
        assert len(source_rels) > 0
        
        # Verify relationship properties
        for rel in relationships:
            assert 0.0 <= rel.strength <= 1.0
            assert isinstance(rel.properties, dict)
    
    @pytest.mark.asyncio
    async def test_graph_search(self, config, mock_driver, mock_session):
        """Test graph search functionality."""
        store = Neo4jGraphStore(config)
        store.driver = mock_driver
        mock_driver.session.return_value = mock_session
        
        # Mock the session context manager properly
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        # Mock search results
        mock_result = AsyncMock()
        mock_records = [
            {
                "c": {"name": "Authentication", "category": "Security"},
                "rels": [],
                "related_nodes": []
            }
        ]
        
        # Mock async iterator
        async def mock_async_iter():
            for record in mock_records:
                yield record
        
        mock_result.__aiter__ = mock_async_iter
        mock_session.run.return_value = mock_result
        
        result = await store.graph_search("authentication", search_type="concept")
        
        assert isinstance(result, GraphSearchResult)
        assert len(result.nodes) > 0
        assert "search_time_ms" in result.query_metadata
        mock_session.run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_graph_stats(self, config, mock_driver, mock_session):
        """Test getting graph statistics."""
        store = Neo4jGraphStore(config)
        store.driver = mock_driver
        mock_driver.session.return_value = mock_session
        
        # Mock the session context manager properly
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        # Mock statistics results
        mock_results = [
            {"document_count": 50},
            {"concept_count": 25},
            {"relationship_count": 100},
            {"avg_quality": 0.85},
            {"avg_relationship_strength": 0.7}
        ]
        
        mock_session.run.side_effect = [
            AsyncMock(single=AsyncMock(return_value=result)) for result in mock_results
        ]
        
        stats = await store.get_graph_stats()
        
        assert stats["document_count"] == 50
        assert stats["concept_count"] == 25
        assert stats["relationship_count"] == 100
        assert stats["average_quality"] == 0.85
        assert stats["average_relationship_strength"] == 0.7
        assert stats["connected"] is True
    
    @pytest.mark.asyncio
    async def test_close_connection(self, config, mock_driver):
        """Test closing database connection."""
        store = Neo4jGraphStore(config)
        store.driver = mock_driver
        
        await store.close()
        
        mock_driver.close.assert_called_once()
        assert store.driver is None

class TestUtilityFunctions:
    """Test utility functions."""
    
    @patch('neo4j_integration.Neo4jGraphStore')
    @pytest.mark.asyncio
    async def test_create_graph_store_success(self, mock_store_class):
        """Test successful graph store creation."""
        mock_store = AsyncMock()
        mock_store.connect.return_value = True
        mock_store_class.return_value = mock_store
        
        config = Neo4jConfig()
        store = await create_graph_store(config)
        
        assert store == mock_store
        mock_store.connect.assert_called_once()
    
    @patch('neo4j_integration.Neo4jGraphStore')
    @pytest.mark.asyncio
    async def test_create_graph_store_failure(self, mock_store_class):
        """Test graph store creation failure."""
        mock_store = AsyncMock()
        mock_store.connect.return_value = False
        mock_store_class.return_value = mock_store
        
        with pytest.raises(RuntimeError, match="Failed to connect"):
            await create_graph_store()
    
    @pytest.mark.asyncio
    async def test_migrate_documents_to_graph(self):
        """Test migrating documents to graph format."""
        mock_store = AsyncMock()
        mock_store.create_document_node.return_value = True
        mock_store.create_concept_node.return_value = True
        mock_store.create_relationship.return_value = True
        mock_store.extract_concepts_from_document.return_value = [
            ConceptNode(
                name="API",
                category="Technical",
                description="Application Programming Interface",
                frequency=5,
                confidence_score=0.8,
                related_topics=["web", "api"]
            )
        ]
        mock_store.build_document_relationships.return_value = [
            Relationship(
                from_node="doc_1",
                to_node="doc_2",
                relationship_type="RELATED_TO",
                strength=0.7,
                properties={"shared_topics": ["api"]}
            )
        ]
        
        documents = [
            {
                "id": "doc_1",
                "source_name": "FastAPI",
                "source_url": "https://fastapi.tiangolo.com",
                "title": "Getting Started",
                "content": "FastAPI is a modern web framework for building APIs",
                "content_hash": "hash1",
                "chunk_count": 1,
                "quality_score": 0.9,
                "topics": ["web", "api", "python"]
            },
            {
                "id": "doc_2",
                "source_name": "FastAPI",
                "source_url": "https://fastapi.tiangolo.com/tutorial",
                "title": "Tutorial",
                "content": "Learn how to build APIs with FastAPI step by step",
                "content_hash": "hash2",
                "chunk_count": 2,
                "quality_score": 0.85,
                "topics": ["tutorial", "api", "python"]
            }
        ]
        
        result = await migrate_documents_to_graph(mock_store, documents, extract_concepts=True)
        
        assert result is True
        assert mock_store.create_document_node.call_count == 2
        mock_store.create_concept_node.assert_called()
        mock_store.create_relationship.assert_called()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])