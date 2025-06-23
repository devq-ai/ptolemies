#!/usr/bin/env python3
"""
Ptolemies FastAPI Application
Main application entry point for the Ptolemies knowledge base system.
"""

import asyncio
import os
import time
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional

import logfire
from fastapi import FastAPI, HTTPException, Depends, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Import our modules
from crawl4ai_integration import PtolemiesCrawler, CrawlConfig, DOCUMENTATION_SOURCES
from surrealdb_integration import SurrealDBVectorStore, VectorStoreConfig
from neo4j_integration import Neo4jGraphStore, Neo4jConfig
from hybrid_query_engine import HybridQueryEngine
from performance_optimizer import PerformanceOptimizer
from redis_cache_layer import RedisCacheLayer

# Configure Logfire (REQUIRED)
logfire.configure(send_to_logfire=False)  # Disable in development

class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    version: str
    framework: str
    services: Dict[str, str]
    timestamp: str

class CrawlRequest(BaseModel):
    """Request model for crawling operations."""
    source_name: str = Field(..., description="Name of the documentation source")
    source_url: str = Field(..., description="URL to crawl")
    max_pages: Optional[int] = Field(10, description="Maximum pages to crawl")
    max_depth: Optional[int] = Field(2, description="Maximum crawl depth")

class CrawlResponse(BaseModel):
    """Response model for crawling operations."""
    success: bool
    source_name: str
    pages_crawled: int
    pages_stored: int
    processing_time: float
    message: str

class SearchRequest(BaseModel):
    """Request model for knowledge base search."""
    query: str = Field(..., description="Search query")
    limit: Optional[int] = Field(10, description="Maximum results to return")
    source_filter: Optional[List[str]] = Field(None, description="Filter by source names")

class SearchResponse(BaseModel):
    """Response model for search results."""
    query: str
    results: List[Dict[str, Any]]
    total_results: int
    processing_time: float

class BatchCrawlResponse(BaseModel):
    """Response model for batch crawling operations."""
    success: bool
    sources_attempted: int
    sources_completed: int
    total_pages_crawled: int
    total_pages_stored: int
    total_processing_time: float
    results: List[Dict[str, Any]]
    message: str

# Global instances for enhanced infrastructure
crawler_instance: Optional[PtolemiesCrawler] = None
surrealdb_store: Optional[SurrealDBVectorStore] = None
neo4j_store: Optional[Neo4jGraphStore] = None
hybrid_engine: Optional[HybridQueryEngine] = None
performance_optimizer: Optional[PerformanceOptimizer] = None
redis_cache: Optional[RedisCacheLayer] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan with enhanced infrastructure initialization."""
    global crawler_instance, surrealdb_store, neo4j_store, hybrid_engine, performance_optimizer, redis_cache
    
    logfire.info("Ptolemies application starting up with enhanced infrastructure")
    
    try:
        # Initialize Redis cache layer
        try:
            redis_cache = RedisCacheLayer()
            await redis_cache.connect()
            logfire.info("Redis cache layer initialized successfully")
        except Exception as e:
            logfire.warning("Redis cache layer initialization failed", error=str(e))
            redis_cache = None
        
        # Initialize SurrealDB vector store
        try:
            surrealdb_store = SurrealDBVectorStore(VectorStoreConfig())
            await surrealdb_store.connect()
            logfire.info("SurrealDB vector store initialized successfully")
        except Exception as e:
            logfire.warning("SurrealDB initialization failed", error=str(e))
            surrealdb_store = None
        
        # Initialize Neo4j graph store
        try:
            neo4j_store = Neo4jGraphStore(Neo4jConfig())
            await neo4j_store.connect()
            logfire.info("Neo4j graph store initialized successfully")
        except Exception as e:
            logfire.warning("Neo4j initialization failed", error=str(e))
            neo4j_store = None
        
        # Initialize performance optimizer
        try:
            performance_optimizer = PerformanceOptimizer()
            await performance_optimizer.initialize()
            logfire.info("Performance optimizer initialized successfully")
        except Exception as e:
            logfire.warning("Performance optimizer initialization failed", error=str(e))
            performance_optimizer = None
        
        # Initialize hybrid query engine
        try:
            if surrealdb_store and neo4j_store:
                hybrid_engine = HybridQueryEngine(
                    surrealdb_store=surrealdb_store,
                    neo4j_store=neo4j_store,
                    redis_cache=redis_cache,
                    performance_optimizer=performance_optimizer
                )
                await hybrid_engine.initialize()
                logfire.info("Hybrid query engine initialized successfully")
            else:
                logfire.warning("Hybrid query engine not initialized - missing storage components")
                hybrid_engine = None
        except Exception as e:
            logfire.warning("Hybrid query engine initialization failed", error=str(e))
            hybrid_engine = None
        
        # Initialize crawler with enhanced infrastructure
        config = CrawlConfig(
            max_depth=int(os.getenv("CRAWLER_MAX_DEPTH", "2")),
            max_pages=int(os.getenv("CRAWLER_MAX_PAGES", "250")),
            delay_ms=int(os.getenv("CRAWLER_DELAY_MS", "1000")),
            user_agent=os.getenv("CRAWLER_USER_AGENT", "Ptolemies Knowledge Crawler/1.0")
        )
        
        crawler_instance = PtolemiesCrawler(
            config=config,
            storage_adapter=surrealdb_store,  # Legacy support
            hybrid_engine=hybrid_engine,
            performance_optimizer=performance_optimizer,
            redis_cache=redis_cache
        )
        
        logfire.info(
            "Enhanced crawler initialized successfully",
            config=config.__dict__,
            has_hybrid_engine=hybrid_engine is not None,
            has_performance_optimizer=performance_optimizer is not None,
            has_redis_cache=redis_cache is not None
        )
        
        yield
        
    finally:
        # Cleanup all components
        logfire.info("Starting enhanced infrastructure cleanup")
        
        if crawler_instance:
            await crawler_instance.close()
            logfire.info("Crawler closed")
        
        if hybrid_engine:
            await hybrid_engine.close()
            logfire.info("Hybrid engine closed")
        
        if performance_optimizer:
            await performance_optimizer.close()
            logfire.info("Performance optimizer closed")
        
        if surrealdb_store:
            await surrealdb_store.close()
            logfire.info("SurrealDB store closed")
        
        if neo4j_store:
            await neo4j_store.close()
            logfire.info("Neo4j store closed")
        
        if redis_cache:
            await redis_cache.close()
            logfire.info("Redis cache closed")
        
        logfire.info("Ptolemies application shutdown complete")

app = FastAPI(
    title="Ptolemies - DevQ.AI Knowledge Base",
    description="Centralized knowledge base for DevQ.AI ecosystem with RAG and graph capabilities",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable Logfire instrumentation (REQUIRED)
logfire.instrument_fastapi(app, capture_headers=True)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse)
@logfire.instrument("health_check")
async def health_check():
    """Health check endpoint with comprehensive status."""
    import datetime
    
    with logfire.span("Health check processing"):
        logfire.info("Health check requested")
        
        # Check service availability
        services = {
            "crawler": "available" if crawler_instance else "unavailable",
            "logfire": "configured",
            "fastapi": "running"
        }
        
        # Add database checks
        try:
            # Check SurrealDB
            if os.getenv("SURREALDB_URL"):
                services["surrealdb"] = "configured"
            else:
                services["surrealdb"] = "not_configured"
                
            # Check Neo4j
            if os.getenv("NEO4J_URI"):
                services["neo4j"] = "configured"
            else:
                services["neo4j"] = "not_configured"
                
            # Check Redis
            if os.getenv("UPSTASH_REDIS_REST_URL"):
                services["redis"] = "configured"
            else:
                services["redis"] = "not_configured"
                
        except Exception as e:
            logfire.error("Error checking services", error=str(e))
            services["error"] = str(e)
        
        response = HealthResponse(
            status="healthy",
            version="1.0.0",
            framework="FastAPI + DevQ.ai stack",
            services=services,
            timestamp=datetime.datetime.utcnow().isoformat()
        )
        
        logfire.info("Health check completed", services=services)
        return response

@app.get("/sources")
@logfire.instrument("list_sources")
async def list_documentation_sources():
    """List all available documentation sources."""
    with logfire.span("List documentation sources"):
        logfire.info("Documentation sources requested")
        
        sources = []
        for source in DOCUMENTATION_SOURCES:
            sources.append({
                "name": source["name"],
                "url": source["url"],
                "status": "available"
            })
        
        logfire.info("Sources listed", count=len(sources))
        return {
            "sources": sources,
            "total_count": len(sources)
        }

@app.post("/crawl", response_model=CrawlResponse)
@logfire.instrument("crawl_documentation")
async def crawl_documentation(request: CrawlRequest):
    """Crawl a documentation source."""
    if not crawler_instance:
        raise HTTPException(status_code=503, detail="Crawler not available")
    
    with logfire.span("Crawl documentation", source=request.source_name):
        logfire.info("Crawling started", request=request.dict())
        
        try:
            # Update crawler config for this request
            crawler_instance.config.max_pages = request.max_pages
            crawler_instance.config.max_depth = request.max_depth
            
            # Perform crawl
            result = await crawler_instance.crawl_documentation_source(
                request.source_url,
                request.source_name
            )
            
            if result["success"]:
                response = CrawlResponse(
                    success=True,
                    source_name=result["source_name"],
                    pages_crawled=result["pages_crawled"],
                    pages_stored=result["pages_stored"],
                    processing_time=result["processing_time"],
                    message=f"Successfully crawled {result['pages_stored']} pages"
                )
                
                logfire.info("Crawl completed successfully", result=result)
                return response
            else:
                logfire.error("Crawl failed", error=result.get("error"))
                raise HTTPException(
                    status_code=500,
                    detail=f"Crawl failed: {result.get('error', 'Unknown error')}"
                )
                
        except Exception as e:
            logfire.error("Crawl exception", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/crawl/metrics")
@logfire.instrument("get_crawl_metrics")
async def get_crawl_metrics():
    """Get comprehensive crawling metrics."""
    if not crawler_instance:
        raise HTTPException(status_code=503, detail="Crawler not available")
    
    with logfire.span("Get crawl metrics"):
        logfire.info("Metrics requested")
        
        try:
            metrics = await crawler_instance.get_crawl_metrics()
            logfire.info("Metrics retrieved", metrics=metrics)
            return metrics
            
        except Exception as e:
            logfire.error("Metrics retrieval failed", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/crawl/all", response_model=BatchCrawlResponse)
@logfire.instrument("batch_crawl_all_sources")
async def batch_crawl_all_sources():
    """Crawl all 18 documentation sources with enhanced infrastructure."""
    if not crawler_instance:
        raise HTTPException(status_code=503, detail="Crawler not available")
    
    with logfire.span("Batch crawl all sources"):
        logfire.info("Starting batch crawl of all documentation sources", total_sources=len(DOCUMENTATION_SOURCES))
        
        start_time = time.time()
        results = []
        sources_completed = 0
        total_pages_crawled = 0
        total_pages_stored = 0
        
        try:
            # Use performance optimization for concurrent processing if available
            if performance_optimizer:
                # Process sources in optimized batches
                batch_size = 3  # Conservative concurrent processing
                for i in range(0, len(DOCUMENTATION_SOURCES), batch_size):
                    batch = DOCUMENTATION_SOURCES[i:i + batch_size]
                    
                    # Create concurrent tasks for the batch
                    tasks = []
                    for source in batch:
                        task = crawler_instance.crawl_documentation_source(
                            source["url"], source["name"]
                        )
                        tasks.append(task)
                    
                    # Process batch concurrently
                    batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Process results
                    for j, result in enumerate(batch_results):
                        source = batch[j]
                        if isinstance(result, Exception):
                            logfire.error(
                                "Source crawl failed",
                                source=source["name"],
                                error=str(result)
                            )
                            results.append({
                                "source_name": source["name"],
                                "source_url": source["url"],
                                "success": False,
                                "error": str(result),
                                "pages_crawled": 0,
                                "pages_stored": 0,
                                "processing_time": 0
                            })
                        else:
                            results.append(result)
                            if result.get("success"):
                                sources_completed += 1
                                total_pages_crawled += result.get("pages_crawled", 0)
                                total_pages_stored += result.get("pages_stored", 0)
                    
                    # Brief pause between batches to be respectful
                    await asyncio.sleep(2)
                    
                    logfire.info(
                        "Batch completed",
                        batch_number=i // batch_size + 1,
                        sources_in_batch=len(batch),
                        completed_in_batch=sum(1 for r in batch_results if not isinstance(r, Exception) and r.get("success"))
                    )
            
            else:
                # Sequential processing fallback
                logfire.info("Using sequential processing (performance optimizer not available)")
                
                for source in DOCUMENTATION_SOURCES:
                    try:
                        logfire.info("Crawling source", source=source["name"], url=source["url"])
                        
                        result = await crawler_instance.crawl_documentation_source(
                            source["url"], source["name"]
                        )
                        
                        results.append(result)
                        
                        if result.get("success"):
                            sources_completed += 1
                            total_pages_crawled += result.get("pages_crawled", 0)
                            total_pages_stored += result.get("pages_stored", 0)
                            
                            logfire.info(
                                "Source completed successfully",
                                source=source["name"],
                                pages_crawled=result.get("pages_crawled", 0),
                                pages_stored=result.get("pages_stored", 0)
                            )
                        else:
                            logfire.error("Source failed", source=source["name"], error=result.get("error"))
                        
                        # Respect rate limiting between sources
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        logfire.error("Source crawl exception", source=source["name"], error=str(e))
                        results.append({
                            "source_name": source["name"],
                            "source_url": source["url"],
                            "success": False,
                            "error": str(e),
                            "pages_crawled": 0,
                            "pages_stored": 0,
                            "processing_time": 0
                        })
            
            processing_time = time.time() - start_time
            
            # Generate comprehensive metrics
            success_rate = sources_completed / len(DOCUMENTATION_SOURCES) * 100
            
            response = BatchCrawlResponse(
                success=sources_completed > 0,
                sources_attempted=len(DOCUMENTATION_SOURCES),
                sources_completed=sources_completed,
                total_pages_crawled=total_pages_crawled,
                total_pages_stored=total_pages_stored,
                total_processing_time=processing_time,
                results=results,
                message=f"Batch crawl completed: {sources_completed}/{len(DOCUMENTATION_SOURCES)} sources successful, {total_pages_stored} pages stored"
            )
            
            logfire.info(
                "Batch crawl completed",
                sources_attempted=len(DOCUMENTATION_SOURCES),
                sources_completed=sources_completed,
                total_pages_crawled=total_pages_crawled,
                total_pages_stored=total_pages_stored,
                processing_time=processing_time,
                success_rate=success_rate
            )
            
            return response
            
        except Exception as e:
            logfire.error("Batch crawl failed", error=str(e))
            raise HTTPException(status_code=500, detail=f"Batch crawl failed: {str(e)}")

@app.post("/search", response_model=SearchResponse)
@logfire.instrument("search_knowledge_base")
async def search_knowledge_base(request: SearchRequest):
    """Search the knowledge base (placeholder implementation)."""
    with logfire.span("Search knowledge base", query=request.query):
        logfire.info("Search requested", request=request.dict())
        
        # Placeholder implementation - will be completed in Task 4
        import time
        start_time = time.time()
        
        # Mock search results
        results = [
            {
                "title": f"Mock Result for: {request.query}",
                "content": "This is a placeholder result. Full search implementation coming in Task 4.",
                "source": "Mock Source",
                "url": "https://example.com/mock",
                "score": 0.95
            }
        ]
        
        processing_time = time.time() - start_time
        
        response = SearchResponse(
            query=request.query,
            results=results,
            total_results=len(results),
            processing_time=processing_time
        )
        
        logfire.info("Search completed", response=response.dict())
        return response

@app.get("/status")
@logfire.instrument("get_system_status")
async def get_system_status():
    """Get detailed system status."""
    with logfire.span("System status check"):
        logfire.info("System status requested")
        
        status = {
            "application": "running",
            "version": "1.0.0",
            "environment": os.getenv("NODE_ENV", "development"),
            "services": {
                "crawler": crawler_instance is not None,
                "logfire": True,
                "fastapi": True
            },
            "configuration": {
                "max_crawl_depth": os.getenv("CRAWLER_MAX_DEPTH", "2"),
                "max_crawl_pages": os.getenv("CRAWLER_MAX_PAGES", "250"),
                "crawler_delay": os.getenv("CRAWLER_DELAY_MS", "1000"),
                "log_level": os.getenv("LOG_LEVEL", "info")
            }
        }
        
        logfire.info("System status retrieved", status=status)
        return status

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler."""
    logfire.warning("404 Not Found", path=str(request.url))
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested resource was not found",
            "path": str(request.url.path)
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Custom 500 handler."""
    logfire.error("500 Internal Server Error", error=str(exc), path=str(request.url))
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An internal server error occurred",
            "path": str(request.url.path)
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )