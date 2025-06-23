#!/usr/bin/env python3
"""
Hybrid Query Engine for Ptolemies
Combines SurrealDB vector search with Neo4j graph relationships for comprehensive knowledge retrieval.
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum

# Optional import for logfire  
try:
    import logfire
    HAS_LOGFIRE = True
except ImportError:
    # Mock logfire for environments where it's not available
    class MockLogfire:
        def configure(self, **kwargs): pass
        def instrument(self, name): 
            def decorator(func): return func
            return decorator
        def span(self, name, **kwargs): 
            class MockSpan:
                def __enter__(self): return self
                def __exit__(self, *args): pass
            return MockSpan()
        def info(self, *args, **kwargs): pass
        def error(self, *args, **kwargs): pass
        def warning(self, *args, **kwargs): pass
    
    logfire = MockLogfire()
    HAS_LOGFIRE = False
import numpy as np

from surrealdb_integration import (
    SurrealDBVectorStore, 
    VectorStoreConfig, 
    SearchResult as VectorSearchResult,
    DocumentChunk
)
from neo4j_integration import (
    Neo4jGraphStore, 
    Neo4jConfig, 
    GraphSearchResult,
    DocumentNode,
    ConceptNode
)

# Configure Logfire
logfire.configure(send_to_logfire=False)  # Configure appropriately for production

class QueryType(Enum):
    """Types of hybrid queries supported."""
    SEMANTIC_ONLY = "semantic_only"
    GRAPH_ONLY = "graph_only"
    HYBRID_BALANCED = "hybrid_balanced"
    SEMANTIC_THEN_GRAPH = "semantic_then_graph"
    GRAPH_THEN_SEMANTIC = "graph_then_semantic"
    CONCEPT_EXPANSION = "concept_expansion"

class RankingStrategy(Enum):
    """Strategies for combining and ranking results."""
    WEIGHTED_AVERAGE = "weighted_average"
    MAX_SCORE = "max_score"
    HARMONIC_MEAN = "harmonic_mean"
    BORDA_COUNT = "borda_count"
    RECIPROCAL_RANK = "reciprocal_rank"

@dataclass
class HybridQueryConfig:
    """Configuration for hybrid query engine."""
    vector_weight: float = 0.6
    graph_weight: float = 0.4
    concept_expansion_threshold: float = 0.8
    max_results: int = 50
    semantic_limit: int = 100
    graph_limit: int = 100
    similarity_threshold: float = 0.5
    graph_depth: int = 2
    enable_concept_expansion: bool = True
    enable_result_fusion: bool = True
    ranking_strategy: RankingStrategy = RankingStrategy.WEIGHTED_AVERAGE

@dataclass
class HybridSearchResult:
    """Represents a unified search result from hybrid query."""
    id: str
    title: str
    content: str
    source_name: str
    source_url: str
    chunk_index: Optional[int] = None
    total_chunks: Optional[int] = None
    quality_score: float = 0.0
    topics: List[str] = None
    
    # Scoring components
    semantic_score: float = 0.0
    graph_score: float = 0.0
    combined_score: float = 0.0
    rank: int = 0
    
    # Metadata
    found_via: List[str] = None  # How this result was discovered
    related_concepts: List[str] = None
    relationship_paths: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.topics is None:
            self.topics = []
        if self.found_via is None:
            self.found_via = []
        if self.related_concepts is None:
            self.related_concepts = []
        if self.relationship_paths is None:
            self.relationship_paths = []

@dataclass
class QueryAnalysis:
    """Analysis of the query to guide search strategy."""
    query_type: str
    detected_concepts: List[str]
    suggested_expansions: List[str]
    complexity_score: float
    semantic_weight: float
    graph_weight: float

@dataclass
class HybridQueryMetrics:
    """Comprehensive metrics for hybrid query performance."""
    total_time_ms: float
    semantic_time_ms: float
    graph_time_ms: float
    fusion_time_ms: float
    total_results: int
    semantic_results: int
    graph_results: int
    unique_results: int
    overlap_count: int
    concept_expansions: int
    query_analysis: QueryAnalysis

class HybridQueryEngine:
    """Hybrid query engine combining vector and graph search."""
    
    def __init__(
        self, 
        vector_store: SurrealDBVectorStore,
        graph_store: Neo4jGraphStore,
        config: HybridQueryConfig = None
    ):
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.config = config or HybridQueryConfig()
        
        # Cache for query analysis
        self._query_cache = {}
        self._concept_cache = {}
    
    @logfire.instrument("analyze_query")
    async def analyze_query(self, query: str) -> QueryAnalysis:
        """Analyze query to determine optimal search strategy."""
        with logfire.span("Analyzing query", query=query[:100]):
            try:
                logfire.info("Starting query analysis", query_length=len(query))
                
                # Check cache first
                if query in self._query_cache:
                    logfire.info("Query analysis cache hit")
                    return self._query_cache[query]
                
                query_lower = query.lower()
                
                # Detect query type
                query_type = "general"
                if any(term in query_lower for term in ["concept", "relationship", "connected", "related"]):
                    query_type = "relational"
                elif any(term in query_lower for term in ["similar", "like", "semantic", "meaning"]):
                    query_type = "semantic"
                elif any(term in query_lower for term in ["specific", "exact", "precise"]):
                    query_type = "exact"
                
                # Detect concepts
                detected_concepts = []
                concept_terms = {
                    "authentication": ["auth", "login", "security", "jwt", "oauth"],
                    "api": ["endpoint", "rest", "graphql", "interface"],
                    "database": ["db", "storage", "data", "persistence"],
                    "framework": ["library", "package", "tool", "platform"],
                    "monitoring": ["logging", "observability", "metrics", "tracing"],
                    "testing": ["test", "unittest", "pytest", "validation"]
                }
                
                for concept, terms in concept_terms.items():
                    if concept in query_lower or any(term in query_lower for term in terms):
                        detected_concepts.append(concept)
                
                # Suggest expansions
                suggested_expansions = []
                if "fastapi" in query_lower:
                    suggested_expansions.extend(["python", "web framework", "api", "async"])
                if "neo4j" in query_lower:
                    suggested_expansions.extend(["graph database", "cypher", "nodes", "relationships"])
                if "surrealdb" in query_lower:
                    suggested_expansions.extend(["multi-model", "database", "vector", "storage"])
                
                # Calculate complexity score
                complexity_score = min(1.0, (
                    len(query.split()) / 10 +  # Word count factor
                    len(detected_concepts) / 5 +  # Concept complexity
                    (0.3 if query_type == "relational" else 0.1)  # Query type factor
                ))
                
                # Determine optimal weights based on query characteristics
                if query_type == "semantic":
                    semantic_weight = 0.8
                    graph_weight = 0.2
                elif query_type == "relational":
                    semantic_weight = 0.3
                    graph_weight = 0.7
                elif len(detected_concepts) > 2:
                    semantic_weight = 0.4
                    graph_weight = 0.6
                else:
                    semantic_weight = self.config.vector_weight
                    graph_weight = self.config.graph_weight
                
                analysis = QueryAnalysis(
                    query_type=query_type,
                    detected_concepts=detected_concepts,
                    suggested_expansions=suggested_expansions,
                    complexity_score=complexity_score,
                    semantic_weight=semantic_weight,
                    graph_weight=graph_weight
                )
                
                # Cache the analysis
                self._query_cache[query] = analysis
                
                logfire.info("Query analysis completed", 
                           query_type=query_type,
                           concepts_detected=len(detected_concepts),
                           complexity_score=complexity_score,
                           semantic_weight=semantic_weight,
                           graph_weight=graph_weight)
                
                return analysis
                
            except Exception as e:
                logfire.error("Query analysis failed", error=str(e))
                # Return default analysis
                return QueryAnalysis(
                    query_type="general",
                    detected_concepts=[],
                    suggested_expansions=[],
                    complexity_score=0.5,
                    semantic_weight=self.config.vector_weight,
                    graph_weight=self.config.graph_weight
                )
    
    @logfire.instrument("semantic_search")
    async def _semantic_search(
        self, 
        query: str, 
        limit: int = None,
        source_filter: Optional[List[str]] = None
    ) -> List[VectorSearchResult]:
        """Perform semantic search using vector store."""
        limit = limit or self.config.semantic_limit
        
        with logfire.span("Semantic search", query=query[:100], limit=limit):
            try:
                start_time = time.time()
                
                results = await self.vector_store.semantic_search(
                    query=query,
                    limit=limit,
                    source_filter=source_filter,
                    quality_threshold=self.config.similarity_threshold
                )
                
                search_time = (time.time() - start_time) * 1000
                
                logfire.info("Semantic search completed",
                           results_found=len(results),
                           search_time_ms=search_time)
                
                return results
                
            except Exception as e:
                logfire.error("Semantic search failed", error=str(e))
                return []
    
    @logfire.instrument("graph_search")
    async def _graph_search(
        self, 
        query: str, 
        search_type: str = "concept",
        limit: int = None,
        max_depth: int = None
    ) -> GraphSearchResult:
        """Perform graph search using graph store."""
        limit = limit or self.config.graph_limit
        max_depth = max_depth or self.config.graph_depth
        
        with logfire.span("Graph search", query=query[:100], search_type=search_type):
            try:
                start_time = time.time()
                
                result = await self.graph_store.graph_search(
                    query=query,
                    search_type=search_type,
                    limit=limit,
                    max_depth=max_depth
                )
                
                search_time = (time.time() - start_time) * 1000
                
                logfire.info("Graph search completed",
                           nodes_found=len(result.nodes),
                           relationships_found=len(result.relationships),
                           paths_found=len(result.paths),
                           search_time_ms=search_time)
                
                return result
                
            except Exception as e:
                logfire.error("Graph search failed", error=str(e))
                return GraphSearchResult(
                    nodes=[],
                    relationships=[],
                    paths=[],
                    query_metadata={"error": str(e)}
                )
    
    @logfire.instrument("concept_expansion")
    async def _expand_query_concepts(self, query: str, analysis: QueryAnalysis) -> List[str]:
        """Expand query with related concepts from graph."""
        if not self.config.enable_concept_expansion or not analysis.detected_concepts:
            return [query]
        
        with logfire.span("Concept expansion", query=query[:100]):
            try:
                expanded_queries = [query]
                
                # Search for each detected concept
                for concept in analysis.detected_concepts:
                    if concept not in self._concept_cache:
                        concept_result = await self._graph_search(
                            concept, 
                            search_type="concept", 
                            limit=10
                        )
                        
                        related_concepts = []
                        for node in concept_result.nodes:
                            if node.get("name") and node["name"].lower() != concept.lower():
                                related_concepts.append(node["name"])
                        
                        self._concept_cache[concept] = related_concepts[:5]  # Cache top 5
                    
                    related = self._concept_cache[concept]
                    for related_concept in related:
                        expanded_query = f"{query} {related_concept}"
                        expanded_queries.append(expanded_query)
                
                # Add suggested expansions
                for expansion in analysis.suggested_expansions:
                    expanded_query = f"{query} {expansion}"
                    expanded_queries.append(expanded_query)
                
                logfire.info("Concept expansion completed",
                           original_query=query,
                           expanded_count=len(expanded_queries))
                
                return expanded_queries[:5]  # Limit to top 5 expansions
                
            except Exception as e:
                logfire.error("Concept expansion failed", error=str(e))
                return [query]
    
    @logfire.instrument("result_fusion")
    async def _fuse_results(
        self,
        semantic_results: List[VectorSearchResult],
        graph_results: List[Dict[str, Any]],
        analysis: QueryAnalysis
    ) -> List[HybridSearchResult]:
        """Fuse and rank results from multiple sources."""
        with logfire.span("Result fusion"):
            try:
                start_time = time.time()
                
                # Convert results to unified format
                unified_results = {}
                
                # Process semantic results
                for i, result in enumerate(semantic_results):
                    doc = result.document
                    result_id = f"semantic_{doc.id}"
                    
                    unified_results[result_id] = HybridSearchResult(
                        id=doc.id,
                        title=doc.title,
                        content=doc.content[:500] + "..." if len(doc.content) > 500 else doc.content,
                        source_name=doc.source_name,
                        source_url=doc.source_url,
                        chunk_index=doc.chunk_index,
                        total_chunks=doc.total_chunks,
                        quality_score=doc.quality_score,
                        topics=doc.topics,
                        semantic_score=result.similarity_score,
                        graph_score=0.0,
                        found_via=["semantic_search"],
                        rank=i + 1
                    )
                
                # Process graph results
                for i, node in enumerate(graph_results):
                    node_id = node.get("id", f"graph_{i}")
                    result_id = f"graph_{node_id}"
                    
                    # Calculate graph score based on node properties
                    graph_score = 0.8  # Base score for graph results
                    if "quality_score" in node:
                        graph_score = float(node["quality_score"])
                    
                    if result_id in unified_results:
                        # Merge with existing result
                        unified_results[result_id].graph_score = graph_score
                        unified_results[result_id].found_via.append("graph_search")
                    else:
                        # Create new result from graph data
                        unified_results[result_id] = HybridSearchResult(
                            id=node_id,
                            title=node.get("title", "Graph Result"),
                            content=node.get("content", "")[:500],
                            source_name=node.get("source_name", "Unknown"),
                            source_url=node.get("source_url", ""),
                            quality_score=node.get("quality_score", 0.5),
                            topics=node.get("topics", []),
                            semantic_score=0.0,
                            graph_score=graph_score,
                            found_via=["graph_search"],
                            rank=i + 1
                        )
                
                # Calculate combined scores
                for result in unified_results.values():
                    if self.config.ranking_strategy == RankingStrategy.WEIGHTED_AVERAGE:
                        result.combined_score = (
                            result.semantic_score * analysis.semantic_weight +
                            result.graph_score * analysis.graph_weight
                        )
                    elif self.config.ranking_strategy == RankingStrategy.MAX_SCORE:
                        result.combined_score = max(result.semantic_score, result.graph_score)
                    elif self.config.ranking_strategy == RankingStrategy.HARMONIC_MEAN:
                        if result.semantic_score > 0 and result.graph_score > 0:
                            result.combined_score = 2 * (result.semantic_score * result.graph_score) / (result.semantic_score + result.graph_score)
                        else:
                            result.combined_score = max(result.semantic_score, result.graph_score)
                    else:
                        # Default to weighted average
                        result.combined_score = (
                            result.semantic_score * analysis.semantic_weight +
                            result.graph_score * analysis.graph_weight
                        )
                
                # Sort by combined score
                sorted_results = sorted(
                    unified_results.values(),
                    key=lambda x: x.combined_score,
                    reverse=True
                )
                
                # Update ranks
                for i, result in enumerate(sorted_results):
                    result.rank = i + 1
                
                fusion_time = (time.time() - start_time) * 1000
                
                # Calculate overlap metrics
                overlap_count = sum(1 for r in sorted_results if len(r.found_via) > 1)
                
                logfire.info("Result fusion completed",
                           total_results=len(sorted_results),
                           overlap_count=overlap_count,
                           fusion_time_ms=fusion_time)
                
                return sorted_results[:self.config.max_results]
                
            except Exception as e:
                logfire.error("Result fusion failed", error=str(e))
                return []
    
    @logfire.instrument("hybrid_search")
    async def search(
        self,
        query: str,
        query_type: QueryType = QueryType.HYBRID_BALANCED,
        source_filter: Optional[List[str]] = None,
        limit: int = None
    ) -> Tuple[List[HybridSearchResult], HybridQueryMetrics]:
        """Perform hybrid search combining semantic and graph approaches."""
        start_time = time.time()
        limit = limit or self.config.max_results
        
        with logfire.span("Hybrid search", query=query[:100], query_type=query_type.value):
            try:
                logfire.info("Starting hybrid search",
                           query=query,
                           query_type=query_type.value,
                           limit=limit)
                
                # Analyze query
                analysis = await self.analyze_query(query)
                
                semantic_results = []
                graph_results = []
                concept_expansions = 0
                
                semantic_start = time.time()
                graph_start = time.time()
                fusion_start = time.time()
                
                if query_type == QueryType.SEMANTIC_ONLY:
                    # Only semantic search
                    semantic_start = time.time()
                    semantic_results = await self._semantic_search(query, limit, source_filter)
                    semantic_time = (time.time() - semantic_start) * 1000
                    graph_time = 0
                    
                elif query_type == QueryType.GRAPH_ONLY:
                    # Only graph search
                    graph_start = time.time()
                    graph_result = await self._graph_search(query, "document", limit)
                    graph_results = graph_result.nodes
                    graph_time = (time.time() - graph_start) * 1000
                    semantic_time = 0
                    
                elif query_type == QueryType.CONCEPT_EXPANSION:
                    # Expand concepts first, then search
                    expanded_queries = await self._expand_query_concepts(query, analysis)
                    concept_expansions = len(expanded_queries) - 1
                    
                    semantic_start = time.time()
                    for expanded_query in expanded_queries:
                        results = await self._semantic_search(expanded_query, limit // len(expanded_queries), source_filter)
                        semantic_results.extend(results)
                    semantic_time = (time.time() - semantic_start) * 1000
                    
                    graph_start = time.time()
                    for expanded_query in expanded_queries:
                        graph_result = await self._graph_search(expanded_query, "concept", limit // len(expanded_queries))
                        graph_results.extend(graph_result.nodes)
                    graph_time = (time.time() - graph_start) * 1000
                    
                elif query_type == QueryType.SEMANTIC_THEN_GRAPH:
                    # Semantic first, then use results to guide graph search
                    semantic_start = time.time()
                    semantic_results = await self._semantic_search(query, limit, source_filter)
                    semantic_time = (time.time() - semantic_start) * 1000
                    
                    # Use top semantic results to guide graph search
                    graph_start = time.time()
                    if semantic_results:
                        for result in semantic_results[:5]:  # Top 5 results
                            for topic in result.document.topics:
                                graph_result = await self._graph_search(topic, "concept", 10)
                                graph_results.extend(graph_result.nodes)
                    graph_time = (time.time() - graph_start) * 1000
                    
                elif query_type == QueryType.GRAPH_THEN_SEMANTIC:
                    # Graph first, then expand with semantic search
                    graph_start = time.time()
                    graph_result = await self._graph_search(query, "concept", limit)
                    graph_results = graph_result.nodes
                    graph_time = (time.time() - graph_start) * 1000
                    
                    # Use graph concepts for semantic search
                    semantic_start = time.time()
                    graph_concepts = [node.get("name", "") for node in graph_results if node.get("name")]
                    for concept in graph_concepts[:5]:
                        results = await self._semantic_search(concept, limit // min(5, len(graph_concepts)), source_filter)
                        semantic_results.extend(results)
                    semantic_time = (time.time() - semantic_start) * 1000
                    
                else:  # HYBRID_BALANCED
                    # Parallel search
                    semantic_start = time.time()
                    semantic_task = self._semantic_search(query, limit, source_filter)
                    
                    graph_start = time.time()
                    graph_task = self._graph_search(query, "document", limit)
                    
                    # Wait for both searches
                    semantic_results, graph_result = await asyncio.gather(semantic_task, graph_task)
                    semantic_time = (time.time() - semantic_start) * 1000
                    graph_time = (time.time() - graph_start) * 1000
                    graph_results = graph_result.nodes
                
                # Fuse results
                fusion_start = time.time()
                if self.config.enable_result_fusion:
                    final_results = await self._fuse_results(semantic_results, graph_results, analysis)
                else:
                    # Simple concatenation without fusion
                    final_results = []
                    for i, result in enumerate(semantic_results):
                        doc = result.document
                        final_results.append(HybridSearchResult(
                            id=doc.id,
                            title=doc.title,
                            content=doc.content,
                            source_name=doc.source_name,
                            source_url=doc.source_url,
                            semantic_score=result.similarity_score,
                            combined_score=result.similarity_score,
                            rank=i + 1,
                            found_via=["semantic_search"]
                        ))
                fusion_time = (time.time() - fusion_start) * 1000
                
                total_time = (time.time() - start_time) * 1000
                
                # Calculate metrics
                overlap_count = sum(1 for r in final_results if len(r.found_via) > 1)
                
                metrics = HybridQueryMetrics(
                    total_time_ms=total_time,
                    semantic_time_ms=semantic_time,
                    graph_time_ms=graph_time,
                    fusion_time_ms=fusion_time,
                    total_results=len(final_results),
                    semantic_results=len(semantic_results),
                    graph_results=len(graph_results),
                    unique_results=len(final_results),
                    overlap_count=overlap_count,
                    concept_expansions=concept_expansions,
                    query_analysis=analysis
                )
                
                logfire.info("Hybrid search completed",
                           total_results=len(final_results),
                           semantic_results=len(semantic_results),
                           graph_results=len(graph_results),
                           overlap_count=overlap_count,
                           total_time_ms=total_time)
                
                return final_results, metrics
                
            except Exception as e:
                logfire.error("Hybrid search failed", error=str(e))
                return [], HybridQueryMetrics(
                    total_time_ms=(time.time() - start_time) * 1000,
                    semantic_time_ms=0,
                    graph_time_ms=0,
                    fusion_time_ms=0,
                    total_results=0,
                    semantic_results=0,
                    graph_results=0,
                    unique_results=0,
                    overlap_count=0,
                    concept_expansions=0,
                    query_analysis=QueryAnalysis(
                        query_type="error",
                        detected_concepts=[],
                        suggested_expansions=[],
                        complexity_score=0.0,
                        semantic_weight=0.5,
                        graph_weight=0.5
                    )
                )
    
    @logfire.instrument("batch_search")
    async def batch_search(
        self,
        queries: List[str],
        query_type: QueryType = QueryType.HYBRID_BALANCED
    ) -> Dict[str, Tuple[List[HybridSearchResult], HybridQueryMetrics]]:
        """Perform batch search for multiple queries."""
        with logfire.span("Batch search", query_count=len(queries)):
            try:
                logfire.info("Starting batch search", query_count=len(queries))
                
                # Execute searches concurrently
                tasks = [
                    self.search(query, query_type) 
                    for query in queries
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Organize results
                batch_results = {}
                successful_searches = 0
                
                for i, query in enumerate(queries):
                    if isinstance(results[i], Exception):
                        logfire.error("Batch search query failed", 
                                    query=query, 
                                    error=str(results[i]))
                        batch_results[query] = ([], None)
                    else:
                        batch_results[query] = results[i]
                        successful_searches += 1
                
                logfire.info("Batch search completed",
                           total_queries=len(queries),
                           successful_searches=successful_searches)
                
                return batch_results
                
            except Exception as e:
                logfire.error("Batch search failed", error=str(e))
                return {query: ([], None) for query in queries}
    
    @logfire.instrument("get_query_suggestions")
    async def get_query_suggestions(self, partial_query: str) -> List[str]:
        """Get query suggestions based on partial input."""
        with logfire.span("Query suggestions", partial_query=partial_query[:50]):
            try:
                suggestions = []
                
                # Get concepts from graph that match partial query
                if len(partial_query) >= 2:
                    graph_result = await self._graph_search(
                        partial_query, 
                        search_type="concept", 
                        limit=10
                    )
                    
                    for node in graph_result.nodes:
                        name = node.get("name", "")
                        if name and name.lower().startswith(partial_query.lower()):
                            suggestions.append(name)
                
                # Add common technical terms
                common_terms = [
                    "FastAPI authentication",
                    "Neo4j graph relationships",
                    "SurrealDB vector search",
                    "Python async programming",
                    "API middleware design",
                    "Database optimization",
                    "Microservices architecture",
                    "Testing strategies",
                    "Monitoring best practices",
                    "Security implementation"
                ]
                
                for term in common_terms:
                    if partial_query.lower() in term.lower():
                        suggestions.append(term)
                
                # Remove duplicates and limit
                unique_suggestions = list(dict.fromkeys(suggestions))[:10]
                
                logfire.info("Query suggestions generated",
                           partial_query=partial_query,
                           suggestions_count=len(unique_suggestions))
                
                return unique_suggestions
                
            except Exception as e:
                logfire.error("Query suggestions failed", error=str(e))
                return []

# Utility functions
async def create_hybrid_engine(
    vector_config: VectorStoreConfig = None,
    graph_config: Neo4jConfig = None,
    hybrid_config: HybridQueryConfig = None
) -> HybridQueryEngine:
    """Create and initialize hybrid query engine."""
    from surrealdb_integration import create_vector_store
    from neo4j_integration import create_graph_store
    
    # Create stores
    vector_store = await create_vector_store(vector_config)
    graph_store = await create_graph_store(graph_config)
    
    # Create hybrid engine
    engine = HybridQueryEngine(vector_store, graph_store, hybrid_config)
    
    return engine

if __name__ == "__main__":
    # Example usage
    async def main():
        engine = await create_hybrid_engine()
        
        # Example search
        results, metrics = await engine.search(
            "FastAPI authentication middleware",
            QueryType.HYBRID_BALANCED
        )
        
        print(f"Found {len(results)} results in {metrics.total_time_ms:.2f}ms")
        for result in results[:5]:
            print(f"- {result.title} (score: {result.combined_score:.3f})")
        
        await engine.vector_store.close()
        await engine.graph_store.close()
    
    asyncio.run(main())