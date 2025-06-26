"""
PyTest configuration for Ptolemies test suite
Provides shared fixtures and test configuration
"""

import pytest
import asyncio
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock
from typing import Dict, List, Any

# Add src directory to Python path for imports
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Configure test environment
os.environ["TESTING"] = "true"
os.environ["LOGFIRE_SEND_TO_LOGFIRE"] = "false"
os.environ["LOGFIRE_IGNORE_NO_CONFIG"] = "1"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_env_file(tmp_path):
    """Create a temporary .env file for testing."""
    env_file = tmp_path / ".env"
    env_content = """
SURREALDB_URL=ws://localhost:8000/rpc
SURREALDB_USERNAME=root
SURREALDB_PASSWORD=root
SURREALDB_NAMESPACE=test_ptolemies
SURREALDB_DATABASE=test_knowledge
OPENAI_API_KEY=test_openai_key_12345
LOGFIRE_TOKEN=test_logfire_token
"""
    env_file.write_text(env_content.strip())
    return str(env_file)

@pytest.fixture
def mock_surrealdb_success():
    """Mock successful SurrealDB operations."""
    return Mock(returncode=0, stdout='{"success": true}', stderr="")

@pytest.fixture
def mock_surrealdb_failure():
    """Mock failed SurrealDB operations."""
    return Mock(returncode=1, stdout="", stderr="Connection failed")

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    client = AsyncMock()

    # Mock embedding response
    mock_embedding = [0.1] * 1536  # Standard embedding size
    mock_response = Mock()
    mock_response.data = [Mock(embedding=mock_embedding)]
    client.embeddings.create.return_value = mock_response

    return client

@pytest.fixture
def mock_http_client():
    """Mock HTTP client for testing."""
    client = AsyncMock()

    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = """
    <html>
        <head><title>Test Documentation</title></head>
        <body>
            <main>
                <h1>Test API Documentation</h1>
                <p>This is comprehensive documentation for testing purposes.</p>
                <p>It includes examples, configuration details, and usage instructions.</p>
            </main>
        </body>
    </html>
    """

    client.get.return_value = mock_response
    return client

@pytest.fixture
def sample_document_chunks():
    """Sample document chunks for testing."""
    return [
        {
            "source_name": "FastAPI",
            "source_url": "https://fastapi.tiangolo.com/",
            "title": "FastAPI Documentation",
            "content": "FastAPI is a modern, fast web framework for building APIs with Python.",
            "chunk_index": 0,
            "total_chunks": 2,
            "quality_score": 0.9,
            "topics": ["FastAPI", "API", "Python"],
            "embedding": [0.1] * 1536,
            "created_at": "2025-01-01T00:00:00Z"
        },
        {
            "source_name": "SurrealDB",
            "source_url": "https://surrealdb.com/docs/",
            "title": "SurrealDB Documentation",
            "content": "SurrealDB is a multi-model database with vector search capabilities.",
            "chunk_index": 0,
            "total_chunks": 1,
            "quality_score": 0.85,
            "topics": ["SurrealDB", "database", "vector"],
            "embedding": [0.2] * 1536,
            "created_at": "2025-01-01T00:00:00Z"
        }
    ]

@pytest.fixture
def production_sources():
    """Production documentation sources for testing."""
    return [
        {"name": "FastAPI", "url": "https://fastapi.tiangolo.com/", "priority": "high"},
        {"name": "SurrealDB", "url": "https://surrealdb.com/docs/surrealdb", "priority": "high"},
        {"name": "TestAPI", "url": "https://test.example.com/docs", "priority": "medium"}
    ]

@pytest.fixture
def mock_logfire():
    """Mock Logfire for testing."""
    with pytest.MonkeyPatch.context() as m:
        mock_logfire = Mock()
        mock_logfire.configure = Mock()
        mock_logfire.info = Mock()
        mock_logfire.error = Mock()
        mock_logfire.warning = Mock()
        mock_logfire.debug = Mock()
        mock_logfire.instrument = lambda *args, **kwargs: lambda func: func
        mock_logfire.span = Mock()

        m.setattr("logfire", mock_logfire)
        yield mock_logfire
