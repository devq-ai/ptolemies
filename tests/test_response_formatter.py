#!/usr/bin/env python3
"""
Test suite for Response Formatter
"""

import pytest
import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# Set logfire config for testing
os.environ['LOGFIRE_IGNORE_NO_CONFIG'] = '1'

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from response_formatter import (
    ResponseFormatter,
    FormattingConfig,
    FormattedResponse,
    OutputFormat,
    ResponseStyle
)
from query_processing_pipeline import QueryIntent, QueryComplexity
from hybrid_query_engine import HybridSearchResult

# Mock classes for testing
class MockProcessedQuery:
    def __init__(self, intent=QueryIntent.SEARCH, entities=None, concepts=None):
        self.intent = intent
        self.entities = entities or [{"type": "technology", "value": "python"}]
        self.concepts = concepts or ["programming"]
        self.confidence_score = 0.85
        self.search_strategy = Mock()
        self.search_strategy.value = "semantic_only"

class MockHybridSearchResult:
    def __init__(self, title="Test Result", content="Test content about programming", score=0.8):
        self.id = "test_1"
        self.title = title
        self.content = content
        self.source_name = "Test Source"
        self.source_url = "https://test.com"
        self.combined_score = score
        self.semantic_score = score
        self.graph_score = 0.0
        self.rank = 1
        self.topics = ["programming", "python"]
        self.related_concepts = ["coding", "development"]
        self.found_via = ["semantic_search"]
        self.chunk_index = 0
        self.total_chunks = 1
        self.quality_score = score

class TestFormattingConfig:
    """Test formatting configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = FormattingConfig()
        
        assert config.default_format == OutputFormat.STRUCTURED
        assert config.max_results_per_section == 5
        assert config.include_metadata is True
        assert config.include_sources is True
        assert config.snippet_length == 200
        assert config.enable_syntax_highlighting is True
        assert config.include_confidence_scores is True
        assert config.language == "en"
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = FormattingConfig(
            default_format=OutputFormat.JSON,
            max_results_per_section=10,
            snippet_length=100,
            language="es"
        )
        
        assert config.default_format == OutputFormat.JSON
        assert config.max_results_per_section == 10
        assert config.snippet_length == 100
        assert config.language == "es"

class TestFormattedResponse:
    """Test formatted response data structure."""
    
    def test_formatted_response_creation(self):
        """Test formatted response creation."""
        response = FormattedResponse(
            formatted_content="Test content",
            format_type=OutputFormat.MARKDOWN,
            style=ResponseStyle.DETAILED,
            query="test query",
            intent="search",
            results_count=5,
            processing_time_ms=25.5,
            timestamp="2024-01-01 12:00:00"
        )
        
        assert response.formatted_content == "Test content"
        assert response.format_type == OutputFormat.MARKDOWN
        assert response.style == ResponseStyle.DETAILED
        assert response.query == "test query"
        assert response.intent == "search"
        assert response.results_count == 5
        assert response.processing_time_ms == 25.5
        assert isinstance(response.sections, list)
        assert isinstance(response.key_insights, list)
        assert isinstance(response.related_queries, list)
        assert isinstance(response.sources, list)

class TestResponseFormatter:
    """Test response formatter functionality."""
    
    @pytest.fixture
    def formatter(self):
        """Create test response formatter."""
        config = FormattingConfig(
            snippet_length=50,
            max_results_per_section=3
        )
        return ResponseFormatter(config)
    
    @pytest.fixture
    def sample_results(self):
        """Create sample search results."""
        return [
            MockHybridSearchResult(
                title="Python Programming Guide",
                content="Python is a high-level programming language known for its simplicity and readability. It's widely used in web development, data science, and automation.",
                score=0.9
            ),
            MockHybridSearchResult(
                title="FastAPI Framework",
                content="FastAPI is a modern web framework for building APIs with Python. It's fast, easy to use, and provides automatic API documentation.",
                score=0.85
            ),
            MockHybridSearchResult(
                title="Web Development with Python",
                content="Python offers several frameworks for web development including Django, Flask, and FastAPI. Each has its own strengths and use cases.",
                score=0.8
            )
        ]
    
    def test_determine_response_style(self, formatter):
        """Test response style determination."""
        # Test different intents
        assert formatter._determine_response_style(QueryIntent.SEARCH) == ResponseStyle.CONCISE
        assert formatter._determine_response_style(QueryIntent.EXPLAIN) == ResponseStyle.DETAILED
        assert formatter._determine_response_style(QueryIntent.COMPARE) == ResponseStyle.COMPARISON
        assert formatter._determine_response_style(QueryIntent.TUTORIAL) == ResponseStyle.TUTORIAL
        assert formatter._determine_response_style(QueryIntent.TROUBLESHOOT) == ResponseStyle.TROUBLESHOOTING
        assert formatter._determine_response_style(QueryIntent.SUMMARIZE) == ResponseStyle.SUMMARY
    
    def test_create_snippet(self, formatter):
        """Test snippet creation."""
        # Short content
        short_content = "This is short content."
        snippet = formatter._create_snippet(short_content)
        assert snippet == short_content
        
        # Long content with sentence boundary
        long_content = "This is a long piece of content. It has multiple sentences. We want to test snippet creation."
        snippet = formatter._create_snippet(long_content)
        assert len(snippet) <= formatter.config.snippet_length + 10  # Allow some flexibility
        assert snippet.endswith('.') or snippet.endswith('...')
        
        # Very long content without sentence boundary
        very_long = "A" * 200
        snippet = formatter._create_snippet(very_long)
        assert snippet.endswith("...")
    
    def test_group_by_topic(self, formatter, sample_results):
        """Test grouping results by topic."""
        grouped = formatter._group_by_topic(sample_results)
        
        # Should have groups for different topics
        assert isinstance(grouped, dict)
        assert len(grouped) > 0
        
        # Each group should contain results
        for topic, results in grouped.items():
            assert isinstance(results, list)
            assert len(results) > 0
            for result in results:
                assert isinstance(result, MockHybridSearchResult)
    
    def test_group_by_source(self, formatter, sample_results):
        """Test grouping results by source."""
        grouped = formatter._group_by_source(sample_results)
        
        # Should have groups for different sources
        assert isinstance(grouped, dict)
        assert len(grouped) > 0
        
        # All results should be from "Test Source"
        assert "Test Source" in grouped
        assert len(grouped["Test Source"]) == len(sample_results)
    
    def test_generate_summary(self, formatter, sample_results):
        """Test summary generation."""
        processed_query = MockProcessedQuery(intent=QueryIntent.SEARCH)
        summary = formatter._generate_summary(processed_query, sample_results)
        
        assert isinstance(summary, str)
        assert "3 relevant results" in summary
        assert "average relevance score" in summary
        
        # Test with no results
        empty_summary = formatter._generate_summary(processed_query, [])
        assert "No relevant information found" in empty_summary
    
    def test_extract_key_insights(self, formatter, sample_results):
        """Test key insights extraction."""
        insights = formatter._extract_key_insights(sample_results, QueryIntent.SEARCH)
        
        assert isinstance(insights, list)
        assert len(insights) > 0
        assert len(insights) <= 5  # Should limit to 5 insights
        
        # Should mention most relevant source
        insights_text = " ".join(insights)
        assert "Test Source" in insights_text
    
    def test_generate_related_queries(self, formatter):
        """Test related query generation."""
        processed_query = MockProcessedQuery(
            intent=QueryIntent.EXPLAIN,
            entities=[{"type": "technology", "value": "python"}],
            concepts=["programming"]
        )
        
        related = formatter._generate_related_queries(processed_query)
        
        assert isinstance(related, list)
        assert len(related) <= 5  # Should limit to 5 suggestions
        
        # Should include entity-based suggestions
        related_text = " ".join(related)
        assert "python" in related_text.lower()
    
    def test_extract_source_info(self, formatter, sample_results):
        """Test source information extraction."""
        sources = formatter._extract_source_info(sample_results)
        
        assert isinstance(sources, list)
        assert len(sources) > 0
        
        # Check source structure
        for source in sources:
            assert "name" in source
            assert "url" in source
            assert "relevance" in source
            assert isinstance(source["relevance"], (int, float))
    
    @pytest.mark.asyncio
    async def test_format_search_response(self, formatter, sample_results):
        """Test search response formatting."""
        processed_query = MockProcessedQuery(intent=QueryIntent.SEARCH)
        
        sections = await formatter._format_search_response("test query", processed_query, sample_results)
        
        assert isinstance(sections, list)
        assert len(sections) > 0
        
        # Check section structure
        for section in sections:
            assert "title" in section
            assert "type" in section
            if section["type"] == "results":
                assert "results" in section
                for result in section["results"]:
                    assert "title" in result
                    assert "snippet" in result
                    assert "source" in result
    
    @pytest.mark.asyncio
    async def test_format_search_response_empty(self, formatter):
        """Test search response formatting with no results."""
        processed_query = MockProcessedQuery(intent=QueryIntent.SEARCH)
        
        sections = await formatter._format_search_response("test query", processed_query, [])
        
        assert isinstance(sections, list)
        assert len(sections) == 1
        assert sections[0]["type"] == "message"
        assert "No Results Found" in sections[0]["title"]
    
    @pytest.mark.asyncio
    async def test_format_explanation_response(self, formatter, sample_results):
        """Test explanation response formatting."""
        processed_query = MockProcessedQuery(intent=QueryIntent.EXPLAIN)
        
        sections = await formatter._format_explanation_response("explain python", processed_query, sample_results)
        
        assert isinstance(sections, list)
        assert len(sections) > 0
        
        # Should have overview section
        overview_section = next((s for s in sections if s["title"] == "Overview"), None)
        assert overview_section is not None
        assert overview_section["type"] == "explanation"
    
    @pytest.mark.asyncio
    async def test_format_comparison_response(self, formatter, sample_results):
        """Test comparison response formatting."""
        processed_query = MockProcessedQuery(
            intent=QueryIntent.COMPARE,
            entities=[
                {"type": "technology", "value": "python"},
                {"type": "technology", "value": "javascript"}
            ]
        )
        
        sections = await formatter._format_comparison_response("compare python vs javascript", processed_query, sample_results)
        
        assert isinstance(sections, list)
        assert len(sections) > 0
        
        # Should have comparison section
        comparison_section = next((s for s in sections if "Comparison" in s["title"]), None)
        assert comparison_section is not None
    
    @pytest.mark.asyncio
    async def test_format_tutorial_response(self, formatter, sample_results):
        """Test tutorial response formatting."""
        processed_query = MockProcessedQuery(intent=QueryIntent.TUTORIAL)
        
        sections = await formatter._format_tutorial_response("python tutorial", processed_query, sample_results)
        
        assert isinstance(sections, list)
        assert len(sections) > 0
        
        # Should have introduction section
        intro_section = next((s for s in sections if s["title"] == "Introduction"), None)
        assert intro_section is not None
        assert intro_section["type"] == "intro"
    
    @pytest.mark.asyncio
    async def test_format_troubleshooting_response(self, formatter, sample_results):
        """Test troubleshooting response formatting."""
        processed_query = MockProcessedQuery(intent=QueryIntent.TROUBLESHOOT)
        
        sections = await formatter._format_troubleshooting_response("python error fix", processed_query, sample_results)
        
        assert isinstance(sections, list)
        assert len(sections) > 0
        
        # Should have problem analysis section
        analysis_section = next((s for s in sections if s["title"] == "Problem Analysis"), None)
        assert analysis_section is not None
        assert analysis_section["type"] == "analysis"
    
    @pytest.mark.asyncio
    async def test_apply_output_format_json(self, formatter):
        """Test JSON output formatting."""
        sections = [
            {"title": "Test Section", "content": "Test content", "type": "test"}
        ]
        
        result = await formatter._apply_output_format(sections, OutputFormat.JSON, ResponseStyle.DETAILED)
        
        # Should be valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["title"] == "Test Section"
    
    @pytest.mark.asyncio
    async def test_apply_output_format_markdown(self, formatter):
        """Test Markdown output formatting."""
        sections = [
            {"title": "Test Section", "content": "Test content", "type": "test"}
        ]
        
        result = await formatter._apply_output_format(sections, OutputFormat.MARKDOWN, ResponseStyle.DETAILED)
        
        assert isinstance(result, str)
        assert "## Test Section" in result
        assert "Test content" in result
    
    @pytest.mark.asyncio
    async def test_apply_output_format_text(self, formatter):
        """Test text output formatting."""
        sections = [
            {"title": "Test Section", "content": "Test content", "type": "test"}
        ]
        
        result = await formatter._apply_output_format(sections, OutputFormat.TEXT, ResponseStyle.DETAILED)
        
        assert isinstance(result, str)
        assert "TEST SECTION" in result
        assert "Test content" in result
    
    @pytest.mark.asyncio
    async def test_format_response_complete(self, formatter, sample_results):
        """Test complete response formatting."""
        query = "How to use Python for web development?"
        processed_query = MockProcessedQuery(intent=QueryIntent.EXPLAIN)
        
        response = await formatter.format_response(
            query, processed_query, sample_results, OutputFormat.MARKDOWN, ResponseStyle.DETAILED, 25.5
        )
        
        # Check response structure
        assert isinstance(response, FormattedResponse)
        assert response.query == query
        assert response.intent == "explain"
        assert response.results_count == len(sample_results)
        assert response.processing_time_ms == 25.5
        assert response.format_type == OutputFormat.MARKDOWN
        assert response.style == ResponseStyle.DETAILED
        
        # Check content
        assert isinstance(response.formatted_content, str)
        assert len(response.formatted_content) > 0
        
        # Check metadata
        assert isinstance(response.sections, list)
        assert isinstance(response.key_insights, list)
        assert isinstance(response.related_queries, list)
        assert isinstance(response.sources, list)
        assert isinstance(response.summary, str)
    
    @pytest.mark.asyncio
    async def test_format_response_no_results(self, formatter):
        """Test response formatting with no results."""
        query = "Nonexistent topic"
        processed_query = MockProcessedQuery(intent=QueryIntent.SEARCH)
        
        response = await formatter.format_response(
            query, processed_query, [], OutputFormat.TEXT
        )
        
        assert isinstance(response, FormattedResponse)
        assert response.results_count == 0
        assert len(response.sections) > 0  # Should have "no results" section
    
    def test_create_fallback_response(self, formatter, sample_results):
        """Test fallback response creation."""
        query = "test query"
        
        response = formatter._create_fallback_response(query, sample_results, OutputFormat.TEXT)
        
        assert isinstance(response, FormattedResponse)
        assert response.query == query
        assert response.results_count == len(sample_results)
        assert response.format_type == OutputFormat.TEXT
        assert "Results for query" in response.formatted_content
    
    @pytest.mark.asyncio
    async def test_format_response_error_handling(self, formatter, sample_results):
        """Test error handling in response formatting."""
        query = "test query"
        processed_query = MockProcessedQuery(intent=QueryIntent.SEARCH)
        
        # Mock an error in the formatting process
        with patch.object(formatter, '_format_search_response', side_effect=Exception("Test error")):
            response = await formatter.format_response(query, processed_query, sample_results)
            
            # Should return fallback response
            assert isinstance(response, FormattedResponse)
            assert "Results for query" in response.formatted_content

class TestOutputFormats:
    """Test different output formats."""
    
    @pytest.fixture
    def formatter(self):
        return ResponseFormatter()
    
    def test_format_as_markdown_with_results(self, formatter):
        """Test markdown formatting with results section."""
        sections = [
            {
                "title": "Search Results",
                "type": "results",
                "results": [
                    {
                        "title": "Test Result",
                        "snippet": "Test snippet",
                        "source": "Test Source",
                        "url": "https://test.com"
                    }
                ]
            }
        ]
        
        result = formatter._format_as_markdown(sections, ResponseStyle.DETAILED)
        
        assert "## Search Results" in result
        assert "### Test Result" in result
        assert "Test snippet" in result
        assert "**Source:** Test Source" in result
    
    def test_format_as_markdown_with_steps(self, formatter):
        """Test markdown formatting with steps section."""
        sections = [
            {
                "title": "Instructions",
                "type": "steps",
                "steps": ["Step 1: Do this", "Step 2: Do that"]
            }
        ]
        
        result = formatter._format_as_markdown(sections, ResponseStyle.TUTORIAL)
        
        assert "## Instructions" in result
        assert "1. Step 1: Do this" in result
        assert "2. Step 2: Do that" in result
    
    def test_format_as_text(self, formatter):
        """Test text formatting."""
        sections = [
            {"title": "Test Section", "content": "Test content", "type": "test"}
        ]
        
        result = formatter._format_as_text(sections, ResponseStyle.CONCISE)
        
        assert "TEST SECTION" in result
        assert "=" * len("TEST SECTION") in result
        assert "Test content" in result
    
    def test_format_as_structured(self, formatter):
        """Test structured formatting."""
        sections = [
            {
                "title": "Test Section",
                "type": "results", 
                "results": [{"title": "Test Result", "snippet": "Test snippet", "source": "Test Source"}]
            }
        ]
        
        result = formatter._format_as_structured(sections, ResponseStyle.DETAILED)
        
        assert "1. Test Section" in result
        assert "1. Test Result" in result
        assert "Test snippet" in result

class TestContentExtraction:
    """Test content extraction methods."""
    
    @pytest.fixture
    def formatter(self):
        return ResponseFormatter()
    
    @pytest.fixture
    def sample_results(self):
        return [
            MockHybridSearchResult(
                title="Python Tutorial",
                content="Python is easy to learn. Step 1: Install Python. Step 2: Write your first program. For example: print('Hello World')",
                score=0.9
            ),
            MockHybridSearchResult(
                title="Advanced Python",
                content="Advanced Python concepts include decorators, generators, and metaclasses. These are powerful features for experienced developers.",
                score=0.8
            )
        ]
    
    def test_create_overview(self, formatter, sample_results):
        """Test overview creation."""
        overview = formatter._create_overview(sample_results)
        
        assert isinstance(overview, str)
        assert len(overview) > 0
        assert "Python" in overview
    
    def test_extract_key_concepts(self, formatter, sample_results):
        """Test key concepts extraction."""
        concepts = formatter._extract_key_concepts(sample_results)
        
        assert isinstance(concepts, list)
        assert len(concepts) <= 10  # Should limit to 10
        
        # Should extract from topics and related_concepts
        all_concepts_text = " ".join(concepts)
        assert "programming" in all_concepts_text or "python" in all_concepts_text
    
    def test_create_detailed_explanation(self, formatter, sample_results):
        """Test detailed explanation creation."""
        explanation = formatter._create_detailed_explanation(sample_results)
        
        assert isinstance(explanation, str)
        assert len(explanation) > 0
        # Should include content from multiple results
        assert explanation.count("...") >= 1  # Should truncate long content

if __name__ == "__main__":
    # Run specific tests
    pytest.main([__file__, "-v"])