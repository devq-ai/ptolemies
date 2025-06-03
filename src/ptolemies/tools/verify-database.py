#!/usr/bin/env python3
"""
verify-database.py - Verify SurrealDB connectivity and functionality for Ptolemies project

This script performs the following operations:
1. Connects to the SurrealDB instance using configuration from the .env file
2. Verifies the database is running and accessible
3. Checks that the required namespace and database exist
4. Verifies the schema has been created correctly
5. Performs basic CRUD operations with test data
"""

import os
import sys
import json
import uuid
from datetime import datetime
from pathlib import Path
import httpx
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / ".env"
if not env_path.exists():
    print("Error: .env file not found. Please create an .env file with the required configuration.")
    print("Hint: Check setup-database.sh for required environment variables.")
    sys.exit(1)

load_dotenv(env_path)

# Get database configuration from environment variables
DB_HOST = os.getenv("SURREALDB_HOST", "localhost")
DB_PORT = os.getenv("SURREALDB_PORT", "8000")
DB_USER = os.getenv("SURREALDB_USER", "root")
DB_PASS = os.getenv("SURREALDB_PASSWORD", "root")
DB_NS = os.getenv("SURREALDB_NAMESPACE", "ptolemies")
DB_NAME = os.getenv("SURREALDB_DATABASE", "knowledge")

# Construct the database URL
DB_URL = f"http://{DB_HOST}:{DB_PORT}"

# Set headers for API requests
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
}

class SurrealDBClient:
    """A simple client for interacting with SurrealDB via HTTP API"""
    
    def __init__(self, url, namespace, database, username, password):
        """Initialize the SurrealDB client with connection details"""
        self.url = url
        self.namespace = namespace
        self.database = database
        self.username = username
        self.password = password
        self.client = httpx.Client(timeout=10.0)
        self.token = None
    
    def signin(self):
        """Sign in to SurrealDB and obtain authentication token"""
        try:
            headers = HEADERS.copy()
            headers["Content-Type"] = "application/json"
            response = self.client.post(
                f"{self.url}/signin",
                headers=headers,
                json={"user": self.username, "pass": self.password}
            )
            response.raise_for_status()
            self.token = response.json()
            return True
        except httpx.HTTPStatusError as e:
            print(f"Error signing in: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error during signin: {e}")
            return False
    
    def get_auth_headers(self):
        """Get headers with authentication token"""
        if not self.token:
            self.signin()
        
        headers = HEADERS.copy()
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    def use_namespace_database(self):
        """Set the namespace and database to use"""
        try:
            headers = self.get_auth_headers()
            headers["Content-Type"] = "application/json"
            response = self.client.post(
                f"{self.url}/use",
                headers=headers,
                json={"ns": self.namespace, "db": self.database}
            )
            response.raise_for_status()
            return True
        except httpx.HTTPStatusError as e:
            print(f"Error selecting namespace/database: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error selecting namespace/database: {e}")
            return False
    
    def query(self, sql, variables=None):
        """Execute a SQL query against SurrealDB"""
        try:
            data = {"query": sql}
            if variables:
                data["vars"] = variables
                
            headers = self.get_auth_headers()
            headers["Content-Type"] = "application/json"
            response = self.client.post(
                f"{self.url}/sql",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Error executing query: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error during query: {e}")
            return None
    
    def create(self, table, data):
        """Create a record in the specified table"""
        try:
            response = self.client.post(
                f"{self.url}/key/{table}/create",
                headers=self.get_auth_headers(),
                json=data
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Error creating record: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error creating record: {e}")
            return None
    
    def get(self, table, id):
        """Get a record by ID"""
        try:
            response = self.client.get(
                f"{self.url}/key/{table}/{id}",
                headers=self.get_auth_headers()
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Error getting record: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error getting record: {e}")
            return None
    
    def delete(self, table, id):
        """Delete a record by ID"""
        try:
            response = self.client.delete(
                f"{self.url}/key/{table}/{id}",
                headers=self.get_auth_headers()
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Error deleting record: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error deleting record: {e}")
            return None

def check_connection(client):
    """Check connection to SurrealDB"""
    print("\n1. Checking database connection...")
    
    try:
        # Try to sign in to verify connection
        if client.signin():
            print("✅ Successfully connected to SurrealDB at", DB_URL)
            return True
        else:
            print("❌ Failed to connect to SurrealDB")
            return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

def check_namespace_database(client):
    """Check if namespace and database exist"""
    print("\n2. Checking namespace and database...")
    
    if client.use_namespace_database():
        print(f"✅ Successfully selected namespace '{DB_NS}' and database '{DB_NAME}'")
        return True
    else:
        print(f"❌ Failed to select namespace '{DB_NS}' and database '{DB_NAME}'")
        return False

def check_schema(client):
    """Check if the required tables and schema exist"""
    print("\n3. Checking database schema...")
    
    # Query to get information about tables
    result = client.query("INFO FOR DB;")
    
    if not result:
        print("❌ Failed to retrieve database schema information")
        return False
    
    # Extract tables from the result
    tables = set()
    for item in result:
        if 'result' in item and item['result']:
            for table_info in item['result']:
                if 'tables' in table_info:
                    for table in table_info['tables']:
                        tables.add(table['name'])
    
    # Check for required tables
    required_tables = {'knowledge_item', 'embedding', 'relationship'}
    missing_tables = required_tables - tables
    
    if missing_tables:
        print(f"❌ Missing tables: {', '.join(missing_tables)}")
        return False
    else:
        print(f"✅ All required tables exist: {', '.join(required_tables)}")
        return True

def perform_basic_operations(client):
    """Perform basic CRUD operations with test data"""
    print("\n4. Performing basic CRUD operations...")
    
    # Generate a unique ID for test data
    test_id = str(uuid.uuid4())
    
    # Create a test knowledge item
    test_item = {
        "id": test_id,
        "title": "Test Knowledge Item",
        "content": "This is a test knowledge item created by verify-database.py",
        "content_type": "text/plain",
        "metadata": {"test": True, "purpose": "verification"},
        "tags": ["test", "verification"],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "version": 1,
        "source": "verify-database.py"
    }
    
    print(f"Creating test knowledge item with ID: {test_id}")
    create_result = client.create("knowledge_item", test_item)
    
    if not create_result:
        print("❌ Failed to create test knowledge item")
        return False
    
    print("✅ Successfully created test knowledge item")
    
    # Query the item back
    print(f"Querying test knowledge item with ID: {test_id}")
    query_result = client.get("knowledge_item", test_id)
    
    if not query_result:
        print("❌ Failed to query test knowledge item")
        return False
    
    print("✅ Successfully queried test knowledge item")
    
    # Delete the test item
    print(f"Deleting test knowledge item with ID: {test_id}")
    delete_result = client.delete("knowledge_item", test_id)
    
    if not delete_result:
        print("❌ Failed to delete test knowledge item")
        return False
    
    print("✅ Successfully deleted test knowledge item")
    
    # Verify deletion
    verify_result = client.get("knowledge_item", test_id)
    if verify_result and verify_result[0].get('result'):
        print("❌ Test knowledge item still exists after deletion")
        return False
    
    print("✅ Verified test knowledge item was properly deleted")
    return True

def main():
    """Main function to verify database setup and functionality"""
    print("=" * 60)
    print("Ptolemies SurrealDB Verification Tool")
    print("=" * 60)
    
    # Initialize SurrealDB client
    client = SurrealDBClient(
        url=DB_URL,
        namespace=DB_NS,
        database=DB_NAME,
        username=DB_USER,
        password=DB_PASS
    )
    
    # Run verification checks
    connection_ok = check_connection(client)
    if not connection_ok:
        print("\n❌ Database connection failed. Please check your SurrealDB installation and configuration.")
        sys.exit(1)
    
    namespace_db_ok = check_namespace_database(client)
    if not namespace_db_ok:
        print("\n❌ Namespace/database verification failed. Please run setup-database.sh to initialize the database.")
        sys.exit(1)
    
    schema_ok = check_schema(client)
    if not schema_ok:
        print("\n❌ Schema verification failed. Please run setup-database.sh to initialize the schema.")
        sys.exit(1)
    
    operations_ok = perform_basic_operations(client)
    if not operations_ok:
        print("\n❌ Basic operations verification failed. Please check database permissions and configuration.")
        sys.exit(1)
    
    # All checks passed
    print("\n" + "=" * 60)
    print("✅ All database verification checks passed successfully!")
    print(f"• SurrealDB is running at: {DB_URL}")
    print(f"• Namespace: {DB_NS}")
    print(f"• Database: {DB_NAME}")
    print("• Schema is correctly configured")
    print("• Basic operations are working properly")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nVerification process interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error during verification: {e}")
        sys.exit(1)