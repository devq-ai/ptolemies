#!/usr/bin/env python3
"""
Test suite for SurrealDB Vector Storage Integration
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

from surrealdb_integration import (
    SurrealDBVectorStore,
    VectorStoreConfig,
    DocumentChunk,
    SearchResult,
    create_vector_store,
    migrate_crawl_data_to_vector_store
)

class TestVectorStoreConfig:
    """Test VectorStoreConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = VectorStoreConfig()
        
        assert config.embedding_model == "text-embedding-3-small"
        assert config.embedding_dimensions == 1536
        assert config.similarity_threshold == 0.7
        assert config.max_results == 50
        assert config.batch_size == 100
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = VectorStoreConfig(
            embedding_model="text-embedding-ada-002",
            embedding_dimensions=1024,
            similarity_threshold=0.8,
            max_results=25,
            batch_size=50
        )
        
        assert config.embedding_model == "text-embedding-ada-002"
        assert config.embedding_dimensions == 1024
        assert config.similarity_threshold == 0.8
        assert config.max_results == 25
        assert config.batch_size == 50

class TestDocumentChunk:
    """Test DocumentChunk dataclass."""
    
    def test_document_chunk_creation(self):
        """Test document chunk creation with required fields."""
        chunk = DocumentChunk(
            id="test_1",
            source_name="FastAPI",
            source_url="https://fastapi.tiangolo.com",
            title="Getting Started",
            content="FastAPI is a modern web framework",
            chunk_index=0,
            total_chunks=5,
            quality_score=0.95,
            topics=["web", "python", "api"]
        )
        
        assert chunk.id == "test_1"
        assert chunk.source_name == "FastAPI"
        assert chunk.quality_score == 0.95
        assert chunk.topics == ["web", "python", "api"]
        assert chunk.embedding is None  # Optional field
    
    def test_document_chunk_with_embedding(self):
        """Test document chunk with embedding vector."""
        embedding = [0.1, 0.2, 0.3]
        chunk = DocumentChunk(
            id="test_2",
            source_name="Test",
            source_url="https://test.com",
            title="Test",
            content="Test content",
            chunk_index=0,
            total_chunks=1,
            quality_score=0.8,
            topics=["test"],
            embedding=embedding
        )
        
        assert chunk.embedding == embedding

class TestSearchResult:
    """Test SearchResult dataclass."""
    
    def test_search_result_creation(self):
        """Test search result creation."""
        chunk = DocumentChunk(
            id="result_1",
            source_name="Test",
            source_url="https://test.com",
            title="Test Result",
            content="Test content for search",
            chunk_index=0,
            total_chunks=1,
            quality_score=0.9,
            topics=["search", "test"]
        )
        
        result = SearchResult(
            document=chunk,
            similarity_score=0.87,
            rank=1
        )
        
        assert result.document == chunk
        assert result.similarity_score == 0.87
        assert result.rank == 1

class TestSurrealDBVectorStore:
    """Test SurrealDB vector store implementation."""
    
    @pytest.fixture
    def config(self):
        """Test configuration."""
        return VectorStoreConfig(batch_size=2)  # Small batch for testing
    
    @pytest.fixture
    def mock_surrealdb(self):
        """Mock SurrealDB connection."""
        mock_db = AsyncMock()
        mock_db.connect = AsyncMock()
        mock_db.signin = AsyncMock()
        mock_db.use = AsyncMock()
        mock_db.query = AsyncMock()
        mock_db.create = AsyncMock()
        mock_db.close = AsyncMock()
        return mock_db
    
    @pytest.fixture
    def mock_openai(self):
        """Mock OpenAI client."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=[0.1, 0.2, 0.3]),
            Mock(embedding=[0.4, 0.5, 0.6])
        ]
        mock_client.embeddings.create.return_value = mock_response
        return mock_client
    
    def test_vector_store_initialization(self, config):
        """Test vector store initialization."""
        store = SurrealDBVectorStore(config)
        
        assert store.config == config
        assert store.db is None
        assert store.openai_client is None  # No API key in test
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
    @patch('surrealdb_integration.openai.OpenAI')
    def test_openai_client_initialization(self, mock_openai_class, config):
        """Test OpenAI client initialization with API key."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        store = SurrealDBVectorStore(config)
        
        assert store.openai_client == mock_client
        mock_openai_class.assert_called_once_with(api_key="test_key")
    
    @pytest.mark.asyncio
    @patch('surrealdb_integration.Surreal')
    @patch.dict(os.environ, {
        "SURREALDB_URL": "ws://test:8000/rpc",
        "SURREALDB_USERNAME": "testuser",
        "SURREALDB_PASSWORD": "testpass"
    })
    @pytest.mark.asyncio
    async def test_connect_success(self, mock_surreal_class, config, mock_surrealdb):
        """Test successful SurrealDB connection."""
        mock_surreal_class.return_value = mock_surrealdb
        
        store = SurrealDBVectorStore(config)
        result = await store.connect()
        
        assert result is True
        assert store.db == mock_surrealdb
        mock_surrealdb.connect.assert_called_once_with("ws://test:8000/rpc")
        mock_surrealdb.signin.assert_called_once_with({"user": "testuser", "pass": "testpass"})
        mock_surrealdb.use.assert_called_once_with("ptolemies", "knowledge")
    
    @pytest.mark.asyncio
    @patch('surrealdb_integration.Surreal')
    @pytest.mark.asyncio
    async def test_connect_failure(self, mock_surreal_class, config):
        """Test SurrealDB connection failure."""
        mock_db = AsyncMock()
        mock_db.connect.side_effect = Exception("Connection failed")
        mock_surreal_class.return_value = mock_db
        
        store = SurrealDBVectorStore(config)
        result = await store.connect()
        
        assert result is False
        assert store.db is None
    
    @pytest.mark.asyncio
    async def test_schema_initialization(self, config, mock_surrealdb):
        """Test schema initialization."""
        store = SurrealDBVectorStore(config)
        store.db = mock_surrealdb
        
        await store._initialize_schema()
        
        # Verify that schema queries were executed
        assert mock_surrealdb.query.call_count >= 3  # At least 3 schema queries
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
    @pytest.mark.asyncio
    async def test_generate_embeddings_success(self, config, mock_openai):
        """Test successful embedding generation."""
        store = SurrealDBVectorStore(config)
        store.openai_client = mock_openai
        
        texts = ["Hello world", "Test content"]
        embeddings = await store.generate_embeddings(texts)
        
        assert len(embeddings) == 2
        assert embeddings[0] == [0.1, 0.2, 0.3]
        assert embeddings[1] == [0.4, 0.5, 0.6]
        mock_openai.embeddings.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_no_client(self, config):
        """Test embedding generation without OpenAI client."""
        store = SurrealDBVectorStore(config)
        store.openai_client = None
        
        texts = ["Hello world", "Test content"]
        embeddings = await store.generate_embeddings(texts)
        
        assert len(embeddings) == 2
        assert len(embeddings[0]) == config.embedding_dimensions
        assert all(val == 0.0 for val in embeddings[0])
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
    @pytest.mark.asyncio
    async def test_store_document_chunks(self, config, mock_surrealdb, mock_openai):
        """Test storing document chunks with embeddings."""
        store = SurrealDBVectorStore(config)
        store.db = mock_surrealdb
        store.openai_client = mock_openai
        
        chunks = [
            DocumentChunk(
                id="test_1",
                source_name="Test",
                source_url="https://test.com",
                title="Test 1",
                content="First test content",
                chunk_index=0,
                total_chunks=2,
                quality_score=0.9,
                topics=["test"]
            ),
            DocumentChunk(
                id="test_2",
                source_name="Test",
                source_url="https://test.com",
                title="Test 2",
                content="Second test content",
                chunk_index=1,
                total_chunks=2,
                quality_score=0.8,
                topics=["test"]
            )
        ]
        
        result = await store.store_document_chunks(chunks)
        
        assert result is True
        # Verify embeddings were generated
        mock_openai.embeddings.create.assert_called_once()
        # Verify chunks were stored
        assert mock_surrealdb.create.call_count == 2
    
    @pytest.mark.asyncio
    async def test_store_document_chunks_no_db(self, config):
        """Test storing chunks without database connection."""
        store = SurrealDBVectorStore(config)
        
        chunks = [DocumentChunk(
            id="test_1",
            source_name="Test",
            source_url="https://test.com",
            title="Test",
            content="Test content",
            chunk_index=0,
            total_chunks=1,
            quality_score=0.9,
            topics=["test"]
        )]
        
        with pytest.raises(RuntimeError, match="Not connected to SurrealDB"):
            await store.store_document_chunks(chunks)
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
    @pytest.mark.asyncio
    async def test_semantic_search(self, config, mock_surrealdb, mock_openai):
        """Test semantic search functionality."""
        store = SurrealDBVectorStore(config)
        store.db = mock_surrealdb
        store.openai_client = mock_openai
        
        # Mock search results
        mock_result = [[
            {
                "id": "test_1",
                "source_name": "Test",
                "source_url": "https://test.com",
                "title": "Test Result",
                "content": "Test content",
                "chunk_index": 0,
                "total_chunks": 1,
                "quality_score": 0.9,
                "topics": ["test"],
                "embedding": [0.1, 0.2, 0.3],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "similarity": 0.85
            }
        ]]
        mock_surrealdb.query.return_value = mock_result
        
        results = await store.semantic_search("test query", limit=5)
        
        assert len(results) == 1
        assert isinstance(results[0], SearchResult)
        assert results[0].similarity_score == 0.85
        assert results[0].rank == 1
        assert results[0].document.source_name == "Test"
    
    @pytest.mark.asyncio
    async def test_semantic_search_with_filters(self, config, mock_surrealdb, mock_openai):
        """Test semantic search with source filter and quality threshold."""
        store = SurrealDBVectorStore(config)
        store.db = mock_surrealdb
        store.openai_client = mock_openai
        
        mock_surrealdb.query.return_value = [[]]  # Empty result
        
        await store.semantic_search(
            "test query",
            source_filter=["FastAPI", "Logfire"],
            quality_threshold=0.8
        )
        
        # Verify query was called with filters
        mock_surrealdb.query.assert_called_once()
        query_args = mock_surrealdb.query.call_args[0][0]
        assert "source_name IN" in query_args
        assert "quality_score >= 0.8" in query_args
    
    @pytest.mark.asyncio
    async def test_get_document_chunks(self, config, mock_surrealdb):
        """Test retrieving document chunks."""
        store = SurrealDBVectorStore(config)
        store.db = mock_surrealdb
        
        mock_result = [[
            {
                "id": "test_1",
                "source_name": "Test",
                "source_url": "https://test.com",
                "title": "Test",
                "content": "Test content",
                "chunk_index": 0,
                "total_chunks": 1,
                "quality_score": 0.9,
                "topics": ["test"],
                "embedding": [0.1, 0.2, 0.3],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        ]]
        mock_surrealdb.query.return_value = mock_result
        
        chunks = await store.get_document_chunks(source_name="Test", limit=10)
        
        assert len(chunks) == 1
        assert isinstance(chunks[0], DocumentChunk)
        assert chunks[0].source_name == "Test"
    
    @pytest.mark.asyncio
    async def test_get_storage_stats(self, config, mock_surrealdb):
        """Test getting storage statistics."""
        store = SurrealDBVectorStore(config)
        store.db = mock_surrealdb
        
        # Mock statistics queries
        mock_results = [
            [[{"count": 100}]],  # Total count
            [[{"source_name": "FastAPI", "count": 50}, {"source_name": "Logfire", "count": 50}]],  # By source
            [[{"avg_quality": 0.85}]],  # Average quality
            [[{"earliest": "2024-01-01T00:00:00Z", "latest": "2024-01-02T00:00:00Z"}]]  # Date range
        ]
        mock_surrealdb.query.side_effect = mock_results
        
        stats = await store.get_storage_stats()
        
        assert stats["total_chunks"] == 100
        assert stats["chunks_by_source"] == {"FastAPI": 50, "Logfire": 50}
        assert stats["average_quality"] == 0.85
        assert "earliest" in stats["date_range"]
    
    @pytest.mark.asyncio
    async def test_close_connection(self, config, mock_surrealdb):
        """Test closing database connection."""
        store = SurrealDBVectorStore(config)
        store.db = mock_surrealdb
        
        await store.close()
        
        mock_surrealdb.close.assert_called_once()
        assert store.db is None

class TestUtilityFunctions:
    """Test utility functions."""
    
    @patch('surrealdb_integration.SurrealDBVectorStore')
    @pytest.mark.asyncio
    async def test_create_vector_store_success(self, mock_store_class):
        """Test successful vector store creation."""
        mock_store = AsyncMock()
        mock_store.connect.return_value = True
        mock_store_class.return_value = mock_store
        
        config = VectorStoreConfig()
        store = await create_vector_store(config)
        
        assert store == mock_store
        mock_store.connect.assert_called_once()
    
    @patch('surrealdb_integration.SurrealDBVectorStore')
    @pytest.mark.asyncio
    async def test_create_vector_store_failure(self, mock_store_class):
        """Test vector store creation failure."""
        mock_store = AsyncMock()
        mock_store.connect.return_value = False
        mock_store_class.return_value = mock_store
        
        with pytest.raises(RuntimeError, match="Failed to connect"):
            await create_vector_store()
    
    @pytest.mark.asyncio
    async def test_migrate_crawl_data(self):
        """Test migrating crawl data to vector store format."""
        crawl_results = [
            {
                "source_name": "FastAPI",
                "source_url": "https://fastapi.tiangolo.com",
                "title": "Getting Started",
                "content": "FastAPI tutorial content",
                "quality_score": 0.9,
                "topics": ["web", "python"]
            },
            {
                "source_name": "Logfire",
                "source_url": "https://logfire.dev",
                "title": "Observability",
                "content": "Logfire monitoring content",
                "quality_score": 0.85,
                "topics": ["monitoring", "observability"]
            }
        ]
        
        mock_store = AsyncMock()
        mock_store.store_document_chunks.return_value = True
        
        result = await migrate_crawl_data_to_vector_store(mock_store, crawl_results)
        
        assert result is True
        mock_store.store_document_chunks.assert_called_once()
        
        # Verify chunks were created correctly
        chunks = mock_store.store_document_chunks.call_args[0][0]
        assert len(chunks) == 2
        assert chunks[0].source_name == "FastAPI"
        assert chunks[1].source_name == "Logfire"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])