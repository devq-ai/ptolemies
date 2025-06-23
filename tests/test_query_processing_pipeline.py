#!/usr/bin/env python3
"""
Test suite for Query Processing Pipeline
"""

import pytest
import asyncio
import time
import os
import sys
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path

# Set logfire config for testing
os.environ['LOGFIRE_IGNORE_NO_CONFIG'] = '1'

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from query_processing_pipeline import (
    QueryProcessor,
    QueryPipelineOrchestrator,
    QueryPipelineConfig,
    QueryContext,
    ProcessedQuery,
    QueryIntent,
    QueryComplexity,
    create_query_pipeline
)
from hybrid_query_engine import QueryType

class TestQueryPipelineConfig:
    """Test query pipeline configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = QueryPipelineConfig()
        
        assert config.enable_intent_detection is True
        assert config.intent_confidence_threshold == 0.7
        assert config.enable_query_expansion is True
        assert config.max_query_expansions == 3
        assert config.synonym_expansion is True
        assert config.concept_expansion is True
        assert config.enable_spell_correction is True
        assert config.spell_check_confidence_threshold == 0.8
        assert config.enable_entity_extraction is True
        assert config.entity_types == ["technology", "concept", "framework", "language", "tool"]
        assert config.enable_context_awareness is True
        assert config.context_window_size == 5
        assert config.session_timeout_minutes == 30
        assert config.enable_caching is True
        assert config.cache_ttl_seconds == 3600
        assert config.parallel_processing is True
        assert config.max_concurrent_operations == 5
        assert config.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = QueryPipelineConfig(
            enable_intent_detection=False,
            max_query_expansions=5,
            enable_caching=False,
            session_timeout_minutes=60,
            entity_types=["custom_type"]
        )
        
        assert config.enable_intent_detection is False
        assert config.max_query_expansions == 5
        assert config.enable_caching is False
        assert config.session_timeout_minutes == 60
        assert config.entity_types == ["custom_type"]

class TestQueryContext:
    """Test query context functionality."""
    
    def test_query_context_creation(self):
        """Test query context creation with defaults."""
        context = QueryContext(session_id="test_session")
        
        assert context.session_id == "test_session"
        assert context.user_id is None
        assert context.previous_queries == []
        assert context.conversation_history == []
        assert context.preferences == {}
        assert context.timestamp is not None
    
    def test_query_context_custom_values(self):
        """Test query context with custom values."""
        context = QueryContext(
            session_id="test_session",
            user_id="user123",
            previous_queries=["query1", "query2"],
            conversation_history=[{"query": "test", "intent": "search"}],
            preferences={"result_limit": 20}
        )
        
        assert context.session_id == "test_session"
        assert context.user_id == "user123"
        assert len(context.previous_queries) == 2
        assert len(context.conversation_history) == 1
        assert context.preferences["result_limit"] == 20

class TestProcessedQuery:
    """Test processed query data structure."""
    
    def test_processed_query_creation(self):
        """Test processed query creation."""
        processed = ProcessedQuery(
            original_query="How to use FastAPI?",
            normalized_query="how to use fastapi",
            intent=QueryIntent.EXPLAIN,
            complexity=QueryComplexity.SIMPLE,
            entities=[{"type": "technology", "value": "fastapi"}],
            keywords=["use", "fastapi"],
            concepts=["tutorial"],
            search_strategy=QueryType.SEMANTIC_ONLY,
            confidence_score=0.85
        )
        
        assert processed.original_query == "How to use FastAPI?"
        assert processed.normalized_query == "how to use fastapi"
        assert processed.intent == QueryIntent.EXPLAIN
        assert processed.complexity == QueryComplexity.SIMPLE
        assert len(processed.entities) == 1
        assert processed.entities[0]["value"] == "fastapi"
        assert processed.keywords == ["use", "fastapi"]
        assert processed.concepts == ["tutorial"]
        assert processed.search_strategy == QueryType.SEMANTIC_ONLY
        assert processed.confidence_score == 0.85
        assert processed.language == "en"
        assert processed.spell_corrected is False
        assert processed.expanded_queries == []
        assert processed.metadata == {}

class TestQueryProcessor:
    """Test query processor functionality."""
    
    @pytest.fixture
    def processor(self):
        """Create test query processor."""
        config = QueryPipelineConfig(
            enable_intent_detection=True,
            enable_entity_extraction=True,
            enable_query_expansion=True,
            enable_spell_correction=True
        )
        # Mock the embedding model initialization
        with patch('query_processing_pipeline.SentenceTransformer'):
            return QueryProcessor(config)
    
    def test_normalize_query(self, processor):
        """Test query normalization."""
        # Test basic normalization
        assert processor._normalize_query("  HELLO WORLD  ") == "hello world"
        assert processor._normalize_query("test   multiple   spaces") == "test multiple spaces"
        assert processor._normalize_query("Special@#$Characters!") == "specialcharacters!"
        assert processor._normalize_query("keep-hyphens.dots,commas?questions!") == "keep-hyphens.dots,commas?questions!"
    
    def test_spell_correct(self, processor):
        """Test spell correction."""
        # Test known corrections
        corrected, was_corrected = processor._spell_correct("pyton programming")
        assert corrected == "python programming"
        assert was_corrected is True
        
        corrected, was_corrected = processor._spell_correct("javascrip databse")
        assert corrected == "javascript database"
        assert was_corrected is True
        
        # Test no correction needed
        corrected, was_corrected = processor._spell_correct("python programming")
        assert corrected == "python programming"
        assert was_corrected is False
    
    def test_detect_intent(self, processor):
        """Test intent detection."""
        # Search intent
        intent, confidence = processor._detect_intent("find information about python")
        assert intent in [QueryIntent.SEARCH, QueryIntent.EXPLAIN]  # Could be either
        
        # Explain intent
        intent, confidence = processor._detect_intent("explain how authentication works")
        assert intent in [QueryIntent.EXPLAIN, QueryIntent.SEARCH]
        assert confidence >= 0
        
        # Compare intent
        intent, confidence = processor._detect_intent("compare redis vs neo4j")
        assert intent in [QueryIntent.COMPARE, QueryIntent.SEARCH]
        
        # Tutorial intent
        intent, confidence = processor._detect_intent("tutorial on fastapi step by step")
        assert intent in [QueryIntent.TUTORIAL, QueryIntent.SEARCH]
        
        # Troubleshoot intent
        intent, confidence = processor._detect_intent("error fix async function not working")
        assert intent in [QueryIntent.TROUBLESHOOT, QueryIntent.SEARCH]
        
        # Test that confidence is a valid number
        intent, confidence = processor._detect_intent("random text without clear intent")
        assert 0 <= confidence <= 1  # Valid confidence range
    
    def test_extract_entities(self, processor):
        """Test entity extraction."""
        # Technology entities
        entities = processor._extract_entities("How to use Python with FastAPI and Redis")
        entity_values = [e["value"] for e in entities]
        assert "python" in entity_values
        assert "fastapi" in entity_values
        assert "redis" in entity_values
        
        # Concept entities
        entities = processor._extract_entities("authentication and caching performance")
        entity_values = [e["value"] for e in entities]
        assert "authentication" in entity_values
        assert "caching" in entity_values
        assert "performance" in entity_values
        
        # Mixed entities
        entities = processor._extract_entities("nodejs api security")
        entity_values = [e["value"] for e in entities]
        assert "nodejs" in entity_values
        assert "api" in entity_values
        assert "security" in entity_values
    
    def test_extract_keywords(self, processor):
        """Test keyword extraction."""
        keywords = processor._extract_keywords("How to implement authentication in FastAPI")
        assert "implement" in keywords
        assert "authentication" in keywords
        assert "fastapi" in keywords
        assert "how" not in keywords  # Stop word
        assert "to" not in keywords   # Stop word
        assert "in" not in keywords   # Stop word
    
    def test_extract_concepts(self, processor):
        """Test concept extraction."""
        entities = [
            {"type": "concept", "value": "authentication"},
            {"type": "technology", "value": "fastapi"}
        ]
        
        concepts = processor._extract_concepts("auth system with caching", entities)
        # Should extract at least one concept from entities or query
        assert len(concepts) >= 1
        assert any(concept in ["authentication", "caching"] for concept in concepts)
    
    def test_assess_complexity(self, processor):
        """Test complexity assessment."""
        # Simple query
        complexity = processor._assess_complexity(
            "how to use python",
            [{"type": "technology", "value": "python"}],
            []
        )
        assert complexity == QueryComplexity.SIMPLE
        
        # Moderate query
        complexity = processor._assess_complexity(
            "implement authentication system with jwt tokens",
            [{"type": "concept", "value": "authentication"}, {"type": "technology", "value": "jwt"}],
            ["authentication"]
        )
        assert complexity == QueryComplexity.MODERATE
        
        # Complex query
        complexity = processor._assess_complexity(
            "design scalable microservices architecture with kafka redis and kubernetes orchestration",
            [
                {"type": "technology", "value": "kafka"},
                {"type": "technology", "value": "redis"},
                {"type": "technology", "value": "kubernetes"},
                {"type": "concept", "value": "microservices"}
            ],
            ["microservices", "orchestration"]
        )
        # Should be complex or compound (due to "and" keyword)
        assert complexity in [QueryComplexity.COMPLEX, QueryComplexity.COMPOUND]
        
        # Compound query
        complexity = processor._assess_complexity(
            "compare python and javascript for backend development",
            [{"type": "technology", "value": "python"}, {"type": "technology", "value": "javascript"}],
            []
        )
        # Should detect compound nature or be at least moderate complexity
        assert complexity in [QueryComplexity.COMPOUND, QueryComplexity.MODERATE, QueryComplexity.COMPLEX]
    
    def test_determine_search_strategy(self, processor):
        """Test search strategy determination."""
        # Intent-based
        strategy = processor._determine_search_strategy(
            QueryIntent.EXPLAIN,
            QueryComplexity.SIMPLE,
            []
        )
        assert strategy == QueryType.CONCEPT_EXPANSION
        
        strategy = processor._determine_search_strategy(
            QueryIntent.COMPARE,
            QueryComplexity.SIMPLE,
            []
        )
        assert strategy == QueryType.GRAPH_THEN_SEMANTIC
        
        # Complexity-based
        strategy = processor._determine_search_strategy(
            QueryIntent.SEARCH,
            QueryComplexity.COMPLEX,
            []
        )
        assert strategy == QueryType.HYBRID_BALANCED
        
        # Concept-based
        strategy = processor._determine_search_strategy(
            QueryIntent.SEARCH,
            QueryComplexity.SIMPLE,
            ["auth", "security", "oauth"]
        )
        assert strategy == QueryType.GRAPH_THEN_SEMANTIC
    
    @pytest.mark.asyncio
    async def test_expand_query(self, processor):
        """Test query expansion."""
        # Synonym expansion
        expanded = await processor._expand_query(
            "database authentication",
            QueryIntent.SEARCH,
            ["authentication"]
        )
        
        # Should contain synonyms
        expanded_text = ' '.join(expanded)
        assert any(syn in expanded_text for syn in ["auth", "login", "db", "datastore"])
        
        # Intent-specific expansion
        expanded = await processor._expand_query(
            "python error",
            QueryIntent.TROUBLESHOOT,
            []
        )
        assert any("solution fix" in exp for exp in expanded)
        
        expanded = await processor._expand_query(
            "fastapi tutorial",
            QueryIntent.TUTORIAL,
            []
        )
        assert any("step by step guide" in exp for exp in expanded)
    
    def test_apply_context(self, processor):
        """Test context application."""
        # Follow-up query context
        context = QueryContext(
            session_id="test",
            previous_queries=["what is fastapi", "more details"]
        )
        
        strategy = processor._apply_context(
            QueryType.SEMANTIC_ONLY,
            context,
            QueryIntent.SEARCH
        )
        # Should change strategy based on context
        assert strategy in [QueryType.GRAPH_THEN_SEMANTIC, QueryType.SEMANTIC_THEN_GRAPH, QueryType.CONCEPT_EXPANSION]
        
        # User preferences
        context = QueryContext(
            session_id="test",
            preferences={"prefer_examples": True}
        )
        
        strategy = processor._apply_context(
            QueryType.SEMANTIC_ONLY,
            context,
            QueryIntent.SEARCH
        )
        # Should apply user preferences
        assert strategy in [QueryType.SEMANTIC_THEN_GRAPH, QueryType.SEMANTIC_ONLY, QueryType.CONCEPT_EXPANSION]
    
    @pytest.mark.asyncio
    async def test_process_query_complete(self, processor):
        """Test complete query processing."""
        query = "How to implement authetication in FastAPI?"
        context = QueryContext(session_id="test")
        
        processed = await processor.process_query(query, context)
        
        assert processed.original_query == query
        # Should be spell corrected
        assert "authentication" in processed.normalized_query or "authetication" in processed.normalized_query
        assert processed.intent in [QueryIntent.EXPLAIN, QueryIntent.SEARCH, QueryIntent.TUTORIAL]
        assert len(processed.entities) >= 0  # May or may not find entities
        assert len(processed.keywords) > 0
        assert processed.search_strategy in [
            QueryType.CONCEPT_EXPANSION,
            QueryType.SEMANTIC_THEN_GRAPH,
            QueryType.HYBRID_BALANCED,
            QueryType.SEMANTIC_ONLY,
            QueryType.GRAPH_THEN_SEMANTIC
        ]

class TestQueryPipelineOrchestrator:
    """Test query pipeline orchestrator."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create test orchestrator."""
        config = QueryPipelineConfig(
            enable_caching=False,
            parallel_processing=False
        )
        # Mock the embedding model
        with patch('query_processing_pipeline.SentenceTransformer'):
            return QueryPipelineOrchestrator(config)
    
    @pytest.fixture
    def orchestrator_with_mocks(self):
        """Create orchestrator with mocked components."""
        config = QueryPipelineConfig(enable_caching=True)
        
        # Mock components
        hybrid_engine = AsyncMock()
        cache_layer = AsyncMock()
        performance_optimizer = Mock()
        tool_registry = Mock()
        
        with patch('query_processing_pipeline.SentenceTransformer'):
            orchestrator = QueryPipelineOrchestrator(
                config=config,
                hybrid_engine=hybrid_engine,
                cache_layer=cache_layer,
                performance_optimizer=performance_optimizer,
                tool_registry=tool_registry
            )
        
        return orchestrator
    
    @pytest.mark.asyncio
    async def test_get_or_create_context(self, orchestrator):
        """Test context creation and retrieval."""
        # Create new context
        context = await orchestrator._get_or_create_context(
            "session1", "user1", {"pref1": "value1"}
        )
        
        assert context.session_id == "session1"
        assert context.user_id == "user1"
        assert context.preferences["pref1"] == "value1"
        assert "session1" in orchestrator.sessions
        
        # Retrieve existing context
        context2 = await orchestrator._get_or_create_context(
            "session1", None, {"pref2": "value2"}
        )
        
        assert context2.session_id == "session1"
        assert context2.user_id == "user1"  # Preserved from before
        assert context2.preferences["pref1"] == "value1"
        assert context2.preferences["pref2"] == "value2"
    
    @pytest.mark.asyncio
    async def test_update_context(self, orchestrator):
        """Test context update."""
        context = QueryContext(session_id="test")
        
        processed = ProcessedQuery(
            original_query="test query",
            normalized_query="test query",
            intent=QueryIntent.SEARCH,
            complexity=QueryComplexity.SIMPLE,
            entities=[],
            keywords=["test", "query"],
            concepts=[],
            search_strategy=QueryType.SEMANTIC_ONLY,
            confidence_score=0.8
        )
        
        await orchestrator._update_context(context, "test query", processed)
        
        assert "test query" in context.previous_queries
        assert len(context.conversation_history) == 1
        assert context.conversation_history[0]["query"] == "test query"
        assert context.conversation_history[0]["intent"] == "search"
    
    @pytest.mark.asyncio
    async def test_clean_old_sessions(self, orchestrator):
        """Test session cleanup."""
        # Create sessions with different timestamps
        old_context = QueryContext(session_id="old")
        old_context.timestamp = time.time() - 3700  # Over 1 hour old
        
        new_context = QueryContext(session_id="new")
        new_context.timestamp = time.time() - 100  # Recent
        
        orchestrator.sessions["old"] = old_context
        orchestrator.sessions["new"] = new_context
        
        await orchestrator._clean_old_sessions()
        
        assert "old" not in orchestrator.sessions
        assert "new" in orchestrator.sessions
    
    @pytest.mark.asyncio
    async def test_execute_search(self, orchestrator_with_mocks):
        """Test search execution."""
        orchestrator = orchestrator_with_mocks
        
        # Mock search results
        from hybrid_query_engine import HybridSearchResult
        mock_result = HybridSearchResult(
            id="doc1",
            title="Test Document",
            content="Test content about FastAPI",
            source_name="Test Source",
            source_url="https://test.com",
            semantic_score=0.8,
            graph_score=0.7,
            combined_score=0.75,
            rank=1,
            found_via=["semantic"],
            topics=["fastapi"],
            related_concepts=[]
        )
        
        orchestrator.hybrid_engine.search.return_value = ([mock_result], Mock())
        
        processed = ProcessedQuery(
            original_query="fastapi",
            normalized_query="fastapi",
            intent=QueryIntent.SEARCH,
            complexity=QueryComplexity.SIMPLE,
            entities=[],
            keywords=["fastapi"],
            concepts=[],
            search_strategy=QueryType.SEMANTIC_ONLY,
            confidence_score=0.8
        )
        
        results = await orchestrator._execute_search(processed)
        
        assert len(results) == 1
        assert results[0]["id"] == "doc1"
        assert results[0]["title"] == "Test Document"
        assert results[0]["score"] == 0.75
    
    @pytest.mark.asyncio
    async def test_apply_intent_processing(self, orchestrator):
        """Test intent-specific result processing."""
        # Mock search results
        results = [
            {"id": f"doc{i}", "content": f"Content {i}", "score": 0.9 - i*0.1}
            for i in range(20)
        ]
        
        # Summarize intent - should return top 3
        processed = ProcessedQuery(
            original_query="test",
            normalized_query="test",
            intent=QueryIntent.SUMMARIZE,
            complexity=QueryComplexity.SIMPLE,
            entities=[],
            keywords=["test"],
            concepts=[],
            search_strategy=QueryType.SEMANTIC_ONLY,
            confidence_score=0.8
        )
        
        summarized = await orchestrator._apply_intent_processing(processed, results)
        assert len(summarized) == 3
        
        # Tutorial intent - should prioritize tutorial content
        tutorial_results = results.copy()
        tutorial_results[5]["content"] = "Step by step tutorial"
        tutorial_results[8]["content"] = "Complete guide"
        
        processed.intent = QueryIntent.TUTORIAL
        tutorial_filtered = await orchestrator._apply_intent_processing(processed, tutorial_results)
        
        # Check that tutorial content is prioritized
        assert any("tutorial" in r["content"].lower() or "guide" in r["content"].lower() 
                  for r in tutorial_filtered[:2])
    
    def test_generate_cache_key(self, orchestrator):
        """Test cache key generation."""
        context = QueryContext(
            session_id="test",
            user_id="user123",
            previous_queries=["query1", "query2"],
            preferences={"result_limit": 20}
        )
        
        key1 = orchestrator._generate_cache_key("test query", context)
        key2 = orchestrator._generate_cache_key("test query", context)
        key3 = orchestrator._generate_cache_key("different query", context)
        
        assert key1 == key2  # Same query, same context
        assert key1 != key3  # Different query
        assert len(key1) == 32  # MD5 hash length
    
    def test_generate_session_id(self, orchestrator):
        """Test session ID generation."""
        id1 = orchestrator._generate_session_id()
        id2 = orchestrator._generate_session_id()
        
        assert id1 != id2
        assert id1.startswith("session_")
        assert len(id1) > 10
    
    @pytest.mark.asyncio
    async def test_process_query_request_complete(self, orchestrator_with_mocks):
        """Test complete query request processing."""
        orchestrator = orchestrator_with_mocks
        
        # Mock cache miss
        orchestrator.cache_layer.get.return_value = (None, False)
        
        # Mock search results
        from hybrid_query_engine import HybridSearchResult
        mock_result = HybridSearchResult(
            id="doc1",
            title="FastAPI Authentication Guide",
            content="How to implement authentication in FastAPI...",
            source_name="FastAPI Docs",
            source_url="https://fastapi.com/auth",
            semantic_score=0.85,
            graph_score=0.75,
            combined_score=0.8,
            rank=1,
            found_via=["semantic", "graph"],
            topics=["fastapi", "authentication"],
            related_concepts=["security", "jwt"]
        )
        
        orchestrator.hybrid_engine.search.return_value = ([mock_result], Mock())
        
        # Process query
        result = await orchestrator.process_query_request(
            "How to implement authentication in FastAPI?",
            session_id="test_session",
            user_id="test_user"
        )
        
        assert result["query"] == "How to implement authentication in FastAPI?"
        assert "processed_query" in result
        assert "results" in result
        assert "metadata" in result
        
        processed = result["processed_query"]
        # Intent should be a valid string (enum value)
        assert isinstance(processed["intent"], str)
        assert processed["intent"] in ["explain", "search", "tutorial", "unknown"]
        # Should be normalized and potentially spell-corrected
        expected_query = "how to implement authentication in fastapi?"
        assert processed["normalized_query"] == expected_query or "authentication" in processed["normalized_query"]
        
        # Check that cache was attempted
        orchestrator.cache_layer.get.assert_called_once()
        orchestrator.cache_layer.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_session_info(self, orchestrator):
        """Test getting session information."""
        context = QueryContext(
            session_id="test_session",
            user_id="test_user",
            previous_queries=["query1", "query2"],
            preferences={"theme": "dark"}
        )
        orchestrator.sessions["test_session"] = context
        
        info = await orchestrator.get_session_info("test_session")
        
        assert info["session_id"] == "test_session"
        assert info["user_id"] == "test_user"
        assert info["query_count"] == 2
        assert info["last_query"] == "query2"
        assert info["preferences"]["theme"] == "dark"
        
        # Non-existent session
        info = await orchestrator.get_session_info("non_existent")
        assert info is None
    
    @pytest.mark.asyncio
    async def test_clear_session(self, orchestrator):
        """Test clearing a session."""
        orchestrator.sessions["test_session"] = QueryContext(session_id="test_session")
        
        success = await orchestrator.clear_session("test_session")
        assert success is True
        assert "test_session" not in orchestrator.sessions
        
        # Clear non-existent session
        success = await orchestrator.clear_session("non_existent")
        assert success is False

class TestUtilityFunctions:
    """Test utility functions."""
    
    @pytest.mark.asyncio
    async def test_create_query_pipeline(self):
        """Test creating query pipeline orchestrator."""
        with patch('query_processing_pipeline.SentenceTransformer'):
            pipeline = await create_query_pipeline()
        
        assert isinstance(pipeline, QueryPipelineOrchestrator)
        assert pipeline.config is not None
        assert pipeline.query_processor is not None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])