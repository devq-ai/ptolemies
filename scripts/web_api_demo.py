#!/usr/bin/env python3
"""
Ptolemies Web API Demo
FastAPI-based REST API demonstrating how to expose the 784-page knowledge base
as a web service with comprehensive search and query capabilities.
"""

import asyncio
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Body, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Import Ptolemies components
from practical_usage_guide import PtolemiesKnowledgeAPI, SearchContext, UsagePattern
from src.hybrid_query_engine import QueryType

# Pydantic models for API requests/responses
class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query text")
    max_results: int = Field(10, ge=1, le=50, description="Maximum number of results")
    query_type: str = Field("hybrid_balanced", description="Search strategy")
    source_filter: Optional[List[str]] = Field(None, description="Filter by specific sources")

class SearchResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    total_found: int
    search_time_ms: float
    from_cache: bool
    metadata: Dict[str, Any]

class CodeExampleRequest(BaseModel):
    technology: str = Field(..., description="Technology/framework name")
    use_case: str = Field(..., description="Specific use case or task")
    language: str = Field("python", description="Programming language")

class ConceptExplorationRequest(BaseModel):
    concept: str = Field(..., description="Starting concept to explore")
    depth: int = Field(2, ge=1, le=3, description="Exploration depth")

class TroubleshootingRequest(BaseModel):
    error_message: str = Field(..., description="Error message or issue description")
    technology_stack: List[str] = Field(..., description="Technologies being used")
    context_info: str = Field("", description="Additional context information")

class LearningPathRequest(BaseModel):
    target_skill: str = Field(..., description="Skill to learn")
    current_level: str = Field("beginner", description="Current skill level")
    time_constraint: str = Field("flexible", description="Time availability")

class QuerySuggestionResponse(BaseModel):
    partial_query: str
    suggestions: List[str]
    generated_at: datetime

# Global knowledge API instance
knowledge_api: Optional[PtolemiesKnowledgeAPI] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    global knowledge_api
    
    print("🚀 Starting Ptolemies Web API...")
    
    # Initialize knowledge API
    knowledge_api = PtolemiesKnowledgeAPI()
    success = await knowledge_api.initialize(enable_cache=True)
    
    if success:
        print("✅ Ptolemies Knowledge API initialized successfully")
    else:
        print("❌ Failed to initialize Knowledge API")
        raise RuntimeError("Failed to initialize Knowledge API")
    
    yield  # Application is running
    
    # Cleanup
    print("🧹 Shutting down Ptolemies Web API...")
    if knowledge_api:
        await knowledge_api.close()
    print("✅ Cleanup completed")

# Create FastAPI app
app = FastAPI(
    title="Ptolemies Knowledge API",
    description="REST API for accessing the 784-page Ptolemies knowledge base with vector search, graph relationships, and intelligent caching",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get knowledge API
async def get_knowledge_api() -> PtolemiesKnowledgeAPI:
    """Dependency to get the knowledge API instance."""
    if not knowledge_api or not knowledge_api.initialized:
        raise HTTPException(status_code=503, detail="Knowledge API not available")
    return knowledge_api

# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check():
    """Check API health and system status."""
    api = await get_knowledge_api()
    status = await api.get_system_status()
    
    return {
        "status": "healthy" if status["initialized"] else "unhealthy",
        "timestamp": datetime.utcnow().isoformat(),
        "system_info": status,
        "knowledge_base": {
            "total_pages": 784,
            "sources": 17,
            "performance_target": "sub-100ms"
        }
    }

# Main search endpoint
@app.post("/search", response_model=SearchResponse, tags=["Search"])
async def search_knowledge_base(
    request: SearchRequest,
    background_tasks: BackgroundTasks,
    api: PtolemiesKnowledgeAPI = Depends(get_knowledge_api)
):
    """
    Search the knowledge base using hybrid vector and graph search.
    
    - **query**: The search query text
    - **max_results**: Maximum number of results to return (1-50)
    - **query_type**: Search strategy (hybrid_balanced, semantic_only, graph_only, etc.)
    - **source_filter**: Optional list of sources to filter by
    """
    try:
        # Create search context
        context = SearchContext(
            user_id="api_user",
            session_id="web_api",
            application="ptolemies_web_api",
            search_history=[],
            preferences={}
        )
        
        # Perform search
        result = await api.search_documentation(
            query=request.query,
            context=context,
            max_results=request.max_results
        )
        
        # Log usage in background
        background_tasks.add_task(
            log_search_usage,
            request.query,
            len(result['results']),
            result['search_time_ms']
        )
        
        return SearchResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

# Code examples endpoint
@app.post("/code-examples", tags=["Code Examples"])
async def find_code_examples(
    request: CodeExampleRequest,
    api: PtolemiesKnowledgeAPI = Depends(get_knowledge_api)
):
    """
    Find code examples for specific technologies and use cases.
    
    - **technology**: Technology or framework name (e.g., "FastAPI", "Neo4j")
    - **use_case**: Specific use case or task (e.g., "authentication", "database setup")
    - **language**: Programming language (default: "python")
    """
    try:
        result = await api.find_code_examples(
            technology=request.technology,
            use_case=request.use_case,
            language=request.language
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Code example search failed: {str(e)}")

# Concept exploration endpoint
@app.post("/explore-concepts", tags=["Concept Exploration"])
async def explore_concepts(
    request: ConceptExplorationRequest,
    api: PtolemiesKnowledgeAPI = Depends(get_knowledge_api)
):
    """
    Explore related concepts and build a knowledge map.
    
    - **concept**: Starting concept to explore (e.g., "authentication", "database")
    - **depth**: Exploration depth (1-3, default: 2)
    """
    try:
        result = await api.explore_concepts(
            starting_concept=request.concept,
            depth=request.depth
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Concept exploration failed: {str(e)}")

# Troubleshooting endpoint
@app.post("/troubleshoot", tags=["Troubleshooting"])
async def troubleshoot_issue(
    request: TroubleshootingRequest,
    api: PtolemiesKnowledgeAPI = Depends(get_knowledge_api)
):
    """
    Get troubleshooting help for technical issues.
    
    - **error_message**: Error message or issue description
    - **technology_stack**: List of technologies being used
    - **context_info**: Additional context information (optional)
    """
    try:
        result = await api.troubleshoot_issue(
            error_message=request.error_message,
            technology_stack=request.technology_stack,
            context_info=request.context_info
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Troubleshooting failed: {str(e)}")

# Learning path endpoint
@app.post("/learning-path", tags=["Learning"])
async def generate_learning_path(
    request: LearningPathRequest,
    api: PtolemiesKnowledgeAPI = Depends(get_knowledge_api)
):
    """
    Generate a personalized learning path for acquiring new skills.
    
    - **target_skill**: Skill to learn (e.g., "FastAPI development", "Graph databases")
    - **current_level**: Current skill level (beginner, intermediate, advanced)
    - **time_constraint**: Time availability (flexible, limited, intensive)
    """
    try:
        result = await api.generate_learning_path(
            target_skill=request.target_skill,
            current_level=request.current_level,
            time_constraint=request.time_constraint
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Learning path generation failed: {str(e)}")

# Query suggestions endpoint
@app.get("/suggest", response_model=QuerySuggestionResponse, tags=["Suggestions"])
async def get_query_suggestions(
    q: str = Query(..., description="Partial query to get suggestions for"),
    api: PtolemiesKnowledgeAPI = Depends(get_knowledge_api)
):
    """
    Get intelligent query suggestions based on partial input.
    
    - **q**: Partial query text to get suggestions for
    """
    try:
        suggestions = await api.get_query_suggestions(q)
        
        return QuerySuggestionResponse(
            partial_query=q,
            suggestions=suggestions,
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query suggestions failed: {str(e)}")

# Statistics endpoint
@app.get("/stats", tags=["Statistics"])
async def get_system_statistics(
    api: PtolemiesKnowledgeAPI = Depends(get_knowledge_api)
):
    """Get comprehensive system statistics and performance metrics."""
    try:
        status = await api.get_system_status()
        
        return {
            "system_status": status,
            "knowledge_base_info": {
                "total_pages": 784,
                "total_sources": 17,
                "storage_systems": [
                    "SurrealDB (Vector Storage)",
                    "Neo4j (Graph Database)",
                    "Redis (Cache Layer)"
                ],
                "search_capabilities": [
                    "Semantic Vector Search",
                    "Graph Relationship Exploration",
                    "Hybrid Query Engine",
                    "Concept Expansion",
                    "Intelligent Result Fusion"
                ]
            },
            "api_info": {
                "version": "1.0.0",
                "endpoints": 7,
                "documentation": "/docs"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Statistics retrieval failed: {str(e)}")

# Advanced search endpoint with all options
@app.post("/advanced-search", tags=["Advanced Search"])
async def advanced_search(
    query: str = Body(..., description="Search query"),
    query_type: str = Body("hybrid_balanced", description="Search strategy"),
    max_results: int = Body(10, description="Maximum results"),
    enable_cache: bool = Body(True, description="Use cache if available"),
    include_metadata: bool = Body(True, description="Include search metadata"),
    source_filter: Optional[List[str]] = Body(None, description="Source filter"),
    api: PtolemiesKnowledgeAPI = Depends(get_knowledge_api)
):
    """
    Advanced search with full control over search parameters.
    Supports all query types and detailed configuration options.
    """
    try:
        # Map string query type to enum
        query_type_map = {
            "semantic_only": QueryType.SEMANTIC_ONLY,
            "graph_only": QueryType.GRAPH_ONLY,
            "hybrid_balanced": QueryType.HYBRID_BALANCED,
            "semantic_then_graph": QueryType.SEMANTIC_THEN_GRAPH,
            "graph_then_semantic": QueryType.GRAPH_THEN_SEMANTIC,
            "concept_expansion": QueryType.CONCEPT_EXPANSION
        }
        
        qt = query_type_map.get(query_type, QueryType.HYBRID_BALANCED)
        
        # Perform search directly through hybrid engine
        results, metrics = await api.hybrid_engine.search(
            query=query,
            query_type=qt,
            source_filter=source_filter,
            limit=max_results
        )
        
        # Format response
        response = {
            "query": query,
            "query_type": query_type,
            "results": [
                {
                    "id": r.id,
                    "title": r.title,
                    "content": r.content,
                    "source": r.source_name,
                    "url": r.source_url,
                    "relevance_score": r.combined_score,
                    "semantic_score": r.semantic_score,
                    "graph_score": r.graph_score,
                    "rank": r.rank,
                    "topics": r.topics,
                    "found_via": r.found_via
                }
                for r in results
            ],
            "total_found": len(results),
            "search_time_ms": metrics.total_time_ms
        }
        
        if include_metadata:
            response["metadata"] = {
                "semantic_time_ms": metrics.semantic_time_ms,
                "graph_time_ms": metrics.graph_time_ms,
                "fusion_time_ms": metrics.fusion_time_ms,
                "overlap_count": metrics.overlap_count,
                "concept_expansions": metrics.concept_expansions,
                "query_analysis": {
                    "query_type": metrics.query_analysis.query_type,
                    "detected_concepts": metrics.query_analysis.detected_concepts,
                    "complexity_score": metrics.query_analysis.complexity_score,
                    "semantic_weight": metrics.query_analysis.semantic_weight,
                    "graph_weight": metrics.query_analysis.graph_weight
                }
            }
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Advanced search failed: {str(e)}")

# Background task for usage logging
async def log_search_usage(query: str, result_count: int, search_time_ms: float):
    """Log search usage for analytics (placeholder implementation)."""
    # In production, this would log to a database or analytics service
    print(f"📊 Search logged: '{query}' -> {result_count} results in {search_time_ms:.2f}ms")

# Custom error handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# Root endpoint with API information
@app.get("/", tags=["Information"])
async def root():
    """Get API information and available endpoints."""
    return {
        "name": "Ptolemies Knowledge API",
        "version": "1.0.0",
        "description": "REST API for the 784-page Ptolemies knowledge base",
        "knowledge_base": {
            "total_pages": 784,
            "sources": 17,
            "performance": "sub-100ms queries"
        },
        "endpoints": {
            "search": "POST /search - Main search interface",
            "code_examples": "POST /code-examples - Find code examples",
            "explore_concepts": "POST /explore-concepts - Concept exploration",
            "troubleshoot": "POST /troubleshoot - Technical troubleshooting",
            "learning_path": "POST /learning-path - Generate learning paths",
            "suggestions": "GET /suggest - Query suggestions",
            "advanced_search": "POST /advanced-search - Full search control",
            "statistics": "GET /stats - System statistics",
            "health": "GET /health - Health check"
        },
        "documentation": {
            "interactive": "/docs",
            "redoc": "/redoc"
        }
    }

# Run the API server
if __name__ == "__main__":
    print("🏛️ Starting Ptolemies Knowledge API Server")
    print("=" * 50)
    print("📚 Knowledge Base: 784 pages with embeddings")
    print("🔍 Search Types: Vector, Graph, Hybrid")
    print("⚡ Performance: Sub-100ms queries")
    print("🌐 API Documentation: http://localhost:8000/docs")
    print("=" * 50)
    
    uvicorn.run(
        "web_api_demo:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Set to True for development
        log_level="info"
    )