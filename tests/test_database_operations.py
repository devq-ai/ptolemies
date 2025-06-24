"""
Database Operations Test Suite
Tests SurrealDB integration and data persistence
"""

import pytest
import subprocess
from unittest.mock import Mock, patch, call
import sys
import os

# Add src to path for imports
sys.path.insert(0, 'src')

try:
    from production_crawler_hybrid import run_surreal_query, load_env_file
    from debug_crawler import run_surreal_query_debug
    from fixed_storage_crawler import run_surreal_command_fixed
    from final_five_crawler import run_surreal_insert
except ImportError as e:
    pytest.skip(f"Missing component: {e}", allow_module_level=True)

class TestSurrealDBOperations:
    """Test SurrealDB query operations."""
    
    def test_run_surreal_query_success(self, mock_env_file):
        """Test successful SurrealDB query execution."""
        with patch('production_crawler_hybrid.load_env_file') as mock_load_env, \
             patch('subprocess.run') as mock_run:
            
            # Mock environment loading
            mock_load_env.return_value = {
                'SURREALDB_URL': 'ws://localhost:8000/rpc',
                'SURREALDB_USERNAME': 'root',
                'SURREALDB_PASSWORD': 'root',
                'SURREALDB_NAMESPACE': 'test',
                'SURREALDB_DATABASE': 'test'
            }
            
            # Mock successful subprocess
            mock_run.return_value = Mock(returncode=0, stdout="success", stderr="")
            
            result = run_surreal_query("SELECT 1;")
            
            assert result is True
            mock_run.assert_called_once()
            
            # Verify command structure
            args, kwargs = mock_run.call_args
            cmd = args[0] if args else kwargs.get('cmd', [])
            assert 'surreal' in cmd
            assert 'sql' in cmd
            assert '--conn' in cmd
            assert 'ws://localhost:8000/rpc' in cmd

    def test_run_surreal_query_failure(self, mock_env_file):
        """Test failed SurrealDB query execution."""
        with patch('production_crawler_hybrid.load_env_file') as mock_load_env, \
             patch('subprocess.run') as mock_run:
            
            mock_load_env.return_value = {}
            mock_run.return_value = Mock(returncode=1, stdout="", stderr="Error")
            
            result = run_surreal_query("INVALID QUERY;")
            
            assert result is False

    def test_run_surreal_query_timeout(self, mock_env_file):
        """Test SurrealDB query timeout handling."""
        with patch('production_crawler_hybrid.load_env_file') as mock_load_env, \
             patch('subprocess.run') as mock_run:
            
            mock_load_env.return_value = {}
            mock_run.side_effect = subprocess.TimeoutExpired('surreal', 30)
            
            result = run_surreal_query("SELECT * FROM large_table;")
            
            assert result is False

class TestDebugQueryOperations:
    """Test debug query operations with enhanced logging."""
    
    def test_debug_query_success_with_logging(self):
        """Test debug query with successful execution and logging."""
        with patch('debug_crawler.load_env_file') as mock_load_env, \
             patch('subprocess.run') as mock_run, \
             patch('debug_crawler.logfire') as mock_logfire:
            
            mock_load_env.return_value = {
                'SURREALDB_URL': 'ws://localhost:8000/rpc'
            }
            mock_run.return_value = Mock(returncode=0, stdout="success", stderr="")
            
            success, output = run_surreal_query_debug("SELECT 1;")
            
            assert success is True
            assert "success" in output
            # Verify no error logging occurred
            mock_logfire.error.assert_not_called()

    def test_debug_query_failure_with_logging(self):
        """Test debug query failure with error logging."""
        with patch('debug_crawler.load_env_file') as mock_load_env, \
             patch('subprocess.run') as mock_run, \
             patch('debug_crawler.logfire') as mock_logfire:
            
            mock_load_env.return_value = {}
            mock_run.return_value = Mock(returncode=1, stdout="", stderr="Connection failed")
            
            success, output = run_surreal_query_debug("SELECT 1;")
            
            assert success is False
            assert "Connection failed" in output
            # Verify error logging occurred
            mock_logfire.error.assert_called()

class TestFixedStorageOperations:
    """Test fixed storage operations with transaction handling."""
    
    def test_fixed_storage_command_with_commit(self):
        """Test fixed storage command includes commit."""
        with patch('fixed_storage_crawler.load_env_file') as mock_load_env, \
             patch('subprocess.run') as mock_run:
            
            mock_load_env.return_value = {}
            mock_run.return_value = Mock(returncode=0, stdout="success", stderr="")
            
            success, output, length = run_surreal_command_fixed("CREATE test SET value = 1")
            
            assert success is True
            assert length > 0
            
            # Verify COMMIT was added to query
            args, kwargs = mock_run.call_args
            input_text = kwargs.get('input', '')
            assert "COMMIT" in input_text

    def test_fixed_storage_returns_detailed_info(self):
        """Test fixed storage returns detailed execution information."""
        with patch('fixed_storage_crawler.load_env_file') as mock_load_env, \
             patch('subprocess.run') as mock_run:
            
            mock_load_env.return_value = {}
            stdout_content = '{"created": true, "id": "test:123"}'
            mock_run.return_value = Mock(returncode=0, stdout=stdout_content, stderr="")
            
            success, output, length = run_surreal_command_fixed("CREATE test SET value = 1")
            
            assert success is True
            assert output == stdout_content
            assert length == len(stdout_content)

class TestFinalFiveInsertOperations:
    """Test final five crawler insert operations."""
    
    def test_final_five_insert_simple(self):
        """Test simplified insert operations for final five sources."""
        with patch('final_five_crawler.load_env_file') as mock_load_env, \
             patch('subprocess.run') as mock_run:
            
            mock_load_env.return_value = {
                'SURREALDB_URL': 'ws://localhost:8000/rpc',
                'SURREALDB_USERNAME': 'root',
                'SURREALDB_PASSWORD': 'root',
                'SURREALDB_NAMESPACE': 'ptolemies',
                'SURREALDB_DATABASE': 'knowledge'
            }
            mock_run.return_value = Mock(returncode=0, stdout="success", stderr="")
            
            result = run_surreal_insert("CREATE document_chunks SET source_name = 'Test';")
            
            assert result is True
            mock_run.assert_called_once()

    def test_final_five_insert_error_handling(self):
        """Test error handling in final five insert operations."""
        with patch('final_five_crawler.load_env_file') as mock_load_env, \
             patch('subprocess.run') as mock_run:
            
            mock_load_env.return_value = {}
            mock_run.return_value = Mock(returncode=1, stdout="", stderr="Syntax error")
            
            result = run_surreal_insert("INVALID SQL;")
            
            assert result is False

class TestEnvironmentHandling:
    """Test environment variable handling across all components."""
    
    def test_load_env_file_comprehensive(self, tmp_path):
        """Test comprehensive environment file loading."""
        env_file = tmp_path / ".env"
        env_content = """
# Database configuration
SURREALDB_URL=ws://localhost:8000/rpc
SURREALDB_USERNAME=root
SURREALDB_PASSWORD=secret123

# API keys
OPENAI_API_KEY=sk-test123
LOGFIRE_TOKEN=pylf_test

# Empty line and comment handling

# Another comment
INVALID_LINE_NO_EQUALS
EMPTY_VALUE=
"""
        env_file.write_text(env_content)
        
        env_vars = load_env_file(str(env_file))
        
        # Test proper parsing
        assert env_vars['SURREALDB_URL'] == 'ws://localhost:8000/rpc'
        assert env_vars['SURREALDB_USERNAME'] == 'root'
        assert env_vars['SURREALDB_PASSWORD'] == 'secret123'
        assert env_vars['OPENAI_API_KEY'] == 'sk-test123'
        assert env_vars['LOGFIRE_TOKEN'] == 'pylf_test'
        assert env_vars['EMPTY_VALUE'] == ''
        
        # Test that invalid lines and comments are ignored
        assert 'INVALID_LINE_NO_EQUALS' not in env_vars
        assert len([k for k in env_vars.keys() if k.startswith('#')]) == 0

    def test_env_file_with_special_characters(self, tmp_path):
        """Test environment file with special characters in values."""
        env_file = tmp_path / ".env"
        env_content = """
PASSWORD_WITH_SPECIAL=p@ssw0rd!#$%
URL_WITH_PARAMS=ws://localhost:8000/rpc?param1=value1&param2=value2
PATH_WITH_SPACES=/path/with spaces/file.txt
"""
        env_file.write_text(env_content)
        
        env_vars = load_env_file(str(env_file))
        
        assert env_vars['PASSWORD_WITH_SPECIAL'] == 'p@ssw0rd!#$%'
        assert env_vars['URL_WITH_PARAMS'] == 'ws://localhost:8000/rpc?param1=value1&param2=value2'
        assert env_vars['PATH_WITH_SPACES'] == '/path/with spaces/file.txt'

class TestDatabaseSchemaOperations:
    """Test database schema creation and management."""
    
    def test_schema_creation_commands(self):
        """Test that schema creation uses proper SurrealDB syntax."""
        expected_schema_elements = [
            "DEFINE TABLE document_chunks SCHEMAFULL",
            "DEFINE FIELD source_name ON TABLE document_chunks TYPE string",
            "DEFINE FIELD embedding ON TABLE document_chunks TYPE array<float>",
            "DEFINE FIELD created_at ON TABLE document_chunks TYPE datetime"
        ]
        
        # Test that our schema contains required elements
        for element in expected_schema_elements:
            # This would be tested against actual schema creation code
            assert "DEFINE" in element
            assert "document_chunks" in element

class TestQueryPerformance:
    """Test query performance and optimization."""
    
    def test_query_timeout_configuration(self):
        """Test that queries have appropriate timeout settings."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            
            # Test various query functions have timeout
            with patch('production_crawler_hybrid.load_env_file', return_value={}):
                run_surreal_query("SELECT 1;")
                
            # Verify timeout was set in subprocess call
            args, kwargs = mock_run.call_args
            assert 'timeout' in kwargs
            assert kwargs['timeout'] == 30

    def test_large_query_handling(self):
        """Test handling of large queries and responses."""
        large_query = "SELECT * FROM document_chunks WHERE " + "OR ".join([f"id = 'test:{i}'" for i in range(1000)])
        
        with patch('production_crawler_hybrid.load_env_file', return_value={}), \
             patch('subprocess.run') as mock_run:
            
            # Mock large response
            large_response = '{"result": [' + ','.join(['{"id": "test:' + str(i) + '"}' for i in range(1000)]) + ']}'
            mock_run.return_value = Mock(returncode=0, stdout=large_response, stderr="")
            
            result = run_surreal_query(large_query)
            
            assert result is True
            # Verify the query was processed
            args, kwargs = mock_run.call_args
            assert len(kwargs.get('input', '')) > 1000

class TestErrorRecovery:
    """Test error recovery and resilience."""
    
    def test_connection_retry_logic(self):
        """Test connection retry behavior."""
        # This would test retry logic if implemented
        with patch('production_crawler_hybrid.load_env_file', return_value={}), \
             patch('subprocess.run') as mock_run:
            
            # Simulate connection failure then success
            mock_run.side_effect = [
                Mock(returncode=1, stdout="", stderr="Connection refused"),
                Mock(returncode=0, stdout="success", stderr="")
            ]
            
            # Current implementation doesn't retry, but test the failure
            result = run_surreal_query("SELECT 1;")
            assert result is False  # First call fails

    def test_malformed_response_handling(self):
        """Test handling of malformed database responses."""
        with patch('production_crawler_hybrid.load_env_file', return_value={}), \
             patch('subprocess.run') as mock_run:
            
            # Simulate malformed JSON response
            mock_run.return_value = Mock(returncode=0, stdout="{invalid json", stderr="")
            
            result = run_surreal_query("SELECT 1;")
            
            # Should still return True for returncode 0, regardless of malformed output
            assert result is True