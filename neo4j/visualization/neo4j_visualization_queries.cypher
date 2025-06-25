# Neo4j Graph Visualization Queries
# ===================================

# Generated on: 2025-06-24T12:01:02.186831

# Framework Overview
# ------------------
MATCH (f:Framework)
            OPTIONAL MATCH (f)-[r1]->(c:Class)
            OPTIONAL MATCH (c)-[r2]->(m:Method)
            RETURN f.name as framework, 
                   count(DISTINCT c) as classes, 
                   count(DISTINCT m) as methods,
                   f.maturity_score as maturity
            ORDER BY maturity DESC;

# Framework Relationships
# -----------------------
MATCH (f1:Framework)-[r]->(f2:Framework)
            RETURN f1.name as source, 
                   type(r) as relationship, 
                   f2.name as target,
                   r.context as context;

# Class Inheritance Tree
# ----------------------
MATCH (c1:Class)-[r:INHERITS_FROM|COMPOSED_OF|EXTENDS]->(c2:Class)
            RETURN c1.name as child_class,
                   c1.module as child_module,
                   type(r) as relationship,
                   c2.name as parent_class,
                   c2.module as parent_module;

# Method Call Chains
# ------------------
MATCH (m1:Method)-[r:CALLS|IMPLEMENTS|USES]->(m2:Method)
            RETURN m1.full_name as calling_method,
                   type(r) as relationship,
                   m2.full_name as called_method,
                   r.context as context;

# Framework Ecosystem
# -------------------
MATCH (f:Framework)
            OPTIONAL MATCH (f)-[r1:HAS_CLASS]->(c:Class)
            OPTIONAL MATCH (c)-[r2:HAS_METHOD]->(m:Method)
            OPTIONAL MATCH (f)-[r3:HAS_FUNCTION]->(func:Function)
            RETURN f.name as framework,
                   collect(DISTINCT c.name) as classes,
                   collect(DISTINCT m.name) as methods,
                   collect(DISTINCT func.name) as functions,
                   f.type as framework_type;

# High Complexity Elements
# ------------------------
MATCH (m:Method)
            WHERE m.complexity_estimated = 'high'
            OPTIONAL MATCH (c:Class)-[:HAS_METHOD]->(m)
            OPTIONAL MATCH (f:Framework)-[:HAS_CLASS]->(c)
            RETURN f.name as framework,
                   c.name as class,
                   m.name as method,
                   m.parameter_count as params
            ORDER BY m.parameter_count DESC;

# Framework Integration Map
# -------------------------
MATCH (f1:Framework)-[r]->(f2:Framework)
            WHERE type(r) IN ['INTEGRATES_WITH', 'DEPENDS_ON', 'USES']
            RETURN f1.name as from_framework,
                   f2.name as to_framework,
                   type(r) as integration_type,
                   r.context as context;

# Code Search By Name
# -------------------
// Usage: Replace 'FastAPI' with your search term
            CALL db.index.fulltext.queryNodes('code_elements_search', 'FastAPI')
            YIELD node, score
            RETURN labels(node) as node_type,
                   node.name as name,
                   node.description as description,
                   score
            ORDER BY score DESC;

