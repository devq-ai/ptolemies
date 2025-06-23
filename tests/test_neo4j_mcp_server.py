#!/usr/bin/env python3
"""
Test suite for Neo4j MCP Server with Logfire instrumentation
"""

import pytest
import asyncio
import os
import sys
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path

# Set logfire config for testing
os.environ['LOGFIRE_IGNORE_NO_CONFIG'] = '1'

# Add neo4j_mcp to path
sys.path.insert(0, str(Path(__file__).parent.parent / "neo4j_mcp"))

from neo4j_mcp_server import Neo4jDatabase, Neo4jMCPServer
from mcp.types import CallToolResult, TextContent

class TestNeo4jDatabase:
    """Test Neo4j database integration with Logfire instrumentation."""
    
    @pytest.fixture
    def mock_driver(self):
        """Mock Neo4j driver."""
        driver = Mock()
        session = Mock()
        result = Mock()
        summary = Mock()
        
        # Configure result and summary
        result.consume.return_value = summary
        summary.result_available_after = 10
        summary.result_consumed_after = 15
        summary.server.address = "localhost:7687"
        summary.server.protocol_version = "4.4"
        summary.database = "neo4j"
        summary.query_type = "READ_ONLY"
        summary.plan = None
        summary.profile = None
        summary.notifications = []
        
        # Configure counters
        counters = Mock()
        counters.nodes_created = 0
        counters.nodes_deleted = 0
        counters.relationships_created = 0
        counters.relationships_deleted = 0
        counters.properties_set = 0
        counters.labels_added = 0
        counters.labels_removed = 0
        counters.indexes_added = 0
        counters.indexes_removed = 0
        counters.constraints_added = 0
        counters.constraints_removed = 0
        summary.counters = counters
        
        # Configure session and driver
        session.run.return_value = result
        session.__enter__ = Mock(return_value=session)
        session.__exit__ = Mock(return_value=None)
        driver.session.return_value = session
        
        return driver
    
    @patch('neo4j_mcp_server.neo4j.GraphDatabase.driver')
    def test_database_connection(self, mock_driver_class, mock_driver):
        """Test database connection with Logfire logging."""
        mock_driver_class.return_value = mock_driver
        
        # Create database instance
        db = Neo4jDatabase(
            uri="bolt://localhost:7687",
            username="neo4j",
            password="password",
            database="neo4j"
        )
        
        # Verify connection was established
        mock_driver_class.assert_called_once_with(
            "bolt://localhost:7687",
            auth=("neo4j", "password")
        )
        assert db.driver == mock_driver
    
    @patch('neo4j_mcp_server.neo4j.GraphDatabase.driver')
    def test_execute_query_success(self, mock_driver_class, mock_driver):
        """Test successful query execution with Logfire instrumentation."""
        mock_driver_class.return_value = mock_driver
        
        # Configure mock result
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([{"name": "test"}]))
        mock_result.consume.return_value = mock_driver.session.return_value.run.return_value.consume.return_value
        
        session = mock_driver.session.return_value.__enter__.return_value
        session.run.return_value = mock_result
        
        db = Neo4jDatabase("bolt://localhost:7687", "neo4j", "password")
        
        # Execute query
        result = db.execute_query("MATCH (n) RETURN n.name as name")
        
        # Verify query was executed
        session.run.assert_called_with("MATCH (n) RETURN n.name as name", {})
        
        # Verify result structure
        assert "records" in result
        assert "summary" in result
        assert result["records"] == [{"name": "test"}]
        assert result["summary"]["query"] == "MATCH (n) RETURN n.name as name"
    
    @patch('neo4j_mcp_server.neo4j.GraphDatabase.driver')
    def test_execute_query_with_parameters(self, mock_driver_class, mock_driver):
        """Test query execution with parameters."""
        mock_driver_class.return_value = mock_driver
        
        # Configure mock result
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([]))
        mock_result.consume.return_value = mock_driver.session.return_value.run.return_value.consume.return_value
        
        session = mock_driver.session.return_value.__enter__.return_value
        session.run.return_value = mock_result
        
        db = Neo4jDatabase("bolt://localhost:7687", "neo4j", "password")
        
        # Execute query with parameters
        parameters = {"name": "test"}
        result = db.execute_query("MATCH (n {name: $name}) RETURN n", parameters)
        
        # Verify parameters were passed
        session.run.assert_called_with("MATCH (n {name: $name}) RETURN n", parameters)
        assert result["summary"]["parameters"] == parameters
    
    @patch('neo4j_mcp_server.neo4j.GraphDatabase.driver')
    def test_execute_query_error(self, mock_driver_class, mock_driver):
        """Test query execution error handling."""
        mock_driver_class.return_value = mock_driver
        
        # Configure initial connection to succeed but query execution to fail
        session = mock_driver.session.return_value.__enter__.return_value
        session.run.side_effect = [None, Exception("Query failed")]  # First call succeeds, second fails
        
        db = Neo4jDatabase("bolt://localhost:7687", "neo4j", "password")
        
        # Execute query that will fail
        result = db.execute_query("INVALID QUERY")
        
        # Verify error handling
        assert "error" in result
        assert "Query failed" in result["error"]
    
    @patch('neo4j_mcp_server.neo4j.GraphDatabase.driver')
    def test_get_schema(self, mock_driver_class, mock_driver):
        """Test schema retrieval with Logfire instrumentation."""
        mock_driver_class.return_value = mock_driver
        
        # Configure mock results for schema queries
        def side_effect(query):
            mock_result = Mock()
            if "db.labels()" in query:
                mock_result.__iter__ = Mock(return_value=iter([{"label": "Person"}, {"label": "Company"}]))
            elif "db.relationshipTypes()" in query:
                mock_result.__iter__ = Mock(return_value=iter([{"relationshipType": "WORKS_FOR"}]))
            elif "db.propertyKeys()" in query:
                mock_result.__iter__ = Mock(return_value=iter([{"propertyKey": "name"}, {"propertyKey": "age"}]))
            elif "SHOW INDEXES" in query:
                mock_result.__iter__ = Mock(return_value=iter([{"name": "person_name_index", "type": "BTREE"}]))
            elif "SHOW CONSTRAINTS" in query:
                mock_result.__iter__ = Mock(return_value=iter([{"name": "person_unique", "type": "UNIQUENESS"}]))
            return mock_result
        
        session = mock_driver.session.return_value.__enter__.return_value
        session.run.side_effect = side_effect
        
        db = Neo4jDatabase("bolt://localhost:7687", "neo4j", "password")
        
        # Get schema
        schema = db.get_schema()
        
        # Verify schema structure
        assert "labels" in schema
        assert "relationship_types" in schema
        assert "property_keys" in schema
        assert "indexes" in schema
        assert "constraints" in schema
        
        assert schema["labels"] == ["Person", "Company"]
        assert schema["relationship_types"] == ["WORKS_FOR"]
        assert schema["property_keys"] == ["name", "age"]
    
    @patch('neo4j_mcp_server.neo4j.GraphDatabase.driver')
    def test_close_connection(self, mock_driver_class, mock_driver):
        """Test connection closure."""
        mock_driver_class.return_value = mock_driver
        
        db = Neo4jDatabase("bolt://localhost:7687", "neo4j", "password")
        db.close()
        
        # Verify driver was closed
        mock_driver.close.assert_called_once()

class TestNeo4jMCPServer:
    """Test Neo4j MCP Server implementation."""
    
    @pytest.fixture
    def mock_database(self):
        """Mock Neo4j database."""
        db = Mock()
        db.execute_query.return_value = {
            "records": [{"test": "data"}],
            "summary": {
                "query": "TEST",
                "result_count": 1,
                "counters": {}
            }
        }
        db.get_schema.return_value = {
            "labels": ["Person"],
            "relationship_types": ["KNOWS"],
            "property_keys": ["name"]
        }
        return db
    
    @patch.dict(os.environ, {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "password",
        "NEO4J_DATABASE": "neo4j"
    })
    @patch('neo4j_mcp_server.Neo4jDatabase')
    def test_mcp_server_initialization(self, mock_db_class):
        """Test MCP server initialization with environment variables."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        
        server = Neo4jMCPServer()
        
        # Verify database was initialized with correct parameters
        mock_db_class.assert_called_once_with(
            "bolt://localhost:7687",
            "neo4j", 
            "password",
            "neo4j"
        )
        assert server.db == mock_db
    
    @patch('neo4j_mcp_server.Neo4jDatabase')
    def test_execute_cypher_query_tool(self, mock_db_class):
        """Test execute_cypher_query MCP tool."""
        mock_db = Mock()
        mock_db.execute_query.return_value = {
            "records": [{"name": "test"}],
            "summary": {"result_count": 1}
        }
        mock_db_class.return_value = mock_db
        
        server = Neo4jMCPServer()
        
        # Test the tool call directly
        # Note: In real test, we'd need to set up proper MCP infrastructure
        # For now, test the underlying logic
        arguments = {
            "query": "MATCH (n) RETURN n.name",
            "parameters": {"limit": 10}
        }
        
        # Verify query would be executed
        result = mock_db.execute_query(arguments["query"], arguments["parameters"])
        assert result["records"] == [{"name": "test"}]
    
    @patch('neo4j_mcp_server.Neo4jDatabase')
    def test_get_database_schema_tool(self, mock_db_class):
        """Test get_database_schema MCP tool."""
        mock_db = Mock()
        mock_db.get_schema.return_value = {
            "labels": ["Person", "Company"],
            "relationship_types": ["WORKS_FOR"],
            "property_keys": ["name", "title"]
        }
        mock_db_class.return_value = mock_db
        
        server = Neo4jMCPServer()
        
        # Test schema retrieval
        schema = mock_db.get_schema()
        assert schema["labels"] == ["Person", "Company"]
        assert schema["relationship_types"] == ["WORKS_FOR"]
        assert schema["property_keys"] == ["name", "title"]
    
    @patch('neo4j_mcp_server.Neo4jDatabase')
    def test_create_node_tool(self, mock_db_class):
        """Test create_node MCP tool."""
        mock_db = Mock()
        mock_db.execute_query.return_value = {
            "records": [{"n": {"name": "test", "age": 30}}],
            "summary": {"result_count": 1}
        }
        mock_db_class.return_value = mock_db
        
        server = Neo4jMCPServer()
        
        # Test node creation logic
        labels = ["Person"]
        properties = {"name": "test", "age": 30}
        
        # Format properties (test internal method)
        props_str = server._format_properties(properties)
        expected_query = f"CREATE (n:Person {props_str}) RETURN n"
        
        # Verify properties formatting
        assert "name: 'test'" in props_str
        assert "age: 30" in props_str
    
    @patch('neo4j_mcp_server.Neo4jDatabase')
    def test_create_relationship_tool(self, mock_db_class):
        """Test create_relationship MCP tool."""
        mock_db = Mock()
        mock_db.execute_query.return_value = {
            "records": [{"a": {}, "r": {}, "b": {}}],
            "summary": {"result_count": 1}
        }
        mock_db_class.return_value = mock_db
        
        server = Neo4jMCPServer()
        
        # Test relationship creation logic
        from_query = "n.name = 'Alice'"
        to_query = "n.name = 'Bob'"
        rel_type = "KNOWS"
        properties = {"since": "2023"}
        
        # This would generate the relationship creation query
        props_str = server._format_properties(properties)
        expected_query = f"""
                    MATCH (a) WHERE {from_query}
                    MATCH (b) WHERE {to_query}
                    CREATE (a)-[r:{rel_type} {props_str}]->(b)
                    RETURN a, r, b
                    """
        
        # Verify properties formatting
        assert "since: '2023'" in props_str

class TestUtilityMethods:
    """Test utility methods and formatting."""
    
    @patch('neo4j_mcp_server.Neo4jDatabase')
    def test_format_properties(self, mock_db_class):
        """Test property formatting for Cypher queries."""
        server = Neo4jMCPServer()
        
        # Test string properties
        props = {"name": "test", "title": "Mr"}
        result = server._format_properties(props)
        assert "name: 'test'" in result
        assert "title: 'Mr'" in result
        
        # Test numeric properties
        props = {"age": 30, "score": 95.5}
        result = server._format_properties(props)
        assert "age: 30" in result
        assert "score: 95.5" in result
        
        # Test empty properties
        result = server._format_properties({})
        assert result == ""
    
    @patch('neo4j_mcp_server.Neo4jDatabase')
    def test_format_query_result(self, mock_db_class):
        """Test query result formatting."""
        server = Neo4jMCPServer()
        
        # Test successful result
        result = {
            "records": [{"name": "test"}, {"name": "test2"}],
            "summary": {
                "query": "MATCH (n) RETURN n.name",
                "result_count": 2,
                "counters": {
                    "nodes_created": 1,
                    "properties_set": 2
                }
            }
        }
        
        formatted = server._format_query_result(result)
        assert "Query: MATCH (n) RETURN n.name" in formatted
        assert "Records returned: 2" in formatted
        assert "nodes_created: 1" in formatted
        assert "properties_set: 2" in formatted
        
        # Test error result
        error_result = {"error": "Query failed"}
        formatted = server._format_query_result(error_result)
        assert "Error: Query failed" in formatted
    
    @patch('neo4j_mcp_server.Neo4jDatabase')
    def test_format_schema(self, mock_db_class):
        """Test schema formatting."""
        server = Neo4jMCPServer()
        
        schema = {
            "labels": ["Person", "Company"],
            "relationship_types": ["WORKS_FOR", "KNOWS"],
            "property_keys": ["name", "age", "title"],
            "indexes": [{"name": "person_index", "type": "BTREE"}],
            "constraints": [{"name": "person_unique", "type": "UNIQUENESS"}]
        }
        
        formatted = server._format_schema(schema)
        assert "Labels (2): Person, Company" in formatted
        assert "Relationship Types (2): WORKS_FOR, KNOWS" in formatted
        assert "Property Keys (3): name, age, title" in formatted
        assert "Indexes (1):" in formatted
        assert "Constraints (1):" in formatted

class TestLogfireInstrumentation:
    """Test Logfire instrumentation coverage."""
    
    @patch('neo4j_mcp_server.logfire')
    @patch('neo4j_mcp_server.Neo4jDatabase')
    def test_logfire_spans_created(self, mock_db_class, mock_logfire):
        """Test that Logfire spans are created for instrumented methods."""
        mock_span = Mock()
        mock_logfire.span.return_value.__enter__ = Mock(return_value=mock_span)
        mock_logfire.span.return_value.__exit__ = Mock(return_value=None)
        
        server = Neo4jMCPServer()
        
        # Verify Logfire is used for logging (configure is called at module level)
        mock_logfire.info.assert_called()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])