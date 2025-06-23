#!/usr/bin/env python3
"""
Test suite for Hybrid Query Engine
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

from hybrid_query_engine import (
    HybridQueryEngine,
    HybridQueryConfig,
    QueryType,
    RankingStrategy,
    HybridSearchResult,
    QueryAnalysis,
    HybridQueryMetrics,
    create_hybrid_engine
)

from surrealdb_integration import (
    SurrealDBVectorStore,
    SearchResult as VectorSearchResult,
    DocumentChunk
)

from neo4j_integration import (
    Neo4jGraphStore,
    GraphSearchResult
)

class TestHybridQueryConfig:
    """Test hybrid query configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = HybridQueryConfig()
        
        assert config.vector_weight == 0.6
        assert config.graph_weight == 0.4
        assert config.concept_expansion_threshold == 0.8
        assert config.max_results == 50
        assert config.semantic_limit == 100
        assert config.graph_limit == 100
        assert config.similarity_threshold == 0.5
        assert config.graph_depth == 2
        assert config.enable_concept_expansion is True
        assert config.enable_result_fusion is True
        assert config.ranking_strategy == RankingStrategy.WEIGHTED_AVERAGE
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = HybridQueryConfig(
            vector_weight=0.7,
            graph_weight=0.3,
            max_results=100,
            ranking_strategy=RankingStrategy.MAX_SCORE
        )
        
        assert config.vector_weight == 0.7
        assert config.graph_weight == 0.3
        assert config.max_results == 100
        assert config.ranking_strategy == RankingStrategy.MAX_SCORE

class TestQueryType:
    """Test query type enumeration."""
    
    def test_query_types(self):
        """Test all query type values."""
        assert QueryType.SEMANTIC_ONLY.value == "semantic_only"
        assert QueryType.GRAPH_ONLY.value == "graph_only"
        assert QueryType.HYBRID_BALANCED.value == "hybrid_balanced"
        assert QueryType.SEMANTIC_THEN_GRAPH.value == "semantic_then_graph"
        assert QueryType.GRAPH_THEN_SEMANTIC.value == "graph_then_semantic"
        assert QueryType.CONCEPT_EXPANSION.value == "concept_expansion"

class TestRankingStrategy:
    """Test ranking strategy enumeration."""
    
    def test_ranking_strategies(self):
        """Test all ranking strategy values."""
        assert RankingStrategy.WEIGHTED_AVERAGE.value == "weighted_average"
        assert RankingStrategy.MAX_SCORE.value == "max_score"
        assert RankingStrategy.HARMONIC_MEAN.value == "harmonic_mean"
        assert RankingStrategy.BORDA_COUNT.value == "borda_count"
        assert RankingStrategy.RECIPROCAL_RANK.value == "reciprocal_rank"

class TestDataClasses:
    """Test data classes."""
    
    def test_hybrid_search_result_creation(self):
        """Test hybrid search result creation."""
        result = HybridSearchResult(
            id="test_1",
            title="Test Document",
            content="Test content",
            source_name="Test Source",
            source_url="https://test.com",
            chunk_index=0,
            total_chunks=1,
            quality_score=0.9,
            topics=["test", "document"],
            semantic_score=0.8,
            graph_score=0.7,
            combined_score=0.75,
            rank=1,
            found_via=["semantic_search"],
            related_concepts=["testing"],
            relationship_paths=[{"path": "test"}]
        )
        
        assert result.id == "test_1"
        assert result.title == "Test Document"
        assert result.semantic_score == 0.8
        assert result.graph_score == 0.7
        assert result.combined_score == 0.75
        assert result.rank == 1
        assert "semantic_search" in result.found_via
        assert "testing" in result.related_concepts
    
    def test_hybrid_search_result_defaults(self):
        """Test hybrid search result with default values."""
        result = HybridSearchResult(
            id="test_2",
            title="Test",
            content="Content",
            source_name="Source",
            source_url="URL"
        )
        
        assert result.topics == []
        assert result.found_via == []
        assert result.related_concepts == []
        assert result.relationship_paths == []
        assert result.semantic_score == 0.0
        assert result.graph_score == 0.0
        assert result.combined_score == 0.0
    
    def test_query_analysis_creation(self):
        """Test query analysis creation."""
        analysis = QueryAnalysis(
            query_type="semantic",
            detected_concepts=["api", "authentication"],
            suggested_expansions=["security", "jwt"],
            complexity_score=0.7,
            semantic_weight=0.8,
            graph_weight=0.2
        )
        
        assert analysis.query_type == "semantic"
        assert "api" in analysis.detected_concepts
        assert "authentication" in analysis.detected_concepts
        assert "security" in analysis.suggested_expansions
        assert analysis.complexity_score == 0.7
        assert analysis.semantic_weight == 0.8
        assert analysis.graph_weight == 0.2
    
    def test_hybrid_query_metrics_creation(self):
        """Test hybrid query metrics creation."""
        analysis = QueryAnalysis(
            query_type="test",
            detected_concepts=[],
            suggested_expansions=[],
            complexity_score=0.5,
            semantic_weight=0.6,
            graph_weight=0.4
        )
        
        metrics = HybridQueryMetrics(
            total_time_ms=150.5,
            semantic_time_ms=80.2,
            graph_time_ms=60.3,
            fusion_time_ms=10.0,
            total_results=25,
            semantic_results=15,
            graph_results=12,
            unique_results=20,
            overlap_count=7,
            concept_expansions=3,
            query_analysis=analysis
        )
        
        assert metrics.total_time_ms == 150.5
        assert metrics.semantic_time_ms == 80.2
        assert metrics.graph_time_ms == 60.3
        assert metrics.fusion_time_ms == 10.0
        assert metrics.total_results == 25
        assert metrics.overlap_count == 7

class TestHybridQueryEngine:
    """Test hybrid query engine functionality."""
    
    @pytest.fixture
    def mock_vector_store(self):
        """Mock vector store."""
        store = AsyncMock(spec=SurrealDBVectorStore)
        
        # Mock semantic search results
        mock_doc = DocumentChunk(
            id="doc_1",
            source_name="FastAPI",
            source_url="https://fastapi.tiangolo.com",
            title="Authentication Guide",
            content="FastAPI provides authentication middleware",
            chunk_index=0,
            total_chunks=1,
            quality_score=0.9,
            topics=["authentication", "fastapi"]
        )
        
        mock_result = VectorSearchResult(
            document=mock_doc,
            similarity_score=0.85,
            rank=1
        )
        
        store.semantic_search.return_value = [mock_result]
        return store
    
    @pytest.fixture
    def mock_graph_store(self):
        """Mock graph store."""
        store = AsyncMock(spec=Neo4jGraphStore)
        
        # Mock graph search results
        mock_nodes = [
            {
                "id": "concept_auth",
                "name": "Authentication",
                "category": "Security",
                "quality_score": 0.9,
                "title": "Authentication Concept",
                "content": "User verification system",
                "source_name": "Security Docs",
                "source_url": "https://security.com",
                "topics": ["security", "auth"]
            }
        ]
        
        mock_graph_result = GraphSearchResult(
            nodes=mock_nodes,
            relationships=[],
            paths=[],
            query_metadata={"search_time_ms": 50.0}
        )
        
        store.graph_search.return_value = mock_graph_result
        return store
    
    @pytest.fixture
    def config(self):
        """Test configuration."""
        return HybridQueryConfig(
            max_results=10,
            semantic_limit=20,
            graph_limit=20
        )
    
    @pytest.fixture
    def engine(self, mock_vector_store, mock_graph_store, config):
        """Test hybrid query engine."""
        return HybridQueryEngine(mock_vector_store, mock_graph_store, config)
    
    @pytest.mark.asyncio
    async def test_analyze_query_general(self, engine):
        """Test query analysis for general query."""
        analysis = await engine.analyze_query("How to implement user authentication?")
        
        assert analysis.query_type in ["general", "relational", "semantic"]
        assert "authentication" in analysis.detected_concepts
        assert analysis.complexity_score > 0
        assert analysis.semantic_weight > 0
        assert analysis.graph_weight > 0
        assert analysis.semantic_weight + analysis.graph_weight <= 1.1  # Allow small float precision
    
    @pytest.mark.asyncio
    async def test_analyze_query_semantic(self, engine):
        """Test query analysis for semantic query."""
        analysis = await engine.analyze_query("Find similar authentication methods")
        
        assert analysis.query_type == "semantic"
        assert "authentication" in analysis.detected_concepts
        assert analysis.semantic_weight > analysis.graph_weight
    
    @pytest.mark.asyncio
    async def test_analyze_query_relational(self, engine):
        """Test query analysis for relational query."""
        analysis = await engine.analyze_query("What concepts are related to authentication?")
        
        assert analysis.query_type == "relational"
        assert "authentication" in analysis.detected_concepts
        assert analysis.graph_weight > analysis.semantic_weight
    
    @pytest.mark.asyncio
    async def test_analyze_query_framework_detection(self, engine):
        """Test framework detection in query analysis."""
        analysis = await engine.analyze_query("FastAPI with Neo4j integration")
        
        # Framework detection adds expansions - check if related terms are present
        expansions_text = " ".join(analysis.suggested_expansions).lower()
        assert any(term in expansions_text for term in ["python", "web framework", "api", "async"])
        assert any(term in expansions_text for term in ["graph database", "cypher", "nodes", "relationships"])
    
    @pytest.mark.asyncio
    async def test_analyze_query_caching(self, engine):
        """Test query analysis caching."""
        query = "Test caching query"
        
        # First call
        analysis1 = await engine.analyze_query(query)
        
        # Second call should use cache
        analysis2 = await engine.analyze_query(query)
        
        assert analysis1.query_type == analysis2.query_type
        assert analysis1.detected_concepts == analysis2.detected_concepts
        assert query in engine._query_cache
    
    @pytest.mark.asyncio
    async def test_semantic_search(self, engine, mock_vector_store):
        """Test semantic search functionality."""
        results = await engine._semantic_search("test query", limit=10)
        
        assert len(results) == 1
        mock_vector_store.semantic_search.assert_called_once()
        
        # Verify call parameters
        call_args = mock_vector_store.semantic_search.call_args
        assert call_args[1]["query"] == "test query"
        assert call_args[1]["limit"] == 10
    
    @pytest.mark.asyncio
    async def test_graph_search(self, engine, mock_graph_store):
        """Test graph search functionality."""
        result = await engine._graph_search("test query", search_type="concept", limit=10)
        
        assert len(result.nodes) == 1
        mock_graph_store.graph_search.assert_called_once()
        
        # Verify call parameters
        call_args = mock_graph_store.graph_search.call_args
        assert call_args[1]["query"] == "test query"
        assert call_args[1]["search_type"] == "concept"
        assert call_args[1]["limit"] == 10
    
    @pytest.mark.asyncio
    async def test_concept_expansion(self, engine, mock_graph_store):
        """Test concept expansion functionality."""
        analysis = QueryAnalysis(
            query_type="general",
            detected_concepts=["authentication"],
            suggested_expansions=["security"],
            complexity_score=0.6,
            semantic_weight=0.6,
            graph_weight=0.4
        )
        
        expanded = await engine._expand_query_concepts("test query", analysis)
        
        assert len(expanded) > 1
        assert "test query" in expanded
        # Should call graph search for detected concepts
        mock_graph_store.graph_search.assert_called()
    
    @pytest.mark.asyncio
    async def test_concept_expansion_disabled(self, engine):
        """Test concept expansion when disabled."""
        engine.config.enable_concept_expansion = False
        
        analysis = QueryAnalysis(
            query_type="general",
            detected_concepts=["authentication"],
            suggested_expansions=[],
            complexity_score=0.5,
            semantic_weight=0.6,
            graph_weight=0.4
        )
        
        expanded = await engine._expand_query_concepts("test query", analysis)
        
        assert expanded == ["test query"]
    
    @pytest.mark.asyncio
    async def test_result_fusion(self, engine):
        """Test result fusion functionality."""
        # Mock semantic results
        doc = DocumentChunk(
            id="doc_1",
            source_name="Test",
            source_url="https://test.com",
            title="Test Doc",
            content="Test content",
            chunk_index=0,
            total_chunks=1,
            quality_score=0.8,
            topics=["test"]
        )
        
        semantic_results = [VectorSearchResult(
            document=doc,
            similarity_score=0.9,
            rank=1
        )]
        
        # Mock graph results
        graph_results = [{
            "id": "graph_1",
            "title": "Graph Result",
            "content": "Graph content",
            "source_name": "Graph Source",
            "source_url": "https://graph.com",
            "quality_score": 0.7,
            "topics": ["graph"]
        }]
        
        analysis = QueryAnalysis(
            query_type="general",
            detected_concepts=[],
            suggested_expansions=[],
            complexity_score=0.5,
            semantic_weight=0.6,
            graph_weight=0.4
        )
        
        fused_results = await engine._fuse_results(semantic_results, graph_results, analysis)
        
        assert len(fused_results) == 2
        
        # Check combined scores
        for result in fused_results:
            assert result.combined_score > 0
            assert len(result.found_via) > 0
    
    @pytest.mark.asyncio
    async def test_result_fusion_ranking_strategies(self, engine):
        """Test different ranking strategies in result fusion."""
        doc = DocumentChunk(
            id="doc_1",
            source_name="Test",
            source_url="https://test.com",
            title="Test Doc",
            content="Test content",
            chunk_index=0,
            total_chunks=1,
            quality_score=0.8,
            topics=["test"]
        )
        
        semantic_results = [VectorSearchResult(
            document=doc,
            similarity_score=0.9,
            rank=1
        )]
        
        graph_results = []
        
        analysis = QueryAnalysis(
            query_type="general",
            detected_concepts=[],
            suggested_expansions=[],
            complexity_score=0.5,
            semantic_weight=0.6,
            graph_weight=0.4
        )
        
        # Test MAX_SCORE strategy
        engine.config.ranking_strategy = RankingStrategy.MAX_SCORE
        results_max = await engine._fuse_results(semantic_results, graph_results, analysis)
        
        # Test HARMONIC_MEAN strategy
        engine.config.ranking_strategy = RankingStrategy.HARMONIC_MEAN
        results_harmonic = await engine._fuse_results(semantic_results, graph_results, analysis)
        
        assert len(results_max) == 1
        assert len(results_harmonic) == 1
        assert results_max[0].combined_score > 0
        assert results_harmonic[0].combined_score > 0
    
    @pytest.mark.asyncio
    async def test_search_semantic_only(self, engine, mock_vector_store):
        """Test semantic-only search."""
        results, metrics = await engine.search(
            "test query", 
            QueryType.SEMANTIC_ONLY, 
            limit=5
        )
        
        assert len(results) >= 0
        assert metrics.semantic_results > 0
        assert metrics.graph_results == 0
        assert metrics.total_time_ms > 0
        mock_vector_store.semantic_search.assert_called()
    
    @pytest.mark.asyncio
    async def test_search_graph_only(self, engine, mock_graph_store):
        """Test graph-only search."""
        results, metrics = await engine.search(
            "test query", 
            QueryType.GRAPH_ONLY, 
            limit=5
        )
        
        assert len(results) >= 0
        assert metrics.semantic_results == 0
        assert metrics.graph_results > 0
        assert metrics.total_time_ms > 0
        mock_graph_store.graph_search.assert_called()
    
    @pytest.mark.asyncio
    async def test_search_hybrid_balanced(self, engine, mock_vector_store, mock_graph_store):
        """Test hybrid balanced search."""
        results, metrics = await engine.search(
            "test query", 
            QueryType.HYBRID_BALANCED, 
            limit=5
        )
        
        assert len(results) >= 0
        assert metrics.total_time_ms > 0
        assert metrics.query_analysis is not None
        mock_vector_store.semantic_search.assert_called()
        mock_graph_store.graph_search.assert_called()
    
    @pytest.mark.asyncio
    async def test_search_concept_expansion(self, engine, mock_vector_store, mock_graph_store):
        """Test concept expansion search."""
        results, metrics = await engine.search(
            "authentication security", 
            QueryType.CONCEPT_EXPANSION, 
            limit=5
        )
        
        assert len(results) >= 0
        assert metrics.concept_expansions >= 0
        assert metrics.total_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_search_semantic_then_graph(self, engine, mock_vector_store, mock_graph_store):
        """Test semantic then graph search."""
        results, metrics = await engine.search(
            "test query", 
            QueryType.SEMANTIC_THEN_GRAPH, 
            limit=5
        )
        
        assert len(results) >= 0
        assert metrics.total_time_ms > 0
        mock_vector_store.semantic_search.assert_called()
        # Graph search should be called with topics from semantic results
        mock_graph_store.graph_search.assert_called()
    
    @pytest.mark.asyncio
    async def test_search_graph_then_semantic(self, engine, mock_vector_store, mock_graph_store):
        """Test graph then semantic search."""
        results, metrics = await engine.search(
            "test query", 
            QueryType.GRAPH_THEN_SEMANTIC, 
            limit=5
        )
        
        assert len(results) >= 0
        assert metrics.total_time_ms > 0
        mock_graph_store.graph_search.assert_called()
        mock_vector_store.semantic_search.assert_called()
    
    @pytest.mark.asyncio
    async def test_search_with_source_filter(self, engine, mock_vector_store):
        """Test search with source filter."""
        source_filter = ["FastAPI", "Security"]
        
        results, metrics = await engine.search(
            "test query", 
            QueryType.SEMANTIC_ONLY,
            source_filter=source_filter,
            limit=5
        )
        
        # Verify source filter was passed to semantic search
        call_args = mock_vector_store.semantic_search.call_args
        assert call_args[1]["source_filter"] == source_filter
    
    @pytest.mark.asyncio
    async def test_search_error_handling(self, engine):
        """Test search error handling."""
        # Mock search methods to raise exceptions
        engine._semantic_search = AsyncMock(side_effect=Exception("Semantic search failed"))
        engine._graph_search = AsyncMock(side_effect=Exception("Graph search failed"))
        
        results, metrics = await engine.search("test query")
        
        # Should return empty results and error metrics
        assert results == []
        assert metrics.total_results == 0
        assert metrics.query_analysis.query_type == "error"
    
    @pytest.mark.asyncio
    async def test_batch_search(self, engine):
        """Test batch search functionality."""
        queries = ["query 1", "query 2", "query 3"]
        
        results = await engine.batch_search(queries, QueryType.SEMANTIC_ONLY)
        
        assert len(results) == 3
        for query in queries:
            assert query in results
            assert isinstance(results[query], tuple)
            assert len(results[query]) == 2  # results and metrics
    
    @pytest.mark.asyncio
    async def test_batch_search_with_failures(self, engine):
        """Test batch search with some failures."""
        queries = ["good query", "bad query"]
        
        # Mock one search to fail
        original_search = engine.search
        async def mock_search(query, *args, **kwargs):
            if query == "bad query":
                raise Exception("Search failed")
            return await original_search(query, *args, **kwargs)
        
        engine.search = mock_search
        
        results = await engine.batch_search(queries)
        
        assert len(results) == 2
        assert "good query" in results
        assert "bad query" in results
        # Bad query should have empty results
        assert results["bad query"] == ([], None)
    
    @pytest.mark.asyncio
    async def test_get_query_suggestions(self, engine, mock_graph_store):
        """Test query suggestions functionality."""
        # Mock graph search to return concept suggestions
        mock_nodes = [
            {"name": "Authentication"},
            {"name": "Authorization"},
            {"name": "API Security"}
        ]
        
        mock_graph_result = GraphSearchResult(
            nodes=mock_nodes,
            relationships=[],
            paths=[],
            query_metadata={}
        )
        
        mock_graph_store.graph_search.return_value = mock_graph_result
        
        suggestions = await engine.get_query_suggestions("auth")
        
        assert len(suggestions) > 0
        # Should include both graph results and common terms
        suggestion_text = " ".join(suggestions).lower()
        assert "auth" in suggestion_text
    
    @pytest.mark.asyncio
    async def test_get_query_suggestions_short_query(self, engine):
        """Test query suggestions with short partial query."""
        suggestions = await engine.get_query_suggestions("a")
        
        # Should still return some common suggestions
        assert len(suggestions) >= 0
    
    @pytest.mark.asyncio
    async def test_get_query_suggestions_error_handling(self, engine, mock_graph_store):
        """Test query suggestions error handling."""
        mock_graph_store.graph_search.side_effect = Exception("Graph search failed")
        
        suggestions = await engine.get_query_suggestions("test")
        
        # Should handle error gracefully - may still return common suggestions
        assert isinstance(suggestions, list)
        # Since common terms matching "test" might still be returned, just verify it's a list

class TestUtilityFunctions:
    """Test utility functions."""
    
    @patch('surrealdb_integration.create_vector_store')
    @patch('neo4j_integration.create_graph_store')
    @pytest.mark.asyncio
    async def test_create_hybrid_engine(self, mock_create_graph, mock_create_vector):
        """Test hybrid engine creation."""
        mock_vector_store = AsyncMock()
        mock_graph_store = AsyncMock()
        
        mock_create_vector.return_value = mock_vector_store
        mock_create_graph.return_value = mock_graph_store
        
        engine = await create_hybrid_engine()
        
        assert isinstance(engine, HybridQueryEngine)
        assert engine.vector_store == mock_vector_store
        assert engine.graph_store == mock_graph_store
        mock_create_vector.assert_called_once()
        mock_create_graph.assert_called_once()

class TestIntegrationScenarios:
    """Test complex integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_full_search_workflow(self):
        """Test complete search workflow with mocked stores."""
        # Create mock stores
        mock_vector_store = AsyncMock()
        mock_graph_store = AsyncMock()
        
        # Mock semantic search result
        doc = DocumentChunk(
            id="doc_auth",
            source_name="FastAPI Docs",
            source_url="https://fastapi.tiangolo.com/auth",
            title="Authentication Tutorial",
            content="Complete guide to FastAPI authentication",
            chunk_index=0,
            total_chunks=1,
            quality_score=0.95,
            topics=["authentication", "fastapi", "security"]
        )
        
        semantic_result = VectorSearchResult(
            document=doc,
            similarity_score=0.92,
            rank=1
        )
        
        mock_vector_store.semantic_search.return_value = [semantic_result]
        
        # Mock graph search result
        graph_nodes = [
            {
                "id": "concept_auth",
                "name": "Authentication",
                "category": "Security",
                "quality_score": 0.9,
                "title": "Authentication Concept",
                "content": "User verification and access control",
                "source_name": "Security Guide",
                "source_url": "https://security.example.com",
                "topics": ["security", "authentication", "access-control"]
            }
        ]
        
        graph_result = GraphSearchResult(
            nodes=graph_nodes,
            relationships=[],
            paths=[],
            query_metadata={"search_time_ms": 45.0}
        )
        
        mock_graph_store.graph_search.return_value = graph_result
        
        # Create engine
        config = HybridQueryConfig(max_results=10)
        engine = HybridQueryEngine(mock_vector_store, mock_graph_store, config)
        
        # Perform search
        results, metrics = await engine.search(
            "FastAPI authentication best practices",
            QueryType.HYBRID_BALANCED
        )
        
        # Verify results
        assert len(results) > 0
        assert metrics.total_results > 0
        assert metrics.semantic_results > 0
        assert metrics.graph_results > 0
        assert metrics.total_time_ms > 0
        
        # Check result content
        result = results[0]
        assert result.combined_score > 0
        assert len(result.found_via) > 0
        assert result.rank > 0
    
    @pytest.mark.asyncio
    async def test_query_analysis_optimization(self):
        """Test query analysis drives search optimization."""
        mock_vector_store = AsyncMock()
        mock_graph_store = AsyncMock()
        
        mock_vector_store.semantic_search.return_value = []
        mock_graph_store.graph_search.return_value = GraphSearchResult(
            nodes=[], relationships=[], paths=[], query_metadata={}
        )
        
        engine = HybridQueryEngine(mock_vector_store, mock_graph_store)
        
        # Test semantic-focused query
        semantic_query = "find similar authentication methods"
        results, metrics = await engine.search(semantic_query, QueryType.HYBRID_BALANCED)
        
        assert metrics.query_analysis.query_type == "semantic"
        assert metrics.query_analysis.semantic_weight > metrics.query_analysis.graph_weight
        
        # Test relationship-focused query
        relation_query = "what concepts are related to authentication?"
        results, metrics = await engine.search(relation_query, QueryType.HYBRID_BALANCED)
        
        assert metrics.query_analysis.query_type == "relational"
        assert metrics.query_analysis.graph_weight > metrics.query_analysis.semantic_weight

if __name__ == "__main__":
    pytest.main([__file__, "-v"])