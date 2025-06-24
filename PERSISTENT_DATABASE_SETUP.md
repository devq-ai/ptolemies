# Ptolemies Persistent Database Setup Guide

## 🚨 Current Status Analysis

Based on the connection strings in `COMPLETE_QUERY_RESULTS.md`, your current setup is:

### SurrealDB: **EPHEMERAL** ⚠️
- **Connection**: `ws://localhost:8000/rpc`
- **Current Setup**: In-memory database (data lost on restart)
- **Status**: All 784 pages would be lost if server restarts

### Neo4j: **PERSISTENT** ✅
- **Connection**: `bolt://localhost:7687` 
- **Current Setup**: Neo4j Desktop (persistent to local machine)
- **Status**: Data survives restarts but tied to your desktop

### Redis: **EPHEMERAL** ⚠️
- **Connection**: `redis://localhost:6379`
- **Current Setup**: Default Redis (may or may not persist)
- **Status**: Cache data lost on restart (this is usually acceptable)

---

## 🔧 Making SurrealDB Persistent

### Option 1: File-Based Persistence (Recommended for Development)

**Stop current SurrealDB instance and restart with file storage:**

```bash
# Stop current instance (Ctrl+C if running in terminal)

# Start with file-based persistence
surreal start \
  --bind 0.0.0.0:8000 \
  --user root \
  --pass root \
  file:/Users/dionedge/devqai/ptolemies/data/surrealdb.db

# Or create a dedicated data directory
mkdir -p /Users/dionedge/devqai/ptolemies/database/surrealdb
surreal start \
  --bind 0.0.0.0:8000 \
  --user root \
  --pass root \
  file:/Users/dionedge/devqai/ptolemies/database/surrealdb/ptolemies.db
```

**Connection remains the same:**
```bash
export SURREALDB_URL="ws://localhost:8000/rpc"
```

### Option 2: Docker Persistent Setup

**Create persistent SurrealDB with Docker:**

```bash
# Create data directory
mkdir -p /Users/dionedge/devqai/ptolemies/database/surrealdb-data

# Run SurrealDB in Docker with persistent volume
docker run -d \
  --name ptolemies-surrealdb \
  -p 8000:8000 \
  -v /Users/dionedge/devqai/ptolemies/database/surrealdb-data:/data \
  surrealdb/surrealdb:latest \
  start \
  --bind 0.0.0.0:8000 \
  --user root \
  --pass root \
  file:/data/ptolemies.db
```

### Option 3: Production Cloud Setup

**SurrealDB Cloud (Recommended for Production):**

```bash
# Sign up at https://surrealdb.com/cloud
# Get your cloud instance URL and credentials

export SURREALDB_URL="wss://your-instance.surrealdb.cloud"
export SURREALDB_USERNAME="your-username"
export SURREALDB_PASSWORD="your-password"
export SURREALDB_DATABASE="ptolemies"
export SURREALDB_NAMESPACE="knowledge"
```

---

## 🔧 Neo4j Persistence Options

### Current Setup: Neo4j Desktop ✅
Your current setup with Neo4j Desktop is already persistent:

```bash
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="password"
```

**Data Location**: Check Neo4j Desktop for database location (usually in user directory)

### Option 1: Docker Persistent Setup

```bash
# Create data directory
mkdir -p /Users/dionedge/devqai/ptolemies/database/neo4j-data

# Run Neo4j in Docker with persistent volume
docker run -d \
  --name ptolemies-neo4j \
  -p 7474:7474 \
  -p 7687:7687 \
  -v /Users/dionedge/devqai/ptolemies/database/neo4j-data:/data \
  -e NEO4J_AUTH=neo4j/your-secure-password \
  -e NEO4J_dbms_default__database=ptolemies \
  neo4j:latest
```

### Option 2: Neo4j AuraDB (Cloud)

```bash
# Sign up at https://console.neo4j.io/
# Create a database instance

export NEO4J_URI="neo4j+s://your-instance.databases.neo4j.io"
export NEO4J_USERNAME="neo4j" 
export NEO4J_PASSWORD="your-generated-password"
export NEO4J_DATABASE="neo4j"  # Default for AuraDB
```

---

## 🔧 Redis Persistence Options

### Current Setup Analysis
Check if your Redis has persistence enabled:

```bash
# Connect to Redis and check config
redis-cli CONFIG GET save
redis-cli CONFIG GET dir
redis-cli CONFIG GET dbfilename
```

### Option 1: Enable Redis Persistence

```bash
# Edit Redis configuration
# Location varies by installation:
# - Homebrew: /usr/local/etc/redis.conf or /opt/homebrew/etc/redis.conf
# - Manual install: /etc/redis/redis.conf

# Add these lines to redis.conf:
save 900 1      # Save if at least 1 key changed in 900 seconds
save 300 10     # Save if at least 10 keys changed in 300 seconds  
save 60 10000   # Save if at least 10000 keys changed in 60 seconds

dir /Users/dionedge/devqai/ptolemies/database/redis-data
dbfilename ptolemies-cache.rdb

# Restart Redis
brew services restart redis
# or
sudo systemctl restart redis
```

### Option 2: Redis Docker with Persistence

```bash
# Create data directory
mkdir -p /Users/dionedge/devqai/ptolemies/database/redis-data

# Run Redis with persistence
docker run -d \
  --name ptolemies-redis \
  -p 6379:6379 \
  -v /Users/dionedge/devqai/ptolemies/database/redis-data:/data \
  redis:latest \
  redis-server --appendonly yes --dir /data
```

---

## ✅ Recommended Persistent Setup

### For Development (Local Machine)

**1. SurrealDB File-Based:**
```bash
# Create directory structure
mkdir -p /Users/dionedge/devqai/ptolemies/database/{surrealdb,neo4j,redis}

# Start SurrealDB with file persistence
surreal start \
  --bind 0.0.0.0:8000 \
  --user root \
  --pass root \
  file:/Users/dionedge/devqai/ptolemies/database/surrealdb/ptolemies.db
```

**2. Keep Neo4j Desktop (Already Persistent):**
```bash
# No changes needed - already persistent
export NEO4J_URI="bolt://localhost:7687"
```

**3. Redis with Basic Persistence:**
```bash
# Enable RDB snapshots in Redis config
save 900 1
save 300 10
save 60 10000
```

### For Production (Cloud/Server)

**1. SurrealDB Cloud:**
```bash
export SURREALDB_URL="wss://your-instance.surrealdb.cloud"
```

**2. Neo4j AuraDB:**
```bash
export NEO4J_URI="neo4j+s://your-instance.databases.neo4j.io"
```

**3. Upstash Redis:**
```bash
export UPSTASH_REDIS_REST_URL="https://your-instance.upstash.io"
export UPSTASH_REDIS_REST_TOKEN="your-token"
```

---

## 🚨 Immediate Action Required

**Your 784-page knowledge base is currently at risk!** The SurrealDB memory setup means:

1. **Data Loss Risk**: All embeddings lost if SurrealDB restarts
2. **No Backup**: In-memory data cannot be backed up
3. **No Recovery**: If the process crashes, you lose everything

### Quick Fix (Do This Now):

```bash
# 1. Stop current SurrealDB (Ctrl+C)

# 2. Create persistent directory  
mkdir -p /Users/dionedge/devqai/ptolemies/database/surrealdb

# 3. Start with file persistence
surreal start \
  --bind 0.0.0.0:8000 \
  --user root \
  --pass root \
  file:/Users/dionedge/devqai/ptolemies/database/surrealdb/ptolemies.db

# 4. Re-run your data loading scripts to populate the persistent database
```

---

## 🔍 How to Check Current Status

### Check SurrealDB Persistence:
```bash
# Connect to SurrealDB
surreal sql --conn ws://localhost:8000/rpc --user root --pass root --ns knowledge --db ptolemies

# Run this query to see if data exists:
SELECT count() FROM document_chunks;

# If you get 0 results, the in-memory data was lost
```

### Check Neo4j Data:
```bash
# Open Neo4j Browser: http://localhost:7474
# Or use cypher-shell:
cypher-shell -a bolt://localhost:7687 -u neo4j -p password

# Check data:
MATCH (n) RETURN count(n);
```

### Check Redis Data:
```bash
redis-cli
> DBSIZE
> KEYS ptolemies:*
```

---

## 💾 Backup Strategy

### Automated Backup Script:
```bash
#!/bin/bash
# backup-ptolemies.sh

BACKUP_DIR="/Users/dionedge/devqai/ptolemies/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# SurrealDB backup
surreal export \
  --conn ws://localhost:8000/rpc \
  --user root --pass root \
  --ns knowledge --db ptolemies \
  "$BACKUP_DIR/surrealdb_backup.surql"

# Neo4j backup (if using Docker)
docker exec ptolemies-neo4j neo4j-admin dump \
  --database=ptolemies \
  --to="/backups/neo4j_$(date +%Y%m%d_%H%M%S).dump"

# Redis backup
redis-cli --rdb "$BACKUP_DIR/redis_backup.rdb"

echo "Backup completed: $BACKUP_DIR"
```

**Make it executable and run weekly:**
```bash
chmod +x backup-ptolemies.sh
# Add to crontab for weekly backups:
# 0 2 * * 0 /path/to/backup-ptolemies.sh
```

---

## 🎯 Summary

**Current Risk Level**: 🚨 **HIGH** - SurrealDB data is ephemeral
**Immediate Action**: Switch to file-based SurrealDB persistence
**Long-term**: Consider cloud hosting for production reliability

Your Neo4j setup is already persistent, but SurrealDB needs immediate attention to preserve the 784-page knowledge base!