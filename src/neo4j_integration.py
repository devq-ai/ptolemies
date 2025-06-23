#!/usr/bin/env python3
"""
Neo4j Graph Relationships Integration for Ptolemies
Implements graph-based document relationships and concept mapping.
"""

import asyncio
import os
import json
import time
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime, UTC
from dataclasses import dataclass, asdict
from collections import defaultdict

import logfire
from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from neo4j.exceptions import ServiceUnavailable, ClientError

# Configure Logfire
logfire.configure(send_to_logfire=False)  # Configure appropriately for production

@dataclass
class DocumentNode:
    """Represents a document node in the graph."""
    id: str
    source_name: str
    source_url: str
    title: str
    content_hash: str
    chunk_count: int
    quality_score: float
    topics: List[str]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

@dataclass
class ConceptNode:
    """Represents a concept extracted from documents."""
    name: str
    category: str
    description: str
    frequency: int
    confidence_score: float
    related_topics: List[str]

@dataclass
class Relationship:
    """Represents a relationship between nodes."""
    from_node: str
    to_node: str
    relationship_type: str
    strength: float
    properties: Dict[str, Any]

@dataclass
class GraphSearchResult:
    """Represents a graph search result."""
    nodes: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    paths: List[Dict[str, Any]]
    query_metadata: Dict[str, Any]

@dataclass
class Neo4jConfig:
    """Configuration for Neo4j connection."""
    uri: str = "bolt://localhost:7687"
    username: str = "neo4j"
    password: str = "password"
    database: str = "ptolemies"
    max_connection_lifetime: int = 3600
    max_connection_pool_size: int = 50
    connection_acquisition_timeout: int = 60

class Neo4jGraphStore:
    """Neo4j graph storage implementation for document relationships."""
    
    def __init__(self, config: Neo4jConfig = None):
        self.config = config or Neo4jConfig()
        self.driver: Optional[AsyncDriver] = None
        self._initialize_config()
    
    @logfire.instrument("neo4j_graph_initialize")
    def _initialize_config(self):
        """Initialize Neo4j configuration from environment."""
        with logfire.span("Initializing Neo4j graph store config"):
            logfire.info("Initializing Neo4j graph store")
            
            # Override config from environment
            self.config.uri = os.getenv("NEO4J_URI", self.config.uri)
            self.config.username = os.getenv("NEO4J_USERNAME", self.config.username)
            self.config.password = os.getenv("NEO4J_PASSWORD", self.config.password)
            self.config.database = os.getenv("NEO4J_DATABASE", self.config.database)
            
            logfire.info("Neo4j config initialized", 
                        uri=self.config.uri, 
                        username=self.config.username,
                        database=self.config.database)
    
    @logfire.instrument("neo4j_connect")
    async def connect(self) -> bool:
        """Connect to Neo4j database."""
        try:
            with logfire.span("Connecting to Neo4j"):
                logfire.info("Connecting to Neo4j", uri=self.config.uri)
                
                self.driver = AsyncGraphDatabase.driver(
                    self.config.uri,
                    auth=(self.config.username, self.config.password),
                    max_connection_lifetime=self.config.max_connection_lifetime,
                    max_connection_pool_size=self.config.max_connection_pool_size,
                    connection_acquisition_timeout=self.config.connection_acquisition_timeout
                )
                
                # Test connection
                await self.driver.verify_connectivity()
                
                # Initialize schema
                await self._initialize_schema()
                
                logfire.info("Neo4j connected successfully")
                return True
                
        except ServiceUnavailable as e:
            logfire.error("Neo4j service unavailable", error=str(e))
            self.driver = None
            return False
        except Exception as e:
            logfire.error("Failed to connect to Neo4j", error=str(e))
            self.driver = None
            return False
    
    @logfire.instrument("neo4j_schema_init")
    async def _initialize_schema(self):
        """Initialize Neo4j schema with constraints and indexes."""
        if not self.driver:
            raise RuntimeError("Not connected to Neo4j")
        
        with logfire.span("Initializing Neo4j schema"):
            try:
                async with self.driver.session(database=self.config.database) as session:
                    # Create constraints
                    constraints = [
                        "CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
                        "CREATE CONSTRAINT concept_name_unique IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE",
                        "CREATE CONSTRAINT topic_name_unique IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE"
                    ]
                    
                    # Create indexes
                    indexes = [
                        "CREATE INDEX document_source_idx IF NOT EXISTS FOR (d:Document) ON (d.source_name)",
                        "CREATE INDEX document_quality_idx IF NOT EXISTS FOR (d:Document) ON (d.quality_score)",
                        "CREATE INDEX concept_category_idx IF NOT EXISTS FOR (c:Concept) ON (c.category)",
                        "CREATE INDEX concept_frequency_idx IF NOT EXISTS FOR (c:Concept) ON (c.frequency)",
                        "CREATE INDEX relationship_strength_idx IF NOT EXISTS FOR ()-[r:RELATES_TO]-() ON (r.strength)"
                    ]
                    
                    all_queries = constraints + indexes
                    
                    for query in all_queries:
                        try:
                            await session.run(query)
                            logfire.debug("Schema query executed", query=query[:50])
                        except ClientError as e:
                            if "already exists" not in str(e).lower():
                                logfire.warning("Schema query failed", query=query[:50], error=str(e))
                    
                    logfire.info("Neo4j schema initialized successfully")
                    
            except Exception as e:
                logfire.error("Failed to initialize schema", error=str(e))
                raise
    
    @logfire.instrument("create_document_node")
    async def create_document_node(self, document: DocumentNode) -> bool:
        """Create or update a document node in the graph."""
        if not self.driver:
            raise RuntimeError("Not connected to Neo4j")
        
        with logfire.span("Creating document node", document_id=document.id):
            try:
                logfire.info("Creating document node", 
                           document_id=document.id,
                           source_name=document.source_name,
                           quality_score=document.quality_score)
                
                now = datetime.now(UTC).isoformat()
                document.updated_at = now
                if not document.created_at:
                    document.created_at = now
                
                async with self.driver.session(database=self.config.database) as session:
                    query = """
                    MERGE (d:Document {id: $id})
                    SET d.source_name = $source_name,
                        d.source_url = $source_url,
                        d.title = $title,
                        d.content_hash = $content_hash,
                        d.chunk_count = $chunk_count,
                        d.quality_score = $quality_score,
                        d.topics = $topics,
                        d.created_at = $created_at,
                        d.updated_at = $updated_at
                    RETURN d.id as document_id
                    """
                    
                    result = await session.run(query, **asdict(document))
                    record = await result.single()
                    
                    if record:
                        logfire.info("Document node created successfully", 
                                   document_id=record["document_id"])
                        return True
                    else:
                        logfire.warning("No record returned for document creation")
                        return False
                        
            except Exception as e:
                logfire.error("Failed to create document node", 
                            document_id=document.id, 
                            error=str(e))
                return False
    
    @logfire.instrument("create_concept_node")
    async def create_concept_node(self, concept: ConceptNode) -> bool:
        """Create or update a concept node in the graph."""
        if not self.driver:
            raise RuntimeError("Not connected to Neo4j")
        
        with logfire.span("Creating concept node", concept_name=concept.name):
            try:
                logfire.info("Creating concept node", 
                           concept_name=concept.name,
                           category=concept.category,
                           frequency=concept.frequency)
                
                async with self.driver.session(database=self.config.database) as session:
                    query = """
                    MERGE (c:Concept {name: $name})
                    SET c.category = $category,
                        c.description = $description,
                        c.frequency = $frequency,
                        c.confidence_score = $confidence_score,
                        c.related_topics = $related_topics
                    RETURN c.name as concept_name
                    """
                    
                    result = await session.run(query, **asdict(concept))
                    record = await result.single()
                    
                    if record:
                        logfire.info("Concept node created successfully", 
                                   concept_name=record["concept_name"])
                        return True
                    else:
                        logfire.warning("No record returned for concept creation")
                        return False
                        
            except Exception as e:
                logfire.error("Failed to create concept node", 
                            concept_name=concept.name, 
                            error=str(e))
                return False
    
    @logfire.instrument("create_relationship")
    async def create_relationship(self, relationship: Relationship) -> bool:
        """Create a relationship between two nodes."""
        if not self.driver:
            raise RuntimeError("Not connected to Neo4j")
        
        with logfire.span("Creating relationship", 
                         from_node=relationship.from_node,
                         to_node=relationship.to_node,
                         rel_type=relationship.relationship_type):
            try:
                logfire.info("Creating relationship", 
                           from_node=relationship.from_node,
                           to_node=relationship.to_node,
                           relationship_type=relationship.relationship_type,
                           strength=relationship.strength)
                
                async with self.driver.session(database=self.config.database) as session:
                    # Build properties string for the relationship
                    properties_str = ", ".join([f"{k}: ${k}" for k in relationship.properties.keys()])
                    if properties_str:
                        properties_str = f", {properties_str}"
                    
                    query = f"""
                    MATCH (from_node), (to_node)
                    WHERE from_node.id = $from_node OR from_node.name = $from_node
                    AND (to_node.id = $to_node OR to_node.name = $to_node)
                    MERGE (from_node)-[r:{relationship.relationship_type} {{strength: $strength{properties_str}}}]->(to_node)
                    RETURN type(r) as relationship_type
                    """
                    
                    params = {
                        "from_node": relationship.from_node,
                        "to_node": relationship.to_node,
                        "strength": relationship.strength,
                        **relationship.properties
                    }
                    
                    result = await session.run(query, params)
                    record = await result.single()
                    
                    if record:
                        logfire.info("Relationship created successfully", 
                                   relationship_type=record["relationship_type"])
                        return True
                    else:
                        logfire.warning("No record returned for relationship creation")
                        return False
                        
            except Exception as e:
                logfire.error("Failed to create relationship", 
                            from_node=relationship.from_node,
                            to_node=relationship.to_node,
                            error=str(e))
                return False
    
    @logfire.instrument("extract_concepts_from_document")
    async def extract_concepts_from_document(
        self, 
        document: DocumentNode,
        content_chunks: List[str]
    ) -> List[ConceptNode]:
        """Extract concepts from document content."""
        with logfire.span("Extracting concepts from document", document_id=document.id):
            try:
                logfire.info("Extracting concepts", 
                           document_id=document.id,
                           chunk_count=len(content_chunks))
                
                concepts = []
                concept_frequency = defaultdict(int)
                
                # Simple concept extraction based on topics and keywords
                # In production, this would use NLP/ML models
                all_text = " ".join(content_chunks).lower()
                
                # Extract concepts from document topics
                for topic in document.topics:
                    concept_frequency[topic.lower()] += 10  # Higher weight for explicit topics
                
                # Extract common technical concepts
                technical_concepts = {
                    "api": "Application Programming Interface",
                    "database": "Data storage system",
                    "framework": "Software development framework",
                    "authentication": "User verification system",
                    "middleware": "Software layer between applications",
                    "endpoint": "API access point",
                    "query": "Data retrieval operation",
                    "schema": "Data structure definition",
                    "integration": "System connection method",
                    "monitoring": "System observation and tracking"
                }
                
                for concept, description in technical_concepts.items():
                    if concept in all_text:
                        frequency = all_text.count(concept)
                        concept_frequency[concept] += frequency
                        
                        if concept_frequency[concept] >= 2:  # Minimum threshold
                            concepts.append(ConceptNode(
                                name=concept.title(),
                                category="Technical",
                                description=description,
                                frequency=concept_frequency[concept],
                                confidence_score=min(0.9, concept_frequency[concept] / 10),
                                related_topics=document.topics
                            ))
                
                # Extract framework-specific concepts
                framework_concepts = {
                    "fastapi": ("FastAPI", "Modern Python web framework"),
                    "logfire": ("Logfire", "Observability and monitoring platform"),
                    "surrealdb": ("SurrealDB", "Multi-model database"),
                    "neo4j": ("Neo4j", "Graph database platform"),
                    "pytest": ("PyTest", "Python testing framework"),
                    "redis": ("Redis", "In-memory data structure store")
                }
                
                for keyword, (name, description) in framework_concepts.items():
                    if keyword in all_text:
                        frequency = all_text.count(keyword)
                        if frequency >= 1:
                            concepts.append(ConceptNode(
                                name=name,
                                category="Framework",
                                description=description,
                                frequency=frequency,
                                confidence_score=min(0.95, frequency / 5),
                                related_topics=document.topics
                            ))
                
                logfire.info("Concepts extracted successfully", 
                           document_id=document.id,
                           concepts_found=len(concepts))
                
                return concepts
                
            except Exception as e:
                logfire.error("Failed to extract concepts", 
                            document_id=document.id, 
                            error=str(e))
                return []
    
    @logfire.instrument("build_document_relationships")
    async def build_document_relationships(
        self, 
        documents: List[DocumentNode]
    ) -> List[Relationship]:
        """Build relationships between documents based on content similarity."""
        with logfire.span("Building document relationships", document_count=len(documents)):
            try:
                logfire.info("Building document relationships", document_count=len(documents))
                
                relationships = []
                
                # Create relationships based on shared topics
                for i, doc1 in enumerate(documents):
                    for j, doc2 in enumerate(documents[i+1:], i+1):
                        shared_topics = set(doc1.topics) & set(doc2.topics)
                        
                        if shared_topics:
                            # Calculate relationship strength based on shared topics
                            topic_overlap = len(shared_topics) / max(len(doc1.topics), len(doc2.topics))
                            
                            # Consider quality scores in relationship strength
                            quality_factor = (doc1.quality_score + doc2.quality_score) / 2
                            strength = topic_overlap * quality_factor
                            
                            if strength >= 0.3:  # Minimum threshold
                                relationships.append(Relationship(
                                    from_node=doc1.id,
                                    to_node=doc2.id,
                                    relationship_type="RELATED_TO",
                                    strength=round(strength, 3),
                                    properties={
                                        "shared_topics": list(shared_topics),
                                        "topic_overlap": round(topic_overlap, 3),
                                        "quality_factor": round(quality_factor, 3)
                                    }
                                ))
                
                # Create relationships based on same source
                source_groups = defaultdict(list)
                for doc in documents:
                    source_groups[doc.source_name].append(doc)
                
                for source_name, source_docs in source_groups.items():
                    if len(source_docs) > 1:
                        # Create PART_OF relationships within same source
                        for i, doc1 in enumerate(source_docs):
                            for doc2 in source_docs[i+1:]:
                                relationships.append(Relationship(
                                    from_node=doc1.id,
                                    to_node=doc2.id,
                                    relationship_type="PART_OF_SAME_SOURCE",
                                    strength=0.8,
                                    properties={
                                        "source_name": source_name,
                                        "relationship_basis": "same_source"
                                    }
                                ))
                
                logfire.info("Document relationships built successfully", 
                           relationships_created=len(relationships))
                
                return relationships
                
            except Exception as e:
                logfire.error("Failed to build document relationships", error=str(e))
                return []
    
    @logfire.instrument("graph_search")
    async def graph_search(
        self,
        query: str,
        search_type: str = "concept",
        max_depth: int = 3,
        limit: int = 20
    ) -> GraphSearchResult:
        """Perform graph-based search for documents and concepts."""
        if not self.driver:
            raise RuntimeError("Not connected to Neo4j")
        
        with logfire.span("Graph search", query=query[:100], search_type=search_type):
            try:
                start_time = time.time()
                logfire.info("Starting graph search", 
                           query_length=len(query),
                           search_type=search_type,
                           max_depth=max_depth,
                           limit=limit)
                
                async with self.driver.session(database=self.config.database) as session:
                    nodes = []
                    relationships = []
                    paths = []
                    
                    if search_type == "concept":
                        # Search for concepts and related documents
                        concept_query = """
                        MATCH (c:Concept)
                        WHERE c.name CONTAINS $query OR c.description CONTAINS $query
                        OPTIONAL MATCH (c)-[r]-(related)
                        RETURN c, collect(distinct r) as rels, collect(distinct related) as related_nodes
                        LIMIT $limit
                        """
                        
                        result = await session.run(concept_query, query=query, limit=limit)
                        async for record in result:
                            concept = record["c"]
                            nodes.append(dict(concept))
                            
                            for rel in record["rels"]:
                                if rel:
                                    relationships.append({
                                        "type": rel.type,
                                        "properties": dict(rel)
                                    })
                            
                            for related in record["related_nodes"]:
                                if related:
                                    nodes.append(dict(related))
                    
                    elif search_type == "document":
                        # Search for documents and their relationships
                        doc_query = """
                        MATCH (d:Document)
                        WHERE d.title CONTAINS $query OR d.source_name CONTAINS $query
                           OR any(topic IN d.topics WHERE topic CONTAINS $query)
                        OPTIONAL MATCH path = (d)-[*1..$max_depth]-(related)
                        RETURN d, collect(distinct nodes(path)) as path_nodes, 
                               collect(distinct relationships(path)) as path_rels
                        ORDER BY d.quality_score DESC
                        LIMIT $limit
                        """
                        
                        result = await session.run(doc_query, 
                                                 query=query, 
                                                 max_depth=max_depth,
                                                 limit=limit)
                        async for record in result:
                            document = record["d"]
                            nodes.append(dict(document))
                            
                            # Add path information
                            if record["path_nodes"]:
                                path_data = {
                                    "length": len(record["path_nodes"]),
                                    "nodes": [dict(node) for node in record["path_nodes"] if node],
                                    "relationships": [dict(rel) for rel in record["path_rels"] if rel]
                                }
                                paths.append(path_data)
                                
                                # Add unique nodes and relationships
                                for node in record["path_nodes"]:
                                    if node:
                                        nodes.append(dict(node))
                                
                                for rel in record["path_rels"]:
                                    if rel:
                                        relationships.append({
                                            "type": rel.type,
                                            "properties": dict(rel)
                                        })
                    
                    elif search_type == "path":
                        # Find paths between concepts/documents
                        path_query = """
                        MATCH (start), (end)
                        WHERE (start.name CONTAINS $query OR start.title CONTAINS $query)
                          AND (end.name CONTAINS $query OR end.title CONTAINS $query)
                          AND id(start) <> id(end)
                        MATCH path = shortestPath((start)-[*1..$max_depth]-(end))
                        RETURN path
                        LIMIT $limit
                        """
                        
                        result = await session.run(path_query, 
                                                 query=query,
                                                 max_depth=max_depth,
                                                 limit=limit)
                        async for record in result:
                            path = record["path"]
                            path_data = {
                                "length": len(path.nodes),
                                "nodes": [dict(node) for node in path.nodes],
                                "relationships": [{"type": rel.type, "properties": dict(rel)} 
                                               for rel in path.relationships]
                            }
                            paths.append(path_data)
                            
                            # Add nodes and relationships to main collections
                            for node in path.nodes:
                                nodes.append(dict(node))
                            for rel in path.relationships:
                                relationships.append({
                                    "type": rel.type,
                                    "properties": dict(rel)
                                })
                    
                    # Remove duplicates
                    unique_nodes = []
                    seen_node_ids = set()
                    for node in nodes:
                        node_id = node.get("id") or node.get("name")
                        if node_id and node_id not in seen_node_ids:
                            unique_nodes.append(node)
                            seen_node_ids.add(node_id)
                    
                    search_time = time.time() - start_time
                    
                    query_metadata = {
                        "search_type": search_type,
                        "query": query,
                        "max_depth": max_depth,
                        "limit": limit,
                        "search_time_ms": round(search_time * 1000, 2),
                        "nodes_found": len(unique_nodes),
                        "relationships_found": len(relationships),
                        "paths_found": len(paths)
                    }
                    
                    logfire.info("Graph search completed", 
                               search_type=search_type,
                               nodes_found=len(unique_nodes),
                               relationships_found=len(relationships),
                               paths_found=len(paths),
                               search_time_ms=query_metadata["search_time_ms"])
                    
                    return GraphSearchResult(
                        nodes=unique_nodes,
                        relationships=relationships,
                        paths=paths,
                        query_metadata=query_metadata
                    )
                    
            except Exception as e:
                logfire.error("Graph search failed", error=str(e))
                raise
    
    @logfire.instrument("get_graph_stats")
    async def get_graph_stats(self) -> Dict[str, Any]:
        """Get graph database statistics."""
        if not self.driver:
            raise RuntimeError("Not connected to Neo4j")
        
        with logfire.span("Get graph statistics"):
            try:
                async with self.driver.session(database=self.config.database) as session:
                    stats_queries = [
                        "MATCH (d:Document) RETURN count(d) as document_count",
                        "MATCH (c:Concept) RETURN count(c) as concept_count",
                        "MATCH ()-[r]->() RETURN count(r) as relationship_count",
                        "MATCH (d:Document) RETURN avg(d.quality_score) as avg_quality",
                        "MATCH ()-[r:RELATED_TO]->() RETURN avg(r.strength) as avg_relationship_strength"
                    ]
                    
                    stats = {}
                    
                    # Document count
                    result = await session.run(stats_queries[0])
                    record = await result.single()
                    stats["document_count"] = record["document_count"] if record else 0
                    
                    # Concept count
                    result = await session.run(stats_queries[1])
                    record = await result.single()
                    stats["concept_count"] = record["concept_count"] if record else 0
                    
                    # Relationship count
                    result = await session.run(stats_queries[2])
                    record = await result.single()
                    stats["relationship_count"] = record["relationship_count"] if record else 0
                    
                    # Average quality
                    result = await session.run(stats_queries[3])
                    record = await result.single()
                    stats["average_quality"] = round(record["avg_quality"], 3) if record and record["avg_quality"] else 0.0
                    
                    # Average relationship strength
                    result = await session.run(stats_queries[4])
                    record = await result.single()
                    stats["average_relationship_strength"] = round(record["avg_relationship_strength"], 3) if record and record["avg_relationship_strength"] else 0.0
                    
                    # Additional metrics
                    stats["database"] = self.config.database
                    stats["connected"] = True
                    
                    logfire.info("Graph statistics retrieved", stats=stats)
                    return stats
                    
            except Exception as e:
                logfire.error("Failed to get graph statistics", error=str(e))
                raise
    
    @logfire.instrument("neo4j_close")
    async def close(self):
        """Close Neo4j connection."""
        if self.driver:
            with logfire.span("Closing Neo4j connection"):
                await self.driver.close()
                self.driver = None
                logfire.info("Neo4j connection closed")

# Utility functions for integration
async def create_graph_store(config: Neo4jConfig = None) -> Neo4jGraphStore:
    """Create and connect to Neo4j graph store."""
    store = Neo4jGraphStore(config)
    connected = await store.connect()
    if not connected:
        raise RuntimeError("Failed to connect to Neo4j graph store")
    return store

async def migrate_documents_to_graph(
    graph_store: Neo4jGraphStore,
    documents: List[Dict[str, Any]],
    extract_concepts: bool = True
) -> bool:
    """Migrate document data to graph format with relationships."""
    try:
        # Convert to DocumentNode objects
        document_nodes = []
        for doc_data in documents:
            doc_node = DocumentNode(
                id=doc_data.get("id", f"doc_{len(document_nodes)}"),
                source_name=doc_data.get("source_name", "Unknown"),
                source_url=doc_data.get("source_url", ""),
                title=doc_data.get("title", "Untitled"),
                content_hash=doc_data.get("content_hash", ""),
                chunk_count=doc_data.get("chunk_count", 1),
                quality_score=doc_data.get("quality_score", 0.5),
                topics=doc_data.get("topics", [])
            )
            document_nodes.append(doc_node)
        
        # Create document nodes
        for doc_node in document_nodes:
            await graph_store.create_document_node(doc_node)
        
        # Extract and create concepts if requested
        if extract_concepts:
            all_concepts = []
            for doc_node in document_nodes:
                content_chunks = [doc_data.get("content", "") for doc_data in documents 
                                if doc_data.get("id") == doc_node.id]
                concepts = await graph_store.extract_concepts_from_document(doc_node, content_chunks)
                all_concepts.extend(concepts)
                
                # Create concept nodes and relationships
                for concept in concepts:
                    await graph_store.create_concept_node(concept)
                    
                    # Create relationship between document and concept
                    relationship = Relationship(
                        from_node=doc_node.id,
                        to_node=concept.name,
                        relationship_type="CONTAINS_CONCEPT",
                        strength=concept.confidence_score,
                        properties={
                            "frequency": concept.frequency,
                            "category": concept.category
                        }
                    )
                    await graph_store.create_relationship(relationship)
        
        # Build relationships between documents
        relationships = await graph_store.build_document_relationships(document_nodes)
        for relationship in relationships:
            await graph_store.create_relationship(relationship)
        
        return True
        
    except Exception as e:
        logfire.error("Failed to migrate documents to graph", error=str(e))
        return False

if __name__ == "__main__":
    # Example usage
    async def main():
        config = Neo4jConfig()
        store = await create_graph_store(config)
        
        # Example search
        results = await store.graph_search("FastAPI authentication", search_type="concept")
        print(f"Found {len(results.nodes)} nodes and {len(results.relationships)} relationships")
        
        await store.close()
    
    asyncio.run(main())