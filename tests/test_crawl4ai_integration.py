#!/usr/bin/env python3
"""
Test suite for Ptolemies Crawl4AI Integration
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import sys
from pathlib import Path
import os

# Set logfire config for testing
os.environ['LOGFIRE_IGNORE_NO_CONFIG'] = '1'

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crawl4ai_integration import (
    PtolemiesCrawler,
    CrawlConfig,
    DocumentMetrics
)

class TestCrawlConfig:
    """Test CrawlConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = CrawlConfig()
        
        assert config.max_depth == 2
        assert config.max_pages == 250
        assert config.delay_ms == 1000
        assert config.respect_robots_txt is True
        assert config.user_agent == "Ptolemies Knowledge Crawler/1.0"
        assert config.timeout == 30
        assert config.concurrent_requests == 5
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = CrawlConfig(
            max_depth=3,
            max_pages=100,
            delay_ms=500,
            user_agent="Custom Agent"
        )
        
        assert config.max_depth == 3
        assert config.max_pages == 100
        assert config.delay_ms == 500
        assert config.user_agent == "Custom Agent"

class TestDocumentMetrics:
    """Test DocumentMetrics dataclass."""
    
    def test_default_metrics(self):
        """Test default metrics values."""
        metrics = DocumentMetrics()
        
        assert metrics.total_pages_crawled == 0
        assert metrics.total_pages_stored == 0
        assert metrics.total_processing_time == 0.0
        assert metrics.success_rate == 0.0
        assert metrics.average_quality_score == 0.0

@pytest.fixture
def crawler_config():
    """Fixture for test crawler configuration."""
    return CrawlConfig(
        max_depth=1,
        max_pages=5,
        delay_ms=100,
        timeout=10
    )

@pytest.fixture
def mock_crawler(crawler_config):
    """Fixture for mocked crawler."""
    with patch('crawl4ai_integration.httpx.AsyncClient'), \
         patch('crawl4ai_integration.openai.AsyncOpenAI'):
        return PtolemiesCrawler(crawler_config)

class TestPtolemiesCrawler:
    """Test PtolemiesCrawler class."""
    
    def test_crawler_initialization(self, crawler_config):
        """Test crawler initialization."""
        with patch('crawl4ai_integration.httpx.AsyncClient'), \
             patch('crawl4ai_integration.openai.AsyncOpenAI'):
            crawler = PtolemiesCrawler(crawler_config)
            
            assert crawler.config == crawler_config
            assert isinstance(crawler.metrics, DocumentMetrics)
            assert crawler.visited_urls == set()
            assert crawler.crawl_cache == {}
    
    def test_should_crawl_link(self, mock_crawler):
        """Test link crawling decision logic."""
        base_url = "https://docs.example.com/guide"
        
        # Valid documentation links
        assert mock_crawler._should_crawl_link(
            "https://docs.example.com/guide/tutorial", base_url
        ) is True
        
        assert mock_crawler._should_crawl_link(
            "https://docs.example.com/api/reference", base_url
        ) is True
        
        # Invalid links (different domain)
        assert mock_crawler._should_crawl_link(
            "https://other-site.com/docs", base_url
        ) is False
        
        # Invalid links (skip patterns)
        assert mock_crawler._should_crawl_link(
            "https://docs.example.com/search?q=test", base_url
        ) is False
        
        assert mock_crawler._should_crawl_link(
            "https://docs.example.com/download/file.pdf", base_url
        ) is False
    
    def test_is_valid_documentation_link(self, mock_crawler):
        """Test documentation link validation."""
        # Valid documentation URLs
        valid_urls = [
            "https://example.com/docs/getting-started",
            "https://example.com/documentation/api",
            "https://example.com/guide/tutorial",
            "https://example.com/reference/functions",
            "https://example.com/manual/setup"
        ]
        
        for url in valid_urls:
            assert mock_crawler._is_valid_documentation_link(url) is True
        
        # Invalid URLs
        invalid_urls = [
            "https://example.com/blog/post",
            "https://example.com/about/company",
            "https://example.com/contact/support"
        ]
        
        for url in invalid_urls:
            assert mock_crawler._is_valid_documentation_link(url) is False
    
    def test_calculate_quality_score(self, mock_crawler):
        """Test content quality scoring."""
        # High quality content
        high_quality = {
            "content": " ".join(["word"] * 500) + " def function() example tutorial ```code```",
            "title": "Complete Python Tutorial Guide",
            "links": ["link1", "link2"]  # Few links relative to content
        }
        
        score = mock_crawler._calculate_quality_score(high_quality)
        assert score > 0.5
        
        # Low quality content
        low_quality = {
            "content": "short content",
            "title": "",
            "links": []
        }
        
        score = mock_crawler._calculate_quality_score(low_quality)
        assert score < 0.5
    
    def test_chunk_content(self, mock_crawler):
        """Test content chunking."""
        content = " ".join([f"word{i}" for i in range(2000)])
        chunks = mock_crawler._chunk_content(content, chunk_size=500)
        
        assert len(chunks) == 4  # 2000 words / 500 per chunk
        assert all(len(chunk.split()) <= 500 for chunk in chunks)
    
    @pytest.mark.asyncio
    async def test_extract_topics(self, mock_crawler):
        """Test topic extraction."""
        content = """
        This is a tutorial about API functions and database configuration.
        def example_function():
            return "hello"
        
        class ExampleClass:
            pass
        """
        
        topics = await mock_crawler._extract_topics(content)
        
        expected_topics = ["api", "function", "tutorial", "configuration", "def ", "class "]
        assert any(topic in topics for topic in expected_topics)
    
    @pytest.mark.asyncio
    async def test_get_crawl_metrics(self, mock_crawler):
        """Test metrics collection."""
        # Set some test metrics
        mock_crawler.metrics.total_pages_crawled = 10
        mock_crawler.metrics.total_pages_stored = 8
        mock_crawler.metrics.total_processing_time = 120.0  # 2 minutes
        mock_crawler.metrics.success_rate = 0.8
        
        metrics = await mock_crawler.get_crawl_metrics()
        
        assert metrics["volume_metrics"]["total_pages_crawled"] == 10
        assert metrics["volume_metrics"]["total_pages_stored"] == 8
        assert metrics["volume_metrics"]["total_processing_time"] == 2.0  # minutes
        assert metrics["volume_metrics"]["success_rate"] == 80.0  # percentage
        assert metrics["quality_metrics"]["content_filtering_effectiveness"] == 80.0

@pytest.mark.asyncio
async def test_crawler_integration():
    """Integration test for crawler functionality."""
    config = CrawlConfig(max_pages=1, delay_ms=100)
    
    with patch('crawl4ai_integration.httpx.AsyncClient') as mock_client, \
         patch('crawl4ai_integration.openai.AsyncOpenAI'):
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <head><title>Test Documentation</title></head>
            <body>
                <main>
                    <h1>API Documentation</h1>
                    <p>This is a comprehensive guide to our API functions.</p>
                    <pre><code>def example(): return "test"</code></pre>
                    <a href="/docs/advanced">Advanced Guide</a>
                </main>
            </body>
        </html>
        """
        mock_response.headers = {"content-type": "text/html"}
        mock_response.raise_for_status = Mock()
        
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value = mock_client_instance
        
        crawler = PtolemiesCrawler(config)
        
        try:
            # Test single page crawl
            page_data = await crawler._crawl_single_page("https://example.com/docs", 0)
            
            assert page_data is not None
            assert page_data["title"] == "Test Documentation"
            assert "API Documentation" in page_data["content"]
            assert page_data["url"] == "https://example.com/docs"
            assert page_data["depth"] == 0
            
        finally:
            await crawler.close()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])