#!/bin/bash
# Check SurrealDB setup for Ptolemies

# Connection details
SURREALDB_HOST="localhost"
SURREALDB_PORT="8000"
SURREALDB_USER="root"
SURREALDB_PASS="root"
SURREALDB_NS="ptolemies"
SURREALDB_DB="knowledge"

echo "Checking SurrealDB setup..."

# Check if SurrealDB is running
if ! curl -s "http://${SURREALDB_HOST}:${SURREALDB_PORT}/health" > /dev/null; then
  echo "Error: SurrealDB is not running!"
  exit 1
fi

echo "SurrealDB is running."

# Check available namespaces
echo "Checking namespaces..."
curl -s -X POST "http://${SURREALDB_HOST}:${SURREALDB_PORT}/sql" \
  -H "Content-Type: application/json" \
  -u "${SURREALDB_USER}:${SURREALDB_PASS}" \
  -d "INFO FOR NS;" | jq .

# Create namespace if it doesn't exist
echo "Creating namespace '${SURREALDB_NS}'..."
curl -s -X POST "http://${SURREALDB_HOST}:${SURREALDB_PORT}/sql" \
  -H "Content-Type: application/json" \
  -u "${SURREALDB_USER}:${SURREALDB_PASS}" \
  -d "DEFINE NAMESPACE ${SURREALDB_NS};" | jq .

# Check if the namespace was created successfully
echo "Checking if namespace was created..."
curl -s -X POST "http://${SURREALDB_HOST}:${SURREALDB_PORT}/sql" \
  -H "Content-Type: application/json" \
  -u "${SURREALDB_USER}:${SURREALDB_PASS}" \
  -d "INFO FOR NS;" | jq .

# Create database in the namespace
echo "Creating database '${SURREALDB_DB}' in namespace '${SURREALDB_NS}'..."
curl -s -X POST "http://${SURREALDB_HOST}:${SURREALDB_PORT}/sql" \
  -H "Content-Type: application/json" \
  -H "NS: ${SURREALDB_NS}" \
  -u "${SURREALDB_USER}:${SURREALDB_PASS}" \
  -d "DEFINE DATABASE ${SURREALDB_DB};" | jq .

# Check databases in the namespace
echo "Checking databases in namespace '${SURREALDB_NS}'..."
curl -s -X POST "http://${SURREALDB_HOST}:${SURREALDB_PORT}/sql" \
  -H "Content-Type: application/json" \
  -H "NS: ${SURREALDB_NS}" \
  -u "${SURREALDB_USER}:${SURREALDB_PASS}" \
  -d "INFO FOR DB;" | jq .

# Define schema
echo "Defining schema in database '${SURREALDB_DB}'..."
curl -s -X POST "http://${SURREALDB_HOST}:${SURREALDB_PORT}/sql" \
  -H "Content-Type: application/json" \
  -H "NS: ${SURREALDB_NS}" \
  -H "DB: ${SURREALDB_DB}" \
  -u "${SURREALDB_USER}:${SURREALDB_PASS}" \
  -d "
  -- Define knowledge_item table
  DEFINE TABLE knowledge_item SCHEMAFULL;
  
  -- Define fields
  DEFINE FIELD title ON knowledge_item TYPE string;
  DEFINE FIELD content ON knowledge_item TYPE string;
  DEFINE FIELD source ON knowledge_item TYPE string;
  DEFINE FIELD source_type ON knowledge_item TYPE string;
  DEFINE FIELD content_type ON knowledge_item TYPE string;
  DEFINE FIELD tags ON knowledge_item TYPE array;
  DEFINE FIELD category ON knowledge_item TYPE string;
  DEFINE FIELD metadata ON knowledge_item TYPE object;
  DEFINE FIELD embedding ON knowledge_item TYPE array;
  DEFINE FIELD embedding_model ON knowledge_item TYPE string;
  DEFINE FIELD embedding_provider ON knowledge_item TYPE string;
  DEFINE FIELD embedding_requested ON knowledge_item TYPE bool DEFAULT false;
  DEFINE FIELD embedding_requested_at ON knowledge_item TYPE datetime;
  DEFINE FIELD created_at ON knowledge_item TYPE datetime;
  DEFINE FIELD updated_at ON knowledge_item TYPE datetime;
  
  -- Define indexes
  DEFINE INDEX knowledge_item_title ON knowledge_item FIELDS title;
  DEFINE INDEX knowledge_item_category ON knowledge_item FIELDS category;
  DEFINE INDEX knowledge_item_tags ON knowledge_item FIELDS tags;
  DEFINE INDEX knowledge_item_source ON knowledge_item FIELDS source;
  DEFINE INDEX knowledge_item_embedding_requested ON knowledge_item FIELDS embedding_requested;
  " | jq .

# Try a simple query
echo "Testing a simple query..."
curl -s -X POST "http://${SURREALDB_HOST}:${SURREALDB_PORT}/sql" \
  -H "Content-Type: application/json" \
  -H "NS: ${SURREALDB_NS}" \
  -H "DB: ${SURREALDB_DB}" \
  -u "${SURREALDB_USER}:${SURREALDB_PASS}" \
  -d "SELECT * FROM knowledge_item LIMIT 5;" | jq .

echo "Database check completed."