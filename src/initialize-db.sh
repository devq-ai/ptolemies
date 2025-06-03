#!/bin/bash
# Initialize SurrealDB for Ptolemies Knowledge Base

# Define color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===== Initializing Ptolemies Knowledge Base =====${NC}"
echo ""

# SurrealDB connection details
SURREALDB_HOST="localhost"
SURREALDB_PORT="8000"
SURREALDB_USER="root"
SURREALDB_PASS="root"
SURREALDB_NS="ptolemies"
SURREALDB_DB="knowledge"

# Check if SurrealDB is running
if ! curl -s "http://${SURREALDB_HOST}:${SURREALDB_PORT}/health" > /dev/null; then
  echo -e "${RED}Error: SurrealDB is not running!${NC}"
  echo "Please start SurrealDB first with:"
  echo "surreal start --log info --user root --pass root --bind 0.0.0.0:8000 memory"
  exit 1
fi

echo -e "${GREEN}SurrealDB is running.${NC}"

# Create namespace and database
echo -e "${YELLOW}Creating namespace and database...${NC}"
curl -s -X POST "http://${SURREALDB_HOST}:${SURREALDB_PORT}/sql" \
  -H "Content-Type: application/json" \
  -u "${SURREALDB_USER}:${SURREALDB_PASS}" \
  -d "DEFINE NAMESPACE ${SURREALDB_NS};" > /dev/null

curl -s -X POST "http://${SURREALDB_HOST}:${SURREALDB_PORT}/sql" \
  -H "Content-Type: application/json" \
  -H "NS: ${SURREALDB_NS}" \
  -u "${SURREALDB_USER}:${SURREALDB_PASS}" \
  -d "DEFINE DATABASE ${SURREALDB_DB};" > /dev/null

echo -e "${GREEN}Namespace and database created.${NC}"

# Define schema
echo -e "${YELLOW}Defining schema...${NC}"
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
  
  -- Vector index (for when embeddings are added)
  DEFINE VECTOR INDEX knowledge_item_embedding ON knowledge_item FIELDS embedding
    DIMENSION 1536
    METRIC cosine;
  " > /dev/null

echo -e "${GREEN}Schema defined.${NC}"
echo -e "${GREEN}Database initialization complete!${NC}"
echo ""
echo -e "${BLUE}You can now start adding knowledge items to the database.${NC}"
echo -e "${BLUE}Use the run-crawler.sh script to crawl web content.${NC}"