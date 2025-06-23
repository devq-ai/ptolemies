#!/usr/bin/env python3
"""
Query Processing Pipeline for Ptolemies
Sophisticated query processing system that coordinates search, analysis, and response generation.
"""

import asyncio
import time
import re
import json
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict
import hashlib

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

# Optional import for numpy
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    np = None
    HAS_NUMPY = False

# Optional import for sentence transformers
try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    SentenceTransformer = None
    HAS_SENTENCE_TRANSFORMERS = False

# Import Ptolemies components
from hybrid_query_engine import HybridQueryEngine, QueryType, HybridSearchResult
from performance_optimizer import PerformanceOptimizer
from redis_cache_layer import RedisCacheLayer
from mcp_tool_registry import MCPToolRegistry

# Configure Logfire
logfire.configure(send_to_logfire=False)

class QueryIntent(Enum):
    """Types of query intents."""
    SEARCH = "search"
    EXPLAIN = "explain"
    COMPARE = "compare"
    ANALYZE = "analyze"
    SUMMARIZE = "summarize"
    TUTORIAL = "tutorial"
    TROUBLESHOOT = "troubleshoot"
    DEFINITION = "definition"
    EXAMPLE = "example"
    UNKNOWN = "unknown"

class QueryComplexity(Enum):
    """Query complexity levels."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    COMPOUND = "compound"

@dataclass
class QueryContext:
    """Context information for query processing."""
    session_id: str
    user_id: Optional[str] = None
    previous_queries: List[str] = None
    conversation_history: List[Dict[str, Any]] = None
    preferences: Dict[str, Any] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.previous_queries is None:
            self.previous_queries = []
        if self.conversation_history is None:
            self.conversation_history = []
        if self.preferences is None:
            self.preferences = {}
        if self.timestamp is None:
            self.timestamp = time.time()

@dataclass
class ProcessedQuery:
    """Represents a processed query with analysis."""
    original_query: str
    normalized_query: str
    intent: QueryIntent
    complexity: QueryComplexity
    entities: List[Dict[str, str]]
    keywords: List[str]
    concepts: List[str]
    search_strategy: QueryType
    confidence_score: float
    language: str = "en"
    spell_corrected: bool = False
    expanded_queries: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.expanded_queries is None:
            self.expanded_queries = []
        if self.metadata is None:
            self.metadata = {}

@dataclass
class QueryPipelineConfig:
    """Configuration for query processing pipeline."""
    # Intent detection
    enable_intent_detection: bool = True
    intent_confidence_threshold: float = 0.7
    
    # Query expansion
    enable_query_expansion: bool = True
    max_query_expansions: int = 3
    synonym_expansion: bool = True
    concept_expansion: bool = True
    
    # Spell correction
    enable_spell_correction: bool = True
    spell_check_confidence_threshold: float = 0.8
    
    # Entity extraction
    enable_entity_extraction: bool = True
    entity_types: List[str] = None
    
    # Context awareness
    enable_context_awareness: bool = True
    context_window_size: int = 5
    session_timeout_minutes: int = 30
    
    # Performance
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600
    parallel_processing: bool = True
    max_concurrent_operations: int = 5
    
    # Model configuration
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    def __post_init__(self):
        if self.entity_types is None:
            self.entity_types = ["technology", "concept", "framework", "language", "tool"]

class QueryProcessor:
    """Advanced query processor with NLP capabilities."""
    
    def __init__(self, config: QueryPipelineConfig = None):
        self.config = config or QueryPipelineConfig()
        self.embedding_model = None
        self._initialize_models()
        
        # Intent patterns
        self.intent_patterns = {
            QueryIntent.SEARCH: [
                r"(find|search|look for|locate|where)",
                r"(show me|get me|fetch)",
                r"(information about|details on)"
            ],
            QueryIntent.EXPLAIN: [
                r"(explain|what is|what are|describe)",
                r"(how does|how do|how to)",
                r"(tell me about|teach me)"
            ],
            QueryIntent.COMPARE: [
                r"(compare|difference|versus|vs)",
                r"(better than|worse than)",
                r"(pros and cons|advantages|disadvantages)"
            ],
            QueryIntent.ANALYZE: [
                r"(analyze|analysis|evaluate)",
                r"(performance|efficiency|quality)",
                r"(review|assess|examine)"
            ],
            QueryIntent.SUMMARIZE: [
                r"(summarize|summary|overview)",
                r"(key points|main ideas|highlights)",
                r"(brief|concise|short)"
            ],
            QueryIntent.TUTORIAL: [
                r"(tutorial|guide|walkthrough)",
                r"(step by step|how to|instructions)",
                r"(learn|teaching|lesson)"
            ],
            QueryIntent.TROUBLESHOOT: [
                r"(error|problem|issue|bug)",
                r"(fix|solve|resolve|debug)",
                r"(not working|broken|failed)"
            ],
            QueryIntent.DEFINITION: [
                r"(define|definition|meaning)",
                r"(what does.*mean)",
                r"(terminology|glossary)"
            ],
            QueryIntent.EXAMPLE: [
                r"(example|sample|demo)",
                r"(show me code|code snippet)",
                r"(use case|scenario|instance)"
            ]
        }
        
        # Common spelling corrections
        self.common_corrections = {
            "pyton": "python",
            "javascrip": "javascript",
            "databse": "database",
            "funtion": "function",
            "paramter": "parameter",
            "asyncronous": "asynchronous",
            "authetication": "authentication",
            "authorisation": "authorization"
        }
        
        # Concept synonyms for expansion
        self.concept_synonyms = {
            "authentication": ["auth", "login", "sign-in", "authorization"],
            "database": ["db", "datastore", "persistence", "storage"],
            "api": ["endpoint", "interface", "service", "rest"],
            "async": ["asynchronous", "concurrent", "parallel", "non-blocking"],
            "error": ["exception", "bug", "issue", "problem", "failure"],
            "performance": ["speed", "efficiency", "optimization", "fast"],
            "security": ["safety", "protection", "secure", "vulnerability"]
        }
    
    def _initialize_models(self):
        """Initialize NLP models."""
        try:
            if (self.config.enable_query_expansion or self.config.enable_entity_extraction) and HAS_SENTENCE_TRANSFORMERS:
                self.embedding_model = SentenceTransformer(self.config.embedding_model)
                logfire.info("Query processor models initialized")
            elif not HAS_SENTENCE_TRANSFORMERS:
                logfire.warning("sentence-transformers not available, some features disabled")
        except Exception as e:
            logfire.error("Failed to initialize query processor models", error=str(e))
    
    @logfire.instrument("process_query")
    async def process_query(
        self, 
        query: str, 
        context: Optional[QueryContext] = None
    ) -> ProcessedQuery:
        """Process a query through the full pipeline."""
        with logfire.span("Query processing pipeline", query=query[:100]):
            # Normalize query
            normalized = self._normalize_query(query)
            
            # Spell correction
            corrected_query = normalized
            spell_corrected = False
            if self.config.enable_spell_correction:
                corrected_query, spell_corrected = self._spell_correct(normalized)
            
            # Detect intent
            intent = QueryIntent.UNKNOWN
            intent_confidence = 0.0
            if self.config.enable_intent_detection:
                intent, intent_confidence = self._detect_intent(corrected_query)
            
            # Extract entities
            entities = []
            if self.config.enable_entity_extraction:
                entities = self._extract_entities(corrected_query)
            
            # Extract keywords and concepts
            keywords = self._extract_keywords(corrected_query)
            concepts = self._extract_concepts(corrected_query, entities)
            
            # Determine complexity
            complexity = self._assess_complexity(corrected_query, entities, concepts)
            
            # Choose search strategy
            search_strategy = self._determine_search_strategy(
                intent, complexity, concepts
            )
            
            # Query expansion
            expanded_queries = []
            if self.config.enable_query_expansion:
                expanded_queries = await self._expand_query(
                    corrected_query, intent, concepts
                )
            
            # Apply context if available
            if context and self.config.enable_context_awareness:
                search_strategy = self._apply_context(
                    search_strategy, context, intent
                )
            
            processed_query = ProcessedQuery(
                original_query=query,
                normalized_query=corrected_query,
                intent=intent,
                complexity=complexity,
                entities=entities,
                keywords=keywords,
                concepts=concepts,
                search_strategy=search_strategy,
                confidence_score=intent_confidence,
                spell_corrected=spell_corrected,
                expanded_queries=expanded_queries,
                metadata={
                    "processing_time_ms": 0,  # Will be updated
                    "context_applied": context is not None
                }
            )
            
            logfire.info("Query processed", 
                       intent=intent.value,
                       complexity=complexity.value,
                       strategy=search_strategy.value,
                       entities_count=len(entities),
                       concepts_count=len(concepts))
            
            return processed_query
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query text."""
        # Convert to lowercase
        normalized = query.lower().strip()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove special characters but keep meaningful punctuation
        normalized = re.sub(r'[^\w\s\-\.\,\?\!]', '', normalized)
        
        return normalized
    
    def _spell_correct(self, query: str) -> Tuple[str, bool]:
        """Apply spell correction to query."""
        corrected = query
        was_corrected = False
        
        words = query.split()
        corrected_words = []
        
        for word in words:
            if word in self.common_corrections:
                corrected_words.append(self.common_corrections[word])
                was_corrected = True
            else:
                corrected_words.append(word)
        
        corrected = ' '.join(corrected_words)
        
        if was_corrected:
            logfire.info("Spell correction applied", 
                       original=query, 
                       corrected=corrected)
        
        return corrected, was_corrected
    
    def _detect_intent(self, query: str) -> Tuple[QueryIntent, float]:
        """Detect query intent using pattern matching."""
        query_lower = query.lower()
        intent_scores = defaultdict(float)
        
        for intent, patterns in self.intent_patterns.items():
            for pattern_list in patterns:
                if re.search(pattern_list, query_lower):
                    intent_scores[intent] += 1.0
        
        if not intent_scores:
            return QueryIntent.UNKNOWN, 0.0
        
        # Get intent with highest score
        best_intent = max(intent_scores, key=intent_scores.get)
        max_score = intent_scores[best_intent]
        
        # Calculate confidence
        total_patterns = sum(len(p) for p in self.intent_patterns.values())
        confidence = min(max_score / 3.0, 1.0)  # Normalize to 0-1
        
        if confidence < self.config.intent_confidence_threshold:
            return QueryIntent.SEARCH, confidence  # Default to search
        
        return best_intent, confidence
    
    def _extract_entities(self, query: str) -> List[Dict[str, str]]:
        """Extract named entities from query."""
        entities = []
        
        # Technology/framework detection
        tech_patterns = {
            "python": r'\bpython\b',
            "javascript": r'\bjavascript\b|\bjs\b',
            "fastapi": r'\bfastapi\b',
            "react": r'\breact\b',
            "nodejs": r'\bnode\.?js\b',
            "database": r'\b(database|db|sql|nosql)\b',
            "api": r'\bapi\b',
            "mcp": r'\bmcp\b',
            "redis": r'\bredis\b',
            "neo4j": r'\bneo4j\b'
        }
        
        for tech, pattern in tech_patterns.items():
            if re.search(pattern, query.lower()):
                entities.append({
                    "type": "technology",
                    "value": tech,
                    "confidence": 0.9
                })
        
        # Concept detection
        concept_patterns = {
            "authentication": r'\b(auth|authentication|login)\b',
            "caching": r'\b(cache|caching)\b',
            "search": r'\b(search|query|find)\b',
            "performance": r'\b(performance|speed|optimization)\b',
            "security": r'\b(security|secure|vulnerability)\b'
        }
        
        for concept, pattern in concept_patterns.items():
            if re.search(pattern, query.lower()):
                entities.append({
                    "type": "concept",
                    "value": concept,
                    "confidence": 0.85
                })
        
        return entities
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract important keywords from query."""
        # Remove common stop words
        stop_words = {
            'the', 'is', 'at', 'which', 'on', 'a', 'an', 'and', 'or', 'but',
            'in', 'with', 'to', 'for', 'of', 'as', 'by', 'that', 'this',
            'it', 'from', 'be', 'are', 'been', 'being', 'have', 'has', 'had',
            'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may',
            'might', 'must', 'can', 'cant', 'what', 'where', 'when', 'how',
            'why', 'who', 'whom', 'whose'
        }
        
        words = query.lower().split()
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        return keywords
    
    def _extract_concepts(
        self, 
        query: str, 
        entities: List[Dict[str, str]]
    ) -> List[str]:
        """Extract high-level concepts from query."""
        concepts = []
        
        # Get concepts from entities
        for entity in entities:
            if entity["type"] == "concept":
                concepts.append(entity["value"])
        
        # Check for concept keywords
        query_lower = query.lower()
        for concept, synonyms in self.concept_synonyms.items():
            if concept in query_lower or any(syn in query_lower for syn in synonyms):
                if concept not in concepts:
                    concepts.append(concept)
        
        return concepts
    
    def _assess_complexity(
        self, 
        query: str, 
        entities: List[Dict[str, str]], 
        concepts: List[str]
    ) -> QueryComplexity:
        """Assess query complexity."""
        # Simple heuristics for complexity
        word_count = len(query.split())
        entity_count = len(entities)
        concept_count = len(concepts)
        
        # Check for compound queries
        if any(word in query.lower() for word in ['and', 'or', 'but also', 'as well as']):
            return QueryComplexity.COMPOUND
        
        # Complexity scoring
        complexity_score = 0
        
        if word_count > 10:
            complexity_score += 2
        elif word_count > 5:
            complexity_score += 1
        
        if entity_count > 3:
            complexity_score += 2
        elif entity_count > 1:
            complexity_score += 1
        
        if concept_count > 2:
            complexity_score += 1
        
        # Map to complexity level
        if complexity_score >= 4:
            return QueryComplexity.COMPLEX
        elif complexity_score >= 2:
            return QueryComplexity.MODERATE
        else:
            return QueryComplexity.SIMPLE
    
    def _determine_search_strategy(
        self,
        intent: QueryIntent,
        complexity: QueryComplexity,
        concepts: List[str]
    ) -> QueryType:
        """Determine optimal search strategy."""
        # Intent-based strategy
        if intent == QueryIntent.EXPLAIN:
            return QueryType.CONCEPT_EXPANSION
        elif intent == QueryIntent.COMPARE:
            return QueryType.GRAPH_THEN_SEMANTIC
        elif intent == QueryIntent.ANALYZE:
            return QueryType.HYBRID_BALANCED
        elif intent == QueryIntent.TROUBLESHOOT:
            return QueryType.SEMANTIC_THEN_GRAPH
        
        # Complexity-based strategy
        if complexity == QueryComplexity.COMPLEX:
            return QueryType.HYBRID_BALANCED
        elif complexity == QueryComplexity.COMPOUND:
            return QueryType.CONCEPT_EXPANSION
        
        # Concept-based strategy
        if len(concepts) > 2:
            return QueryType.GRAPH_THEN_SEMANTIC
        elif len(concepts) > 0:
            return QueryType.SEMANTIC_THEN_GRAPH
        
        # Default
        return QueryType.SEMANTIC_ONLY
    
    async def _expand_query(
        self,
        query: str,
        intent: QueryIntent,
        concepts: List[str]
    ) -> List[str]:
        """Expand query with synonyms and related terms."""
        expanded = []
        
        # Synonym expansion
        if self.config.synonym_expansion:
            expanded_words = []
            for word in query.split():
                # Check if word has synonyms
                for concept, synonyms in self.concept_synonyms.items():
                    if word == concept or word in synonyms:
                        expanded_words.extend(synonyms)
                        break
            
            if expanded_words:
                expanded.append(f"{query} {' '.join(expanded_words[:3])}")
        
        # Concept expansion
        if self.config.concept_expansion and concepts:
            for concept in concepts[:2]:  # Limit expansion
                expanded.append(f"{query} {concept} tutorial")
                expanded.append(f"{query} {concept} example")
        
        # Intent-specific expansion
        if intent == QueryIntent.TROUBLESHOOT:
            expanded.append(f"{query} solution fix")
        elif intent == QueryIntent.TUTORIAL:
            expanded.append(f"{query} step by step guide")
        elif intent == QueryIntent.EXAMPLE:
            expanded.append(f"{query} code sample demo")
        
        # Limit expansions
        return expanded[:self.config.max_query_expansions]
    
    def _apply_context(
        self,
        search_strategy: QueryType,
        context: QueryContext,
        intent: QueryIntent
    ) -> QueryType:
        """Apply context to refine search strategy."""
        # Check if this is a follow-up query
        if context.previous_queries:
            recent_queries = context.previous_queries[-self.config.context_window_size:]
            
            # If asking for more details, use graph search
            if any(q in context.previous_queries[-1:] for q in ["more", "details", "explain"]):
                return QueryType.GRAPH_THEN_SEMANTIC
            
            # If refining previous search, use semantic
            if len(recent_queries) > 1 and intent == QueryIntent.SEARCH:
                return QueryType.SEMANTIC_ONLY
        
        # Check user preferences
        if context.preferences:
            if context.preferences.get("prefer_examples"):
                return QueryType.SEMANTIC_THEN_GRAPH
            elif context.preferences.get("prefer_concepts"):
                return QueryType.CONCEPT_EXPANSION
        
        return search_strategy

class QueryPipelineOrchestrator:
    """Orchestrates the complete query processing pipeline."""
    
    def __init__(
        self,
        config: QueryPipelineConfig = None,
        hybrid_engine: Optional[HybridQueryEngine] = None,
        cache_layer: Optional[RedisCacheLayer] = None,
        performance_optimizer: Optional[PerformanceOptimizer] = None,
        tool_registry: Optional[MCPToolRegistry] = None
    ):
        self.config = config or QueryPipelineConfig()
        self.query_processor = QueryProcessor(self.config)
        self.hybrid_engine = hybrid_engine
        self.cache_layer = cache_layer
        self.performance_optimizer = performance_optimizer
        self.tool_registry = tool_registry
        
        # Session management
        self.sessions: Dict[str, QueryContext] = {}
        self.session_lock = asyncio.Lock()
    
    @logfire.instrument("process_query_request")
    async def process_query_request(
        self,
        query: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a complete query request."""
        start_time = time.time()
        
        with logfire.span("Query pipeline orchestration", query=query[:100]):
            try:
                # Get or create session context
                context = await self._get_or_create_context(
                    session_id, user_id, preferences
                )
                
                # Check cache first
                cache_key = self._generate_cache_key(query, context)
                if self.cache_layer and self.config.enable_caching:
                    cached_result, found = await self.cache_layer.get(
                        cache_key, "query_pipeline"
                    )
                    if found:
                        logfire.info("Query pipeline cache hit", cache_key=cache_key[:50])
                        return cached_result
                
                # Process query
                processed_query = await self.query_processor.process_query(
                    query, context
                )
                
                # Execute search based on processed query
                search_results = None
                if self.hybrid_engine:
                    if self.config.parallel_processing and processed_query.expanded_queries:
                        # Parallel search for expanded queries
                        search_results = await self._parallel_search(
                            processed_query
                        )
                    else:
                        # Single search
                        search_results = await self._execute_search(
                            processed_query
                        )
                
                # Apply intent-specific processing
                final_results = await self._apply_intent_processing(
                    processed_query, search_results
                )
                
                # Update context
                await self._update_context(context, query, processed_query)
                
                # Calculate metrics
                processing_time_ms = (time.time() - start_time) * 1000
                
                # Build response
                response = {
                    "query": query,
                    "processed_query": asdict(processed_query),
                    "results": final_results,
                    "metadata": {
                        "processing_time_ms": processing_time_ms,
                        "session_id": session_id or "anonymous",
                        "timestamp": time.time(),
                        "cache_key": cache_key[:50] if cache_key else None
                    }
                }
                
                # Cache results
                if self.cache_layer and self.config.enable_caching:
                    await self.cache_layer.set(
                        cache_key,
                        response,
                        "query_pipeline",
                        self.config.cache_ttl_seconds
                    )
                
                logfire.info("Query pipeline completed",
                           processing_time_ms=processing_time_ms,
                           intent=processed_query.intent.value,
                           results_count=len(final_results) if final_results else 0)
                
                return response
                
            except Exception as e:
                logfire.error("Query pipeline failed", 
                            query=query, 
                            error=str(e))
                raise
    
    async def _get_or_create_context(
        self,
        session_id: Optional[str],
        user_id: Optional[str],
        preferences: Optional[Dict[str, Any]]
    ) -> QueryContext:
        """Get or create query context."""
        if not session_id:
            session_id = self._generate_session_id()
        
        async with self.session_lock:
            if session_id in self.sessions:
                context = self.sessions[session_id]
                # Update if new info provided
                if user_id:
                    context.user_id = user_id
                if preferences:
                    context.preferences.update(preferences)
            else:
                context = QueryContext(
                    session_id=session_id,
                    user_id=user_id,
                    preferences=preferences or {}
                )
                self.sessions[session_id] = context
            
            # Clean old sessions
            await self._clean_old_sessions()
        
        return context
    
    async def _update_context(
        self,
        context: QueryContext,
        query: str,
        processed_query: ProcessedQuery
    ):
        """Update context with query information."""
        context.previous_queries.append(query)
        context.conversation_history.append({
            "query": query,
            "intent": processed_query.intent.value,
            "timestamp": time.time()
        })
        
        # Keep context size manageable
        if len(context.previous_queries) > self.config.context_window_size * 2:
            context.previous_queries = context.previous_queries[-self.config.context_window_size:]
        if len(context.conversation_history) > self.config.context_window_size * 2:
            context.conversation_history = context.conversation_history[-self.config.context_window_size:]
    
    async def _clean_old_sessions(self):
        """Clean expired sessions."""
        current_time = time.time()
        timeout_seconds = self.config.session_timeout_minutes * 60
        
        expired_sessions = []
        for session_id, context in self.sessions.items():
            if current_time - context.timestamp > timeout_seconds:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
        
        if expired_sessions:
            logfire.info("Cleaned expired sessions", count=len(expired_sessions))
    
    async def _execute_search(
        self,
        processed_query: ProcessedQuery
    ) -> List[Dict[str, Any]]:
        """Execute search using hybrid engine."""
        if not self.hybrid_engine:
            return []
        
        results, metrics = await self.hybrid_engine.search(
            query=processed_query.normalized_query,
            query_type=processed_query.search_strategy,
            limit=50  # Will be filtered later based on intent
        )
        
        # Convert results to dict format
        formatted_results = []
        for result in results:
            formatted_results.append({
                "id": result.id,
                "title": result.title,
                "content": result.content,
                "source": result.source_name,
                "url": result.source_url,
                "score": result.combined_score,
                "type": "hybrid_result"
            })
        
        return formatted_results
    
    async def _parallel_search(
        self,
        processed_query: ProcessedQuery
    ) -> List[Dict[str, Any]]:
        """Execute parallel searches for expanded queries."""
        all_queries = [processed_query.normalized_query] + processed_query.expanded_queries
        
        # Limit concurrency
        semaphore = asyncio.Semaphore(self.config.max_concurrent_operations)
        
        async def search_with_query(query: str):
            async with semaphore:
                query_copy = ProcessedQuery(
                    original_query=query,
                    normalized_query=query,
                    intent=processed_query.intent,
                    complexity=processed_query.complexity,
                    entities=processed_query.entities,
                    keywords=processed_query.keywords,
                    concepts=processed_query.concepts,
                    search_strategy=processed_query.search_strategy,
                    confidence_score=processed_query.confidence_score
                )
                return await self._execute_search(query_copy)
        
        # Execute searches in parallel
        search_tasks = [search_with_query(q) for q in all_queries]
        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # Merge and deduplicate results
        merged_results = []
        seen_ids = set()
        
        for results in search_results:
            if isinstance(results, Exception):
                logfire.error("Parallel search failed", error=str(results))
                continue
            
            for result in results:
                if result["id"] not in seen_ids:
                    seen_ids.add(result["id"])
                    merged_results.append(result)
        
        # Sort by score
        merged_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return merged_results
    
    async def _apply_intent_processing(
        self,
        processed_query: ProcessedQuery,
        search_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Apply intent-specific processing to results."""
        if not search_results:
            return []
        
        intent = processed_query.intent
        
        if intent == QueryIntent.SUMMARIZE:
            # Return top results with summaries
            return search_results[:3]
        
        elif intent == QueryIntent.COMPARE:
            # Group results by entity for comparison
            entity_groups = defaultdict(list)
            for result in search_results:
                for entity in processed_query.entities:
                    if entity["value"] in result["content"].lower():
                        entity_groups[entity["value"]].append(result)
            
            # Return balanced results from each group
            comparison_results = []
            for entity, results in entity_groups.items():
                comparison_results.extend(results[:2])
            
            return comparison_results[:10]
        
        elif intent == QueryIntent.TUTORIAL:
            # Prioritize tutorial-like content
            tutorial_results = []
            other_results = []
            
            for result in search_results:
                content_lower = result["content"].lower()
                if any(word in content_lower for word in ["step", "guide", "tutorial", "example"]):
                    tutorial_results.append(result)
                else:
                    other_results.append(result)
            
            return tutorial_results[:5] + other_results[:5]
        
        elif intent == QueryIntent.TROUBLESHOOT:
            # Prioritize solution-oriented content
            solution_results = []
            other_results = []
            
            for result in search_results:
                content_lower = result["content"].lower()
                if any(word in content_lower for word in ["fix", "solution", "resolve", "solved"]):
                    solution_results.append(result)
                else:
                    other_results.append(result)
            
            return solution_results[:7] + other_results[:3]
        
        elif intent == QueryIntent.EXAMPLE:
            # Prioritize code examples
            example_results = []
            other_results = []
            
            for result in search_results:
                content_lower = result["content"].lower()
                if any(indicator in content_lower for indicator in ["```", "code", "example", "sample"]):
                    example_results.append(result)
                else:
                    other_results.append(result)
            
            return example_results[:8] + other_results[:2]
        
        else:
            # Default: return top results
            return search_results[:10]
    
    def _generate_cache_key(
        self,
        query: str,
        context: QueryContext
    ) -> str:
        """Generate cache key for query."""
        # Include relevant context in cache key
        key_parts = [
            query.lower(),
            context.user_id or "anonymous",
            str(len(context.previous_queries)),
            str(context.preferences.get("result_limit", 10))
        ]
        
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        return f"session_{int(time.time() * 1000)}_{hash(time.time())}"
    
    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a session."""
        if session_id not in self.sessions:
            return None
        
        context = self.sessions[session_id]
        return {
            "session_id": session_id,
            "user_id": context.user_id,
            "query_count": len(context.previous_queries),
            "last_query": context.previous_queries[-1] if context.previous_queries else None,
            "session_duration_seconds": time.time() - context.timestamp,
            "preferences": context.preferences
        }
    
    async def clear_session(self, session_id: str) -> bool:
        """Clear a specific session."""
        async with self.session_lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                logfire.info("Session cleared", session_id=session_id)
                return True
        return False

# Utility functions
async def create_query_pipeline(
    hybrid_engine: Optional[HybridQueryEngine] = None,
    cache_layer: Optional[RedisCacheLayer] = None,
    performance_optimizer: Optional[PerformanceOptimizer] = None,
    tool_registry: Optional[MCPToolRegistry] = None,
    config: Optional[QueryPipelineConfig] = None
) -> QueryPipelineOrchestrator:
    """Create and initialize query pipeline orchestrator."""
    orchestrator = QueryPipelineOrchestrator(
        config=config,
        hybrid_engine=hybrid_engine,
        cache_layer=cache_layer,
        performance_optimizer=performance_optimizer,
        tool_registry=tool_registry
    )
    
    logfire.info("Query pipeline orchestrator created")
    return orchestrator

if __name__ == "__main__":
    # Example usage
    async def main():
        # Create pipeline
        pipeline = await create_query_pipeline()
        
        # Example queries
        test_queries = [
            "How to implement authentication in FastAPI?",
            "Compare Redis and Neo4j for caching",
            "Debug async function not working",
            "Example of MCP tool registration",
            "Summarize performance optimization techniques"
        ]
        
        for query in test_queries:
            print(f"\nProcessing: {query}")
            result = await pipeline.process_query_request(query)
            
            processed = result["processed_query"]
            print(f"Intent: {processed['intent']}")
            print(f"Complexity: {processed['complexity']}")
            print(f"Strategy: {processed['search_strategy']}")
            print(f"Concepts: {processed['concepts']}")
            print(f"Processing time: {result['metadata']['processing_time_ms']:.2f}ms")
    
    asyncio.run(main())