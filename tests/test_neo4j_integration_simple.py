#!/usr/bin/env python3
"""
Simplified test suite for Neo4j Graph Integration
Tests core functionality without complex async mocking.
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

class TestNeo4jConfigSimple:
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

class TestDataClassesSimple:
    """Test data classes."""
    
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

class TestNeo4jGraphStoreSimple:
    """Test Neo4j graph store core functionality."""
    
    def test_graph_store_initialization(self):
        """Test graph store initialization."""
        config = Neo4jConfig(database="test_ptolemies")
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
    async def test_extract_concepts_from_document(self):
        """Test concept extraction from document."""
        config = Neo4jConfig()
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
    async def test_build_document_relationships(self):
        """Test building relationships between documents."""
        config = Neo4jConfig()
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
    async def test_connection_error_handling(self):
        """Test connection error handling."""
        config = Neo4jConfig()
        store = Neo4jGraphStore(config)
        
        # Test operations without connection
        with pytest.raises(RuntimeError, match="Not connected to Neo4j"):
            await store.graph_search("test query")
        
        with pytest.raises(RuntimeError, match="Not connected to Neo4j"):
            await store.get_graph_stats()
    
    @pytest.mark.asyncio
    async def test_close_connection(self):
        """Test closing database connection."""
        config = Neo4jConfig()
        store = Neo4jGraphStore(config)
        
        # Test closing when no connection exists
        await store.close()
        assert store.driver is None

class TestUtilityFunctionsSimple:
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

class TestConceptExtractionLogic:
    """Test concept extraction logic in detail."""
    
    @pytest.mark.asyncio
    async def test_concept_extraction_technical_terms(self):
        """Test extraction of technical concepts."""
        config = Neo4jConfig()
        store = Neo4jGraphStore(config)
        
        doc = DocumentNode(
            id="doc_tech",
            source_name="Technical Docs",
            source_url="https://example.com/tech",
            title="API Design Guide",
            content_hash="hash_tech",
            chunk_count=1,
            quality_score=0.95,
            topics=["api", "design", "technical"]
        )
        
        content_chunks = [
            "API design involves creating endpoints, middleware, and authentication systems. "
            "Database integration requires proper schema design and query optimization. "
            "Monitoring systems track performance and provide insights into system behavior."
        ]
        
        concepts = await store.extract_concepts_from_document(doc, content_chunks)
        
        # Should extract technical concepts
        concept_names = [c.name.lower() for c in concepts]
        expected_concepts = ["api", "database", "authentication", "middleware", "monitoring"]
        
        found_concepts = [name for name in expected_concepts if any(name in cn for cn in concept_names)]
        assert len(found_concepts) > 0, f"Expected to find some of {expected_concepts}, got {concept_names}"
    
    @pytest.mark.asyncio
    async def test_concept_extraction_framework_specific(self):
        """Test extraction of framework-specific concepts."""
        config = Neo4jConfig()
        store = Neo4jGraphStore(config)
        
        doc = DocumentNode(
            id="doc_framework",
            source_name="Framework Guide",
            source_url="https://example.com/framework",
            title="Modern Web Development",
            content_hash="hash_framework",
            chunk_count=1,
            quality_score=0.9,
            topics=["framework", "web", "development"]
        )
        
        content_chunks = [
            "FastAPI provides excellent performance for Python web applications. "
            "Logfire offers comprehensive monitoring and observability features. "
            "SurrealDB delivers multi-model database capabilities, while Neo4j excels at graph relationships. "
            "PyTest ensures thorough testing coverage, and Redis provides fast caching solutions."
        ]
        
        concepts = await store.extract_concepts_from_document(doc, content_chunks)
        
        # Should extract framework concepts
        concept_names = [c.name for c in concepts]
        framework_concepts = ["FastAPI", "Logfire", "SurrealDB", "Neo4j", "PyTest", "Redis"]
        
        found_frameworks = [name for name in framework_concepts if name in concept_names]
        assert len(found_frameworks) >= 3, f"Expected to find at least 3 frameworks, got {found_frameworks}"

class TestRelationshipBuilding:
    """Test relationship building logic."""
    
    @pytest.mark.asyncio
    async def test_topic_based_relationships(self):
        """Test relationships based on shared topics."""
        config = Neo4jConfig()
        store = Neo4jGraphStore(config)
        
        docs = [
            DocumentNode(
                id="auth_guide",
                source_name="Security",
                source_url="https://security.com/auth",
                title="Authentication Guide",
                content_hash="hash_auth",
                chunk_count=1,
                quality_score=0.95,
                topics=["authentication", "security", "oauth"]
            ),
            DocumentNode(
                id="jwt_tutorial",
                source_name="Security",
                source_url="https://security.com/jwt",
                title="JWT Tutorial",
                content_hash="hash_jwt",
                chunk_count=1,
                quality_score=0.9,
                topics=["authentication", "jwt", "tokens"]
            ),
            DocumentNode(
                id="api_docs",
                source_name="API",
                source_url="https://api.com/docs",
                title="API Documentation",
                content_hash="hash_api",
                chunk_count=1,
                quality_score=0.8,
                topics=["api", "documentation", "endpoints"]
            )
        ]
        
        relationships = await store.build_document_relationships(docs)
        
        # Should create relationship between auth_guide and jwt_tutorial (shared: authentication)
        auth_relations = [r for r in relationships 
                         if (r.from_node == "auth_guide" and r.to_node == "jwt_tutorial") or
                            (r.from_node == "jwt_tutorial" and r.to_node == "auth_guide")]
        
        assert len(auth_relations) > 0, "Should create relationship between documents with shared topics"
        
        # Verify relationship properties
        for rel in auth_relations:
            if rel.relationship_type == "RELATED_TO":
                assert "shared_topics" in rel.properties
                assert "authentication" in rel.properties["shared_topics"]
    
    @pytest.mark.asyncio
    async def test_same_source_relationships(self):
        """Test relationships based on same source."""
        config = Neo4jConfig()
        store = Neo4jGraphStore(config)
        
        docs = [
            DocumentNode(
                id="fastapi_intro",
                source_name="FastAPI",
                source_url="https://fastapi.tiangolo.com/intro",
                title="Introduction",
                content_hash="hash_intro",
                chunk_count=1,
                quality_score=0.9,
                topics=["introduction", "basics"]
            ),
            DocumentNode(
                id="fastapi_advanced",
                source_name="FastAPI",
                source_url="https://fastapi.tiangolo.com/advanced",
                title="Advanced Features",
                content_hash="hash_advanced",
                chunk_count=1,
                quality_score=0.85,
                topics=["advanced", "features"]
            ),
            DocumentNode(
                id="django_intro",
                source_name="Django",
                source_url="https://django.com/intro",
                title="Django Introduction",
                content_hash="hash_django",
                chunk_count=1,
                quality_score=0.8,
                topics=["introduction", "django"]
            )
        ]
        
        relationships = await store.build_document_relationships(docs)
        
        # Should create same-source relationship between FastAPI docs
        same_source_relations = [r for r in relationships 
                               if r.relationship_type == "PART_OF_SAME_SOURCE"]
        
        assert len(same_source_relations) > 0, "Should create relationships between documents from same source"
        
        # Verify same source relationship
        fastapi_relations = [r for r in same_source_relations 
                           if r.properties.get("source_name") == "FastAPI"]
        
        assert len(fastapi_relations) > 0, "Should create FastAPI same-source relationship"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])