// Populate Knowledge Graph with Code Structure Data
// =================================================
// Run these in Neo4j Browser to add more code knowledge

// 1. ADD COMMON PYTHON FRAMEWORK CLASSES
// ======================================

// FastAPI classes and functions
CREATE (fastapi_app:Class {
    name: "FastAPI",
    full_name: "fastapi.FastAPI",
    module: "fastapi",
    methods_count: 15,
    created_at: datetime()
});

CREATE (fastapi_request:Class {
    name: "Request", 
    full_name: "fastapi.Request",
    module: "fastapi",
    methods_count: 8,
    created_at: datetime()
});

// Pydantic classes
CREATE (pydantic_model:Class {
    name: "BaseModel",
    full_name: "pydantic.BaseModel", 
    module: "pydantic",
    methods_count: 20,
    created_at: datetime()
});

// 2. ADD METHODS FOR THESE CLASSES
// ================================

// FastAPI methods
CREATE (get_method:Method {
    name: "get",
    full_name: "FastAPI.get",
    parameters: ["self", "path", "response_model", "status_code"],
    return_type: "Callable",
    visibility: "public",
    created_at: datetime()
});

CREATE (post_method:Method {
    name: "post", 
    full_name: "FastAPI.post",
    parameters: ["self", "path", "response_model", "status_code"],
    return_type: "Callable",
    visibility: "public",
    created_at: datetime()
});

// Pydantic methods
CREATE (model_validate:Method {
    name: "model_validate",
    full_name: "BaseModel.model_validate",
    parameters: ["cls", "obj"],
    return_type: "BaseModel",
    visibility: "public", 
    created_at: datetime()
});

// 3. ADD COMMON FUNCTIONS
// =======================

CREATE (parse_content_func:Function {
    name: "parse_content",
    full_name: "ptolemies.utils.parse_content",
    module: "ptolemies.utils",
    parameters: ["content", "format_type"],
    return_type: "Dict[str, Any]",
    created_at: datetime()
});

CREATE (crawl_source_func:Function {
    name: "crawl_source", 
    full_name: "ptolemies.crawler.crawl_source",
    module: "ptolemies.crawler",
    parameters: ["url", "max_depth"],
    return_type: "List[Dict]",
    created_at: datetime()
});

// 4. ADD FRAMEWORK-SPECIFIC KNOWLEDGE
// ===================================

// SurrealDB classes
CREATE (surreal_client:Class {
    name: "Surreal",
    full_name: "surrealdb.Surreal",
    module: "surrealdb", 
    methods_count: 12,
    created_at: datetime()
});

CREATE (surreal_connect:Method {
    name: "connect",
    full_name: "Surreal.connect", 
    parameters: ["self", "url"],
    return_type: "None",
    visibility: "public",
    created_at: datetime()
});

// Logfire functions
CREATE (logfire_info:Function {
    name: "info",
    full_name: "logfire.info",
    module: "logfire",
    parameters: ["message", "extra"],
    return_type: "None", 
    created_at: datetime()
});

// 5. CREATE RELATIONSHIPS
// =======================

// Link classes to methods
MATCH (fastapi:Class {name: "FastAPI"}), (get_m:Method {name: "get"})
CREATE (fastapi)-[:HAS_METHOD]->(get_m);

MATCH (fastapi:Class {name: "FastAPI"}), (post_m:Method {name: "post"})
CREATE (fastapi)-[:HAS_METHOD]->(post_m);

MATCH (pydantic:Class {name: "BaseModel"}), (validate_m:Method {name: "model_validate"})
CREATE (pydantic)-[:HAS_METHOD]->(validate_m);

MATCH (surreal:Class {name: "Surreal"}), (connect_m:Method {name: "connect"})
CREATE (surreal)-[:HAS_METHOD]->(connect_m);

// Link to frameworks
MATCH (fastapi_class:Class {name: "FastAPI"}), (fastapi_fw:Framework {name: "FastAPI"})
CREATE (fastapi_fw)-[:HAS_CLASS]->(fastapi_class);

MATCH (surreal_class:Class {name: "Surreal"}), (surrealdb_fw:Framework {name: "SurrealDB"})
CREATE (surrealdb_fw)-[:HAS_CLASS]->(surreal_class);

// 6. VERIFICATION QUERIES
// =======================

// Check all classes
MATCH (c:Class) 
RETURN c.name, c.full_name, c.module 
ORDER BY c.name;

// Check all methods
MATCH (m:Method) 
RETURN m.name, m.full_name, m.parameters 
ORDER BY m.name;

// Check all functions  
MATCH (f:Function)
RETURN f.name, f.full_name, f.module
ORDER BY f.name;