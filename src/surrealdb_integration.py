#!/usr/bin/env python3
"""
SurrealDB Vector Storage Integration for Ptolemies
Implements vector storage with OpenAI embeddings for semantic search capabilities.
"""

import asyncio
import os
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, UTC
from dataclasses import dataclass, asdict

import openai
import numpy as np
import logfire
from surrealdb import Surreal

# Configure Logfire
logfire.configure(send_to_logfire=False)  # Configure appropriately for production

@dataclass
class DocumentChunk:
    """Represents a chunk of document content with metadata."""
    id: str
    source_name: str
    source_url: str
    title: str
    content: str
    chunk_index: int
    total_chunks: int
    quality_score: float
    topics: List[str]
    embedding: Optional[List[float]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

@dataclass
class SearchResult:
    """Represents a search result with similarity score."""
    document: DocumentChunk
    similarity_score: float
    rank: int

@dataclass
class VectorStoreConfig:
    """Configuration for SurrealDB vector storage."""
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    similarity_threshold: float = 0.7
    max_results: int = 50
    batch_size: int = 100

class SurrealDBVectorStore:
    """SurrealDB vector storage implementation with OpenAI embeddings."""
    
    def __init__(self, config: VectorStoreConfig = None):
        self.config = config or VectorStoreConfig()
        self.db: Optional[Surreal] = None
        self.openai_client = None
        self._initialize_clients()
    
    @logfire.instrument("surrealdb_vector_initialize")
    def _initialize_clients(self):
        """Initialize SurrealDB and OpenAI clients."""
        with logfire.span("Initializing vector store clients"):
            logfire.info("Initializing SurrealDB vector store")
            
            # Initialize OpenAI client
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logfire.warning("OPENAI_API_KEY not found - embeddings will be disabled")
            else:
                self.openai_client = openai.OpenAI(api_key=api_key)
                logfire.info("OpenAI client initialized", model=self.config.embedding_model)
    
    @logfire.instrument("surrealdb_connect")
    async def connect(self) -> bool:
        """Connect to SurrealDB."""
        try:
            with logfire.span("Connecting to SurrealDB"):
                url = os.getenv("SURREALDB_URL", "ws://localhost:8000/rpc")
                username = os.getenv("SURREALDB_USERNAME", "root")
                password = os.getenv("SURREALDB_PASSWORD", "root")
                namespace = os.getenv("SURREALDB_NAMESPACE", "ptolemies")
                database = os.getenv("SURREALDB_DATABASE", "knowledge")
                
                logfire.info("Connecting to SurrealDB", url=url, username=username, namespace=namespace, database=database)
                
                self.db = Surreal()
                await self.db.connect(url)
                await self.db.signin({"user": username, "pass": password})
                await self.db.use(namespace, database)
                
                # Initialize schema
                await self._initialize_schema()
                
                logfire.info("SurrealDB connected successfully")
                return True
                
        except Exception as e:
            logfire.error("Failed to connect to SurrealDB", error=str(e))
            self.db = None  # Ensure db is None on failure
            return False
    
    @logfire.instrument("surrealdb_schema_init")
    async def _initialize_schema(self):
        """Initialize SurrealDB schema for vector storage."""
        with logfire.span("Initializing SurrealDB schema"):
            try:
                # Create document_chunks table with vector index
                schema_queries = [
                    """
                    DEFINE TABLE document_chunks SCHEMAFULL;
                    """,
                    """
                    DEFINE FIELD id ON document_chunks TYPE string;
                    DEFINE FIELD source_name ON document_chunks TYPE string;
                    DEFINE FIELD source_url ON document_chunks TYPE string;
                    DEFINE FIELD title ON document_chunks TYPE string;
                    DEFINE FIELD content ON document_chunks TYPE string;
                    DEFINE FIELD chunk_index ON document_chunks TYPE int;
                    DEFINE FIELD total_chunks ON document_chunks TYPE int;
                    DEFINE FIELD quality_score ON document_chunks TYPE float;
                    DEFINE FIELD topics ON document_chunks TYPE array<string>;
                    DEFINE FIELD embedding ON document_chunks TYPE array<float>;
                    DEFINE FIELD created_at ON document_chunks TYPE datetime;
                    DEFINE FIELD updated_at ON document_chunks TYPE datetime;
                    """,
                    """
                    DEFINE INDEX idx_source_name ON document_chunks COLUMNS source_name;
                    DEFINE INDEX idx_quality_score ON document_chunks COLUMNS quality_score;
                    DEFINE INDEX idx_topics ON document_chunks COLUMNS topics;
                    """
                ]
                
                for query in schema_queries:
                    await self.db.query(query)
                
                logfire.info("SurrealDB schema initialized successfully")
                
            except Exception as e:
                logfire.error("Failed to initialize schema", error=str(e))
                raise
    
    @logfire.instrument("generate_embeddings")
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts using OpenAI."""
        if not self.openai_client:
            logfire.warning("OpenAI client not available - returning zero embeddings")
            return [[0.0] * self.config.embedding_dimensions for _ in texts]
        
        with logfire.span("Generating embeddings", text_count=len(texts)):
            try:
                logfire.info("Generating embeddings", 
                           text_count=len(texts), 
                           model=self.config.embedding_model)
                
                # Process in batches to avoid rate limits
                embeddings = []
                for i in range(0, len(texts), self.config.batch_size):
                    batch = texts[i:i + self.config.batch_size]
                    
                    response = await asyncio.to_thread(
                        self.openai_client.embeddings.create,
                        input=batch,
                        model=self.config.embedding_model
                    )
                    
                    batch_embeddings = [data.embedding for data in response.data]
                    embeddings.extend(batch_embeddings)
                    
                    logfire.info("Processed embedding batch", 
                               batch_size=len(batch), 
                               total_processed=len(embeddings))
                
                logfire.info("Embeddings generated successfully", total_count=len(embeddings))
                return embeddings
                
            except Exception as e:
                logfire.error("Failed to generate embeddings", error=str(e))
                raise
    
    @logfire.instrument("store_document_chunks")
    async def store_document_chunks(self, chunks: List[DocumentChunk]) -> bool:
        """Store document chunks with embeddings in SurrealDB."""
        if not self.db:
            raise RuntimeError("Not connected to SurrealDB")
        
        with logfire.span("Storing document chunks", chunk_count=len(chunks)):
            try:
                logfire.info("Starting document chunk storage", chunk_count=len(chunks))
                
                # Generate embeddings for all chunks
                texts = [chunk.content for chunk in chunks]
                embeddings = await self.generate_embeddings(texts)
                
                # Prepare chunks with embeddings and timestamps
                now = datetime.now(UTC).isoformat()
                stored_chunks = []
                
                for i, chunk in enumerate(chunks):
                    chunk.embedding = embeddings[i]
                    chunk.created_at = now
                    chunk.updated_at = now
                    
                    # Convert to dict for SurrealDB
                    chunk_data = asdict(chunk)
                    chunk_data["id"] = f"document_chunks:{chunk.id}"
                    
                    stored_chunks.append(chunk_data)
                
                # Store in batches
                success_count = 0
                for i in range(0, len(stored_chunks), self.config.batch_size):
                    batch = stored_chunks[i:i + self.config.batch_size]
                    
                    for chunk_data in batch:
                        await self.db.create("document_chunks", chunk_data)
                        success_count += 1
                    
                    logfire.info("Stored chunk batch", 
                               batch_size=len(batch), 
                               total_stored=success_count)
                
                logfire.info("Document chunks stored successfully", 
                           total_chunks=len(chunks), 
                           success_count=success_count)
                
                return success_count == len(chunks)
                
            except Exception as e:
                logfire.error("Failed to store document chunks", error=str(e))
                return False
    
    @logfire.instrument("semantic_search")
    async def semantic_search(
        self, 
        query: str, 
        limit: int = 10,
        source_filter: Optional[List[str]] = None,
        quality_threshold: float = 0.0
    ) -> List[SearchResult]:
        """Perform semantic search using vector similarity."""
        if not self.db:
            raise RuntimeError("Not connected to SurrealDB")
        
        with logfire.span("Semantic search", query=query[:100], limit=limit):
            try:
                start_time = time.time()
                logfire.info("Starting semantic search", 
                           query_length=len(query), 
                           limit=limit,
                           source_filter=source_filter,
                           quality_threshold=quality_threshold)
                
                # Generate embedding for query
                query_embeddings = await self.generate_embeddings([query])
                query_embedding = query_embeddings[0]
                
                # Build filter conditions
                conditions = []
                if source_filter:
                    source_list = "', '".join(source_filter)
                    conditions.append(f"source_name IN ['{source_list}']")
                
                if quality_threshold > 0:
                    conditions.append(f"quality_score >= {quality_threshold}")
                
                where_clause = " AND ".join(conditions) if conditions else "true"
                
                # Perform vector similarity search
                # Note: This is a simplified implementation. In production, you'd use
                # SurrealDB's vector similarity functions when they become available
                query_str = f"""
                SELECT *, 
                       vector::similarity::cosine(embedding, {query_embedding}) AS similarity
                FROM document_chunks 
                WHERE {where_clause}
                ORDER BY similarity DESC
                LIMIT {limit};
                """
                
                result = await self.db.query(query_str)
                
                # Process results
                search_results = []
                if result and len(result) > 0:
                    for i, record in enumerate(result[0]):
                        # Convert back to DocumentChunk
                        chunk_data = dict(record)
                        similarity = chunk_data.pop('similarity', 0.0)
                        
                        # Handle SurrealDB ID format and ensure we have required fields
                        surrealdb_id = chunk_data.pop('id', None)
                        if not chunk_data.get('id'):
                            # Extract ID from SurrealDB format or use the surrealdb_id
                            if surrealdb_id and isinstance(surrealdb_id, str):
                                chunk_data['id'] = surrealdb_id.split(':')[-1] if ':' in surrealdb_id else surrealdb_id
                            else:
                                chunk_data['id'] = f"chunk_{i}"
                        
                        chunk = DocumentChunk(**chunk_data)
                        
                        search_result = SearchResult(
                            document=chunk,
                            similarity_score=float(similarity),
                            rank=i + 1
                        )
                        search_results.append(search_result)
                
                search_time = time.time() - start_time
                
                logfire.info("Semantic search completed", 
                           results_found=len(search_results),
                           search_time_ms=search_time * 1000,
                           avg_similarity=np.mean([r.similarity_score for r in search_results]) if search_results else 0)
                
                return search_results
                
            except Exception as e:
                logfire.error("Semantic search failed", error=str(e))
                raise
    
    @logfire.instrument("get_document_chunks")
    async def get_document_chunks(
        self,
        source_name: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[DocumentChunk]:
        """Retrieve document chunks with optional filtering."""
        if not self.db:
            raise RuntimeError("Not connected to SurrealDB")
        
        with logfire.span("Get document chunks", source_name=source_name, limit=limit):
            try:
                where_clause = f"source_name = '{source_name}'" if source_name else "true"
                
                query_str = f"""
                SELECT * FROM document_chunks 
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT {limit}
                START {offset};
                """
                
                result = await self.db.query(query_str)
                
                chunks = []
                if result and len(result) > 0:
                    for i, record in enumerate(result[0]):
                        chunk_data = dict(record)
                        
                        # Handle SurrealDB ID format and ensure we have required fields
                        surrealdb_id = chunk_data.pop('id', None)
                        if not chunk_data.get('id'):
                            # Extract ID from SurrealDB format or use the surrealdb_id
                            if surrealdb_id and isinstance(surrealdb_id, str):
                                chunk_data['id'] = surrealdb_id.split(':')[-1] if ':' in surrealdb_id else surrealdb_id
                            else:
                                chunk_data['id'] = f"chunk_{i}"
                        
                        chunks.append(DocumentChunk(**chunk_data))
                
                logfire.info("Retrieved document chunks", 
                           chunks_found=len(chunks),
                           source_name=source_name)
                
                return chunks
                
            except Exception as e:
                logfire.error("Failed to retrieve document chunks", error=str(e))
                raise
    
    @logfire.instrument("get_storage_stats")
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics and metrics."""
        if not self.db:
            raise RuntimeError("Not connected to SurrealDB")
        
        with logfire.span("Get storage statistics"):
            try:
                stats_queries = [
                    "SELECT count() FROM document_chunks GROUP ALL;",
                    "SELECT source_name, count() FROM document_chunks GROUP BY source_name;",
                    "SELECT avg(quality_score) AS avg_quality FROM document_chunks GROUP ALL;",
                    "SELECT min(created_at) AS earliest, max(created_at) AS latest FROM document_chunks GROUP ALL;"
                ]
                
                stats = {
                    "total_chunks": 0,
                    "chunks_by_source": {},
                    "average_quality": 0.0,
                    "date_range": {}
                }
                
                # Total chunks
                result = await self.db.query(stats_queries[0])
                if result and len(result) > 0 and len(result[0]) > 0:
                    stats["total_chunks"] = result[0][0].get("count", 0)
                
                # Chunks by source
                result = await self.db.query(stats_queries[1])
                if result and len(result) > 0:
                    for record in result[0]:
                        source = record.get("source_name", "unknown")
                        count = record.get("count", 0)
                        stats["chunks_by_source"][source] = count
                
                # Average quality
                result = await self.db.query(stats_queries[2])
                if result and len(result) > 0 and len(result[0]) > 0:
                    stats["average_quality"] = result[0][0].get("avg_quality", 0.0)
                
                # Date range
                result = await self.db.query(stats_queries[3])
                if result and len(result) > 0 and len(result[0]) > 0:
                    record = result[0][0]
                    stats["date_range"] = {
                        "earliest": record.get("earliest"),
                        "latest": record.get("latest")
                    }
                
                logfire.info("Storage statistics retrieved", stats=stats)
                return stats
                
            except Exception as e:
                logfire.error("Failed to get storage statistics", error=str(e))
                raise
    
    @logfire.instrument("surrealdb_close")
    async def close(self):
        """Close SurrealDB connection."""
        if self.db:
            with logfire.span("Closing SurrealDB connection"):
                await self.db.close()
                self.db = None
                logfire.info("SurrealDB connection closed")

# Utility functions for integration
async def create_vector_store(config: VectorStoreConfig = None) -> SurrealDBVectorStore:
    """Create and connect to SurrealDB vector store."""
    store = SurrealDBVectorStore(config)
    connected = await store.connect()
    if not connected:
        raise RuntimeError("Failed to connect to SurrealDB vector store")
    return store

async def migrate_crawl_data_to_vector_store(
    vector_store: SurrealDBVectorStore,
    crawl_results: List[Dict[str, Any]]
) -> bool:
    """Migrate crawl data to vector store format."""
    chunks = []
    
    for i, result in enumerate(crawl_results):
        chunk = DocumentChunk(
            id=f"{result.get('source_name', 'unknown')}_{i}",
            source_name=result.get('source_name', 'Unknown'),
            source_url=result.get('source_url', ''),
            title=result.get('title', 'Untitled'),
            content=result.get('content', ''),
            chunk_index=i,
            total_chunks=len(crawl_results),
            quality_score=result.get('quality_score', 0.0),
            topics=result.get('topics', [])
        )
        chunks.append(chunk)
    
    return await vector_store.store_document_chunks(chunks)

if __name__ == "__main__":
    # Example usage
    async def main():
        config = VectorStoreConfig()
        store = await create_vector_store(config)
        
        # Example search
        results = await store.semantic_search("FastAPI middleware configuration")
        print(f"Found {len(results)} results")
        
        await store.close()
    
    asyncio.run(main())