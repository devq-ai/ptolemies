#!/bin/bash

# setup-database.sh
# Script to set up SurrealDB for the Ptolemies Knowledge Base
# This script is idempotent - it will not reinstall or reconfigure 
# components that are already set up correctly.

set -e  # Exit on any error

# Load environment variables
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    # Load environment variables without trying to export them directly
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ "$key" =~ ^#.*$ ]] && continue
        [[ -z "$key" ]] && continue
        # Remove quotes from the value if present
        value=$(echo "$value" | sed -e 's/^"//' -e 's/"$//')
        # Export the variable
        export "$key=$value"
    done < .env
else
    echo "Error: .env file not found. Please create an .env file with the required configuration."
    exit 1
fi

# Default values if env vars are not set
DB_HOST=${SURREALDB_HOST:-localhost}
DB_PORT=${SURREALDB_PORT:-8000}
DB_USER=${SURREALDB_USER:-root}
DB_PASS=${SURREALDB_PASSWORD:-root}
DB_NS=${SURREALDB_NAMESPACE:-ptolemies}
DB_NAME=${SURREALDB_DATABASE:-knowledge}
ADMIN_USER="admin"
ADMIN_PASS="ptolemiesadmin"  # You might want to change this or make it configurable

# Check if homebrew is installed
check_homebrew() {
    echo "Checking if Homebrew is installed..."
    if ! command -v brew &>/dev/null; then
        echo "Homebrew is not installed. Please install Homebrew first:"
        echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
    echo "✅ Homebrew is installed."
}

# Check if SurrealDB is installed, install if not
check_install_surrealdb() {
    echo "Checking if SurrealDB is installed..."
    if ! command -v surreal &>/dev/null; then
        echo "SurrealDB is not installed. Installing with Homebrew..."
        brew install surrealdb/tap/surreal
        echo "✅ SurrealDB installed successfully."
    else
        echo "✅ SurrealDB is already installed."
    fi
}

# Check if SurrealDB is running, start if not
check_start_surrealdb() {
    echo "Checking if SurrealDB is running on port $DB_PORT..."
    if ! nc -z localhost $DB_PORT &>/dev/null; then
        echo "SurrealDB is not running. Starting SurrealDB..."
        
        # Start SurrealDB in the background
        nohup surreal start --log debug --user $DB_USER --pass $DB_PASS --bind 0.0.0.0:$DB_PORT memory &>/dev/null &
        
        # Store the PID
        SURREAL_PID=$!
        echo "SurrealDB started with PID: $SURREAL_PID"
        
        # Wait for SurrealDB to start
        echo "Waiting for SurrealDB to start..."
        for i in {1..10}; do
            if nc -z localhost $DB_PORT; then
                echo "✅ SurrealDB is now running on port $DB_PORT."
                break
            fi
            if [ $i -eq 10 ]; then
                echo "Error: SurrealDB failed to start within the expected time."
                exit 1
            fi
            sleep 1
        done
    else
        echo "✅ SurrealDB is already running on port $DB_PORT."
    fi
}

# Create namespace and database
setup_namespace_database() {
    echo "Setting up namespace and database..."
    
    # Create a temporary SQL file
    TMP_SQL=$(mktemp)
    
    cat > $TMP_SQL <<EOF
-- Define the namespace and database
DEFINE NAMESPACE $DB_NS;
USE NAMESPACE $DB_NS;
DEFINE DATABASE $DB_NAME;
USE DATABASE $DB_NAME;

-- Output confirmation message
INFO "Namespace $DB_NS and database $DB_NAME created or already exist.";
EOF
    
    # Execute the SQL file
    surreal sql --conn http://$DB_HOST:$DB_PORT --user $DB_USER --pass $DB_PASS --ns $DB_NS --db $DB_NAME --pretty < $TMP_SQL
    
    # Clean up
    rm $TMP_SQL
    
    echo "✅ Namespace and database setup complete."
}

# Create schema (tables, indexes, etc.)
setup_schema() {
    echo "Setting up database schema..."
    
    # Get vector configuration from environment
    VECTOR_DIM=${EMBEDDING_DIMENSIONS:-1536}
    VECTOR_METRIC=${VECTOR_DISTANCE_METRIC:-cosine}
    
    # Create a temporary SQL file for schema
    TMP_SQL=$(mktemp)
    
    cat > $TMP_SQL <<EOF
-- Use the specified namespace and database
USE NAMESPACE $DB_NS;
USE DATABASE $DB_NAME;

-- Set dimension and distance metric for vector operations
LET \$dimensions = $VECTOR_DIM;
LET \$distance_metric = '$VECTOR_METRIC';

-- Define Knowledge Item table
DEFINE TABLE knowledge_item SCHEMAFULL;

DEFINE FIELD id ON knowledge_item TYPE string;
DEFINE FIELD title ON knowledge_item TYPE string;
DEFINE FIELD content ON knowledge_item TYPE string;
DEFINE FIELD content_type ON knowledge_item TYPE string;
DEFINE FIELD metadata ON knowledge_item TYPE object;
DEFINE FIELD tags ON knowledge_item TYPE array;
DEFINE FIELD embedding_id ON knowledge_item TYPE string;
DEFINE FIELD created_at ON knowledge_item TYPE datetime;
DEFINE FIELD updated_at ON knowledge_item TYPE datetime;
DEFINE FIELD version ON knowledge_item TYPE int;
DEFINE FIELD source ON knowledge_item TYPE string;

-- Define indexes for knowledge_item
DEFINE INDEX knowledge_item_title ON knowledge_item FIELDS title;
DEFINE INDEX knowledge_item_tags ON knowledge_item FIELDS tags;
DEFINE INDEX knowledge_item_content_type ON knowledge_item FIELDS content_type;
DEFINE INDEX knowledge_item_created_at ON knowledge_item FIELDS created_at;
DEFINE INDEX knowledge_item_updated_at ON knowledge_item FIELDS updated_at;
DEFINE INDEX knowledge_item_embedding_id ON knowledge_item FIELDS embedding_id;

-- Define Embedding table
DEFINE TABLE embedding SCHEMAFULL;

DEFINE FIELD id ON embedding TYPE string;
DEFINE FIELD vector ON embedding TYPE array<float>;
DEFINE FIELD model ON embedding TYPE string;
DEFINE FIELD dimensions ON embedding TYPE int;
DEFINE FIELD item_id ON embedding TYPE string;
DEFINE FIELD created_at ON embedding TYPE datetime;

-- Define indexes for embedding
DEFINE INDEX embedding_item_id ON embedding FIELDS item_id;
DEFINE INDEX embedding_model ON embedding FIELDS model;

-- Define vector index for similarity search
-- Using HNSW index for fast approximate nearest neighbors
DEFINE INDEX vector_index_hnsw ON embedding 
FIELDS vector 
VECTOR HNSW 
DIMENSION \$dimensions 
DISTANCE \$distance_metric;

-- Alternative M-Tree index (commented out by default)
-- DEFINE INDEX vector_index_mtree ON embedding 
-- FIELDS vector 
-- MTREE 
-- DIMENSION \$dimensions 
-- DISTANCE \$distance_metric;

-- Define vector search functions
DEFINE FUNCTION fn::similarity_search(\$query_vector: array<float>, \$limit: int, \$threshold: float) {
    LET \$items = SELECT 
        e.item_id, 
        k.*, 
        vector::similarity::\$distance_metric(e.vector, \$query_vector) AS score
    FROM embedding AS e
    INNER JOIN knowledge_item AS k ON k.id = e.item_id
    WHERE e.vector <|\$threshold|> \$query_vector
    ORDER BY score DESC
    LIMIT \$limit;
    
    RETURN \$items;
};

-- Define Relationship table for graph connections
DEFINE TABLE relationship SCHEMAFULL;

DEFINE FIELD type ON relationship TYPE string;
DEFINE FIELD source_id ON relationship TYPE string;
DEFINE FIELD target_id ON relationship TYPE string;
DEFINE FIELD weight ON relationship TYPE float;
DEFINE FIELD metadata ON relationship TYPE object;

-- Define indexes for relationship
DEFINE INDEX relationship_source ON relationship FIELDS source_id;
DEFINE INDEX relationship_target ON relationship FIELDS target_id;
DEFINE INDEX relationship_type ON relationship FIELDS type;
DEFINE INDEX relationship_source_target ON relationship FIELDS source_id, target_id;

-- Create permission scopes
DEFINE SCOPE allusers SESSION 24h
  SIGNUP (
    CREATE user SET email = \$email, pass = crypto::argon2::generate(\$pass)
  )
  SIGNIN (
    SELECT * FROM user WHERE email = \$email AND crypto::argon2::compare(pass, \$pass)
  );

-- Output confirmation message
INFO "Schema setup complete.";
EOF
    
    # Execute the SQL file
    surreal sql --conn http://$DB_HOST:$DB_PORT --user $DB_USER --pass $DB_PASS --ns $DB_NS --db $DB_NAME --pretty < $TMP_SQL
    
    # Clean up
    rm $TMP_SQL
    
    echo "✅ Schema setup complete."
}

# Create admin user
create_admin_user() {
    echo "Creating admin user..."
    
    # Create a temporary SQL file for admin user
    TMP_SQL=$(mktemp)
    
    cat > $TMP_SQL <<EOF
-- Use the specified namespace and database
USE NAMESPACE $DB_NS;
USE DATABASE $DB_NAME;

-- Create admin user table if it doesn't exist
DEFINE TABLE admin_user SCHEMAFULL;
DEFINE FIELD username ON admin_user TYPE string;
DEFINE FIELD password ON admin_user TYPE string;
DEFINE FIELD created_at ON admin_user TYPE datetime;
DEFINE FIELD role ON admin_user TYPE string;

-- Check if admin user already exists
LET existing_admin = SELECT * FROM admin_user WHERE username = '$ADMIN_USER';

-- Create admin user if it doesn't exist
IF array::len(\$existing_admin) == 0 THEN
    CREATE admin_user SET 
        username = '$ADMIN_USER', 
        password = crypto::argon2::generate('$ADMIN_PASS'), 
        created_at = time::now(), 
        role = 'admin';
    INFO "Admin user created.";
ELSE
    INFO "Admin user already exists.";
END;
EOF
    
    # Execute the SQL file
    surreal sql --conn http://$DB_HOST:$DB_PORT --user $DB_USER --pass $DB_PASS --ns $DB_NS --db $DB_NAME --pretty < $TMP_SQL
    
    # Clean up
    rm $TMP_SQL
    
    echo "✅ Admin user setup complete."
}

# Main execution
main() {
    echo "Starting Ptolemies Knowledge Base database setup..."
    
    check_homebrew
    check_install_surrealdb
    check_start_surrealdb
    setup_namespace_database
    setup_schema
    create_admin_user
    
    echo ""
    echo "✅ Ptolemies Knowledge Base database setup complete!"
    echo "SurrealDB is running at: http://$DB_HOST:$DB_PORT"
    echo "Namespace: $DB_NS"
    echo "Database: $DB_NAME"
    echo "Admin Username: $ADMIN_USER"
    echo "Admin Password: $ADMIN_PASS"
    echo ""
    echo "You can connect to the database using:"
    echo "  surreal sql --conn http://$DB_HOST:$DB_PORT --user $DB_USER --pass $DB_PASS --ns $DB_NS --db $DB_NAME"
    echo ""
}

# Run the main function
main