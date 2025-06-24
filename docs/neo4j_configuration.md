# Neo4j Configuration for Ptolemies

## APOC Procedure Configuration

The Ptolemies system requires access to APOC procedures for graph database operations. Add the following configuration to your Neo4j configuration file:

### Configuration File Location
- **Neo4j Desktop**: Settings → Open Configuration
- **Docker**: Mount to `/var/lib/neo4j/conf/neo4j.conf`
- **Manual Installation**: `$NEO4J_HOME/conf/neo4j.conf`

### Required Configuration
```properties
# Enable APOC procedures for Ptolemies graph operations
dbms.security.procedures.unrestricted=,jwt.security.*,gds.*,apoc.*

# Optional: Additional APOC configurations
dbms.security.procedures.allowlist=,jwt.security.*,gds.*,apoc.*
apoc.export.file.enabled=true
apoc.import.file.enabled=true
```

### Restart Required
After adding these configurations, restart your Neo4j instance:

**Neo4j Desktop:**
1. Stop the database
2. Start the database

**Docker:**
```bash
docker restart neo4j
```

**Manual Installation:**
```bash
neo4j restart
```

### Verification
After restart, verify APOC is available:
```cypher
RETURN apoc.version()
```

## Ptolemies Graph Schema
The system will create the following node types:
- `DocumentNode`: Represents documentation sources
- `ConceptNode`: Represents extracted concepts
- `TopicNode`: Represents categorized topics

## Security Considerations
The APOC procedures are enabled specifically for:
- Schema metadata operations (`apoc.meta.schema`)
- Graph algorithms and utilities
- Data import/export functions

This configuration is safe for development and testing environments. For production, consider more restrictive settings based on your security requirements.