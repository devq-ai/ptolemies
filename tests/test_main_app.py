#!/usr/bin/env python3
"""
Test suite for Ptolemies FastAPI Application
"""

import pytest
import pytest_asyncio
import asyncio
import os
import sys
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
from fastapi.testclient import TestClient

# Set logfire config for testing
os.environ['LOGFIRE_IGNORE_NO_CONFIG'] = '1'

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from main import app, crawler_instance
from crawl4ai_integration import CrawlConfig

class TestFastAPIApplication:
    """Test FastAPI application endpoints."""
    
    @pytest.fixture
    def client(self):
        """Test client fixture."""
        return TestClient(app)
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert data["framework"] == "FastAPI + DevQ.ai stack"
        assert "services" in data
        assert "timestamp" in data
        
        # Check required services
        services = data["services"]
        assert "crawler" in services
        assert "logfire" in services
        assert "fastapi" in services
    
    def test_sources_endpoint(self, client):
        """Test documentation sources listing."""
        response = client.get("/sources")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "sources" in data
        assert "total_count" in data
        assert data["total_count"] > 0
        
        # Check source structure
        sources = data["sources"]
        for source in sources:
            assert "name" in source
            assert "url" in source
            assert "status" in source
    
    @pytest.mark.asyncio
    async def test_status_endpoint(self, client):
        """Test system status endpoint."""
        response = await client.get("/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["application"] == "running"
        assert data["version"] == "1.0.0"
        assert "services" in data
        assert "configuration" in data
        
        # Check configuration
        config = data["configuration"]
        assert "max_crawl_depth" in config
        assert "max_crawl_pages" in config
        assert "crawler_delay" in config
    
    @pytest.mark.asyncio
    async def test_crawl_endpoint_invalid_request(self, client):
        """Test crawl endpoint with invalid request."""
        # Missing required fields
        response = await client.post("/crawl", json={})
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_crawl_endpoint_valid_request(self, client):
        """Test crawl endpoint with valid request."""
        with patch('main.crawler_instance') as mock_crawler:
            # Mock successful crawl
            mock_crawler.crawl_documentation_source = AsyncMock(return_value={
                "success": True,
                "source_name": "Test Source",
                "pages_crawled": 5,
                "pages_stored": 4,
                "processing_time": 2.5
            })
            mock_crawler.config = CrawlConfig()
            
            request_data = {
                "source_name": "Test Source",
                "source_url": "https://example.com/docs",
                "max_pages": 5,
                "max_depth": 1
            }
            
            response = await client.post("/crawl", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert data["source_name"] == "Test Source"
            assert data["pages_crawled"] == 5
            assert data["pages_stored"] == 4
            assert "processing_time" in data
            assert "message" in data
    
    @pytest.mark.asyncio
    async def test_crawl_endpoint_crawler_unavailable(self, client):
        """Test crawl endpoint when crawler is unavailable."""
        with patch('main.crawler_instance', None):
            request_data = {
                "source_name": "Test Source",
                "source_url": "https://example.com/docs"
            }
            
            response = await client.post("/crawl", json=request_data)
            assert response.status_code == 503
    
    @pytest.mark.asyncio
    async def test_crawl_metrics_endpoint(self, client):
        """Test crawl metrics endpoint."""
        with patch('main.crawler_instance') as mock_crawler:
            mock_crawler.get_crawl_metrics = AsyncMock(return_value={
                "volume_metrics": {
                    "total_pages_crawled": 10,
                    "total_pages_stored": 8,
                    "success_rate": 80.0
                },
                "quality_metrics": {
                    "average_quality_score": 0.85
                }
            })
            
            response = await client.get("/crawl/metrics")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "volume_metrics" in data
            assert "quality_metrics" in data
    
    @pytest.mark.asyncio
    async def test_search_endpoint(self, client):
        """Test search endpoint (placeholder implementation)."""
        request_data = {
            "query": "test search",
            "limit": 5
        }
        
        response = await client.post("/search", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["query"] == "test search"
        assert "results" in data
        assert "total_results" in data
        assert "processing_time" in data
        
        # Check result structure
        results = data["results"]
        for result in results:
            assert "title" in result
            assert "content" in result
            assert "source" in result
    
    @pytest.mark.asyncio
    async def test_404_handler(self, client):
        """Test custom 404 handler."""
        response = await client.get("/nonexistent")
        
        assert response.status_code == 404
        data = response.json()
        
        assert data["error"] == "Not Found"
        assert "message" in data
        assert "path" in data
    
    @pytest.mark.asyncio
    async def test_cors_headers(self, client):
        """Test CORS middleware."""
        response = await client.options("/health")
        
        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers
    
    @pytest.mark.asyncio
    async def test_search_with_filters(self, client):
        """Test search endpoint with source filters."""
        request_data = {
            "query": "test search",
            "limit": 10,
            "source_filter": ["FastAPI", "Logfire"]
        }
        
        response = await client.post("/search", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["query"] == "test search"
        assert isinstance(data["results"], list)

class TestApplicationLifespan:
    """Test application lifespan management."""
    
    @pytest.mark.asyncio
    async def test_lifespan_startup_cleanup(self):
        """Test application startup and cleanup."""
        with patch('main.PtolemiesCrawler') as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler_class.return_value = mock_crawler
            
            # Import after patching to ensure the patch takes effect
            from main import lifespan
            
            async with lifespan(app):
                # During lifespan, crawler should be initialized
                mock_crawler_class.assert_called_once()
            
            # After lifespan, crawler should be closed
            mock_crawler.close.assert_called_once()

class TestRequestModels:
    """Test Pydantic request/response models."""
    
    def test_crawl_request_validation(self):
        """Test CrawlRequest model validation."""
        from main import CrawlRequest
        
        # Valid request
        request = CrawlRequest(
            source_name="Test",
            source_url="https://example.com",
            max_pages=10,
            max_depth=2
        )
        
        assert request.source_name == "Test"
        assert request.source_url == "https://example.com"
        assert request.max_pages == 10
        assert request.max_depth == 2
    
    def test_search_request_validation(self):
        """Test SearchRequest model validation."""
        from main import SearchRequest
        
        # Valid request with minimal fields
        request = SearchRequest(query="test")
        assert request.query == "test"
        assert request.limit == 10  # Default value
        assert request.source_filter is None  # Default value
        
        # Valid request with all fields
        request = SearchRequest(
            query="test query",
            limit=20,
            source_filter=["FastAPI", "Logfire"]
        )
        assert request.query == "test query"
        assert request.limit == 20
        assert request.source_filter == ["FastAPI", "Logfire"]
    
    def test_health_response_model(self):
        """Test HealthResponse model."""
        from main import HealthResponse
        import datetime
        
        response = HealthResponse(
            status="healthy",
            version="1.0.0",
            framework="FastAPI",
            services={"test": "ok"},
            timestamp=datetime.datetime.utcnow().isoformat()
        )
        
        assert response.status == "healthy"
        assert response.version == "1.0.0"
        assert response.services["test"] == "ok"

class TestEnvironmentConfiguration:
    """Test environment-based configuration."""
    
    def test_default_configuration(self):
        """Test default configuration values."""
        from main import app
        
        # App should be properly configured
        assert app.title == "Ptolemies - DevQ.AI Knowledge Base"
        assert app.version == "1.0.0"
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"
    
    @patch.dict(os.environ, {
        "CRAWLER_MAX_DEPTH": "3",
        "CRAWLER_MAX_PAGES": "100",
        "CRAWLER_DELAY_MS": "500"
    })
    def test_environment_overrides(self):
        """Test environment variable overrides."""
        # These would be used during crawler initialization
        assert os.getenv("CRAWLER_MAX_DEPTH") == "3"
        assert os.getenv("CRAWLER_MAX_PAGES") == "100"
        assert os.getenv("CRAWLER_DELAY_MS") == "500"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])