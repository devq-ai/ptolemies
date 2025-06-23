#!/usr/bin/env python3
"""
Performance Optimizer for Ptolemies
Optimizes query performance for sub-100ms response times through caching, connection pooling,
query optimization, and intelligent resource management.
"""

import asyncio
import time
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import json
from collections import defaultdict, OrderedDict
import threading
import weakref

import logfire
import numpy as np

# Configure Logfire
logfire.configure(send_to_logfire=False)  # Configure appropriately for production

class CacheStrategy(Enum):
    """Cache strategies for different data types."""
    LRU = "lru"
    LFU = "lfu"
    TTL = "ttl"
    ADAPTIVE = "adaptive"

class OptimizationLevel(Enum):
    """Performance optimization levels."""
    MINIMAL = "minimal"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    EXTREME = "extreme"

@dataclass
class PerformanceConfig:
    """Configuration for performance optimization."""
    # Cache settings
    query_cache_size: int = 1000
    result_cache_size: int = 5000
    embedding_cache_size: int = 2000
    concept_cache_size: int = 500
    cache_ttl_seconds: int = 3600
    
    # Connection pooling
    max_concurrent_queries: int = 100
    connection_pool_size: int = 20
    connection_timeout_ms: int = 5000
    
    # Query optimization
    semantic_batch_size: int = 50
    graph_batch_size: int = 25
    parallel_search_threshold: int = 2
    query_timeout_ms: int = 90
    
    # Resource limits
    max_memory_mb: int = 512
    max_cpu_percent: float = 80.0
    gc_threshold: int = 1000
    
    # Optimization level
    optimization_level: OptimizationLevel = OptimizationLevel.BALANCED
    
    # Performance targets
    target_response_time_ms: float = 100.0
    target_cache_hit_rate: float = 0.7
    target_memory_usage_mb: float = 256.0

@dataclass
class PerformanceMetrics:
    """Performance metrics tracking."""
    query_count: int = 0
    total_query_time_ms: float = 0.0
    avg_query_time_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    cache_hit_rate: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    concurrent_queries: int = 0
    optimization_applied: List[str] = None
    bottlenecks_detected: List[str] = None
    
    def __post_init__(self):
        if self.optimization_applied is None:
            self.optimization_applied = []
        if self.bottlenecks_detected is None:
            self.bottlenecks_detected = []

class LRUCache:
    """Thread-safe LRU cache implementation."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache = OrderedDict()
        self.timestamps = {}
        self.lock = threading.RLock()
        self.hits = 0
        self.misses = 0
    
    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired."""
        if key not in self.timestamps:
            return True
        return time.time() - self.timestamps[key] > self.ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self.lock:
            if key in self.cache and not self._is_expired(key):
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                self.hits += 1
                return self.cache[key]
            elif key in self.cache:
                # Remove expired entry
                del self.cache[key]
                del self.timestamps[key]
            
            self.misses += 1
            return None
    
    def put(self, key: str, value: Any) -> None:
        """Put value in cache."""
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            else:
                if len(self.cache) >= self.max_size:
                    # Remove least recently used
                    oldest_key = next(iter(self.cache))
                    del self.cache[oldest_key]
                    del self.timestamps[oldest_key]
            
            self.cache[key] = value
            self.timestamps[key] = time.time()
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self.lock:
            self.cache.clear()
            self.timestamps.clear()
            self.hits = 0
            self.misses = 0
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = self.hits / total_requests if total_requests > 0 else 0.0
            
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": hit_rate,
                "memory_usage_estimate": len(self.cache) * 1024  # Rough estimate
            }

class QueryOptimizer:
    """Optimizes individual queries for better performance."""
    
    def __init__(self, config: PerformanceConfig):
        self.config = config
        self.query_patterns = {}
        self.optimization_history = defaultdict(list)
    
    @logfire.instrument("optimize_semantic_query")
    def optimize_semantic_query(self, query: str, limit: int) -> Tuple[str, int, Dict[str, Any]]:
        """Optimize semantic search query."""
        optimizations = []
        optimized_query = query.strip()
        optimized_limit = limit
        
        # Query length optimization
        if len(query) > 200:
            # Truncate very long queries
            optimized_query = query[:200] + "..."
            optimizations.append("query_truncation")
        
        # Limit optimization
        if limit > self.config.semantic_batch_size:
            optimized_limit = self.config.semantic_batch_size
            optimizations.append("limit_reduction")
        
        # Remove redundant words
        words = optimized_query.split()
        if len(words) > 20:
            # Keep most important words (first and last parts)
            important_words = words[:10] + words[-5:]
            optimized_query = " ".join(important_words)
            optimizations.append("word_reduction")
        
        optimization_info = {
            "applied": optimizations,
            "original_length": len(query),
            "optimized_length": len(optimized_query),
            "original_limit": limit,
            "optimized_limit": optimized_limit
        }
        
        logfire.info("Semantic query optimized", 
                    optimizations=optimizations,
                    length_reduction=len(query) - len(optimized_query))
        
        return optimized_query, optimized_limit, optimization_info
    
    @logfire.instrument("optimize_graph_query")
    def optimize_graph_query(self, query: str, search_type: str, max_depth: int) -> Tuple[str, str, int, Dict[str, Any]]:
        """Optimize graph search query."""
        optimizations = []
        optimized_query = query.strip()
        optimized_search_type = search_type
        optimized_max_depth = max_depth
        
        # Depth optimization based on query complexity
        if max_depth > 3 and len(query.split()) < 3:
            # Simple queries don't need deep traversal
            optimized_max_depth = 2
            optimizations.append("depth_reduction_simple")
        elif max_depth > 4:
            # Cap maximum depth for performance
            optimized_max_depth = 3
            optimizations.append("depth_capping")
        
        # Search type optimization
        if "concept" in query.lower() and search_type == "document":
            optimized_search_type = "concept"
            optimizations.append("search_type_concept")
        elif "document" in query.lower() and search_type == "concept":
            optimized_search_type = "document"
            optimizations.append("search_type_document")
        
        optimization_info = {
            "applied": optimizations,
            "original_depth": max_depth,
            "optimized_depth": optimized_max_depth,
            "original_search_type": search_type,
            "optimized_search_type": optimized_search_type
        }
        
        logfire.info("Graph query optimized",
                    optimizations=optimizations,
                    depth_reduction=max_depth - optimized_max_depth)
        
        return optimized_query, optimized_search_type, optimized_max_depth, optimization_info

class ConnectionPool:
    """Connection pool for database connections."""
    
    def __init__(self, max_size: int = 20, timeout_ms: int = 5000):
        self.max_size = max_size
        self.timeout_ms = timeout_ms
        self.active_connections = 0
        self.semaphore = asyncio.Semaphore(max_size)
        self.connection_stats = {
            "created": 0,
            "reused": 0,
            "timeout": 0,
            "errors": 0
        }
    
    @logfire.instrument("acquire_connection")
    async def acquire(self) -> bool:
        """Acquire connection from pool."""
        try:
            acquired = await asyncio.wait_for(
                self.semaphore.acquire(),
                timeout=self.timeout_ms / 1000.0
            )
            if acquired:
                self.active_connections += 1
                self.connection_stats["reused"] += 1
                logfire.debug("Connection acquired", active=self.active_connections)
                return True
            return False
        except asyncio.TimeoutError:
            self.connection_stats["timeout"] += 1
            logfire.warning("Connection acquisition timeout")
            return False
        except Exception as e:
            self.connection_stats["errors"] += 1
            logfire.error("Connection acquisition error", error=str(e))
            return False
    
    @logfire.instrument("release_connection")
    async def release(self) -> None:
        """Release connection back to pool."""
        if self.active_connections > 0:
            self.active_connections -= 1
            self.semaphore.release()
            logfire.debug("Connection released", active=self.active_connections)
    
    def stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        return {
            "max_size": self.max_size,
            "active_connections": self.active_connections,
            "available_connections": self.max_size - self.active_connections,
            **self.connection_stats
        }

class PerformanceOptimizer:
    """Main performance optimization coordinator."""
    
    def __init__(self, config: PerformanceConfig = None):
        self.config = config or PerformanceConfig()
        
        # Caches
        self.query_cache = LRUCache(
            max_size=self.config.query_cache_size,
            ttl_seconds=self.config.cache_ttl_seconds
        )
        self.result_cache = LRUCache(
            max_size=self.config.result_cache_size,
            ttl_seconds=self.config.cache_ttl_seconds
        )
        self.embedding_cache = LRUCache(
            max_size=self.config.embedding_cache_size,
            ttl_seconds=self.config.cache_ttl_seconds * 2  # Embeddings last longer
        )
        self.concept_cache = LRUCache(
            max_size=self.config.concept_cache_size,
            ttl_seconds=self.config.cache_ttl_seconds
        )
        
        # Optimizers
        self.query_optimizer = QueryOptimizer(self.config)
        self.connection_pool = ConnectionPool(
            max_size=self.config.connection_pool_size,
            timeout_ms=self.config.connection_timeout_ms
        )
        
        # Metrics
        self.metrics = PerformanceMetrics()
        self.start_time = time.time()
        
        # Concurrency control
        self.query_semaphore = asyncio.Semaphore(self.config.max_concurrent_queries)
        self.active_queries = 0
        
        # Optimization state
        self.bottleneck_history = defaultdict(int)
        self.optimization_log = []
    
    def _generate_cache_key(self, operation: str, **kwargs) -> str:
        """Generate cache key for operation and parameters."""
        # Sort kwargs for consistent key generation
        sorted_params = sorted(kwargs.items())
        params_str = json.dumps(sorted_params, sort_keys=True)
        key_data = f"{operation}:{params_str}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    @logfire.instrument("cached_operation")
    async def cached_operation(
        self,
        cache_type: str,
        operation: str,
        operation_func,
        **kwargs
    ) -> Tuple[Any, bool]:
        """Execute operation with caching."""
        cache_key = self._generate_cache_key(operation, **kwargs)
        
        # Select appropriate cache
        cache = {
            "query": self.query_cache,
            "result": self.result_cache,
            "embedding": self.embedding_cache,
            "concept": self.concept_cache
        }.get(cache_type, self.query_cache)
        
        # Try cache first
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logfire.info("Cache hit", 
                        cache_type=cache_type,
                        operation=operation,
                        key=cache_key[:8])
            return cached_result, True
        
        # Execute operation
        start_time = time.time()
        try:
            result = await operation_func(**kwargs)
            execution_time = (time.time() - start_time) * 1000
            
            # Cache successful results
            cache.put(cache_key, result)
            
            logfire.info("Cache miss - operation executed",
                        cache_type=cache_type,
                        operation=operation,
                        execution_time_ms=execution_time,
                        key=cache_key[:8])
            
            return result, False
            
        except Exception as e:
            logfire.error("Cached operation failed",
                         cache_type=cache_type,
                         operation=operation,
                         error=str(e))
            raise
    
    @logfire.instrument("optimize_search_parameters")
    def optimize_search_parameters(
        self,
        query: str,
        query_type: str,
        limit: int = None,
        search_type: str = None,
        max_depth: int = None
    ) -> Dict[str, Any]:
        """Optimize search parameters based on query characteristics and performance targets."""
        optimizations = {
            "query": query,
            "query_type": query_type,
            "limit": limit,
            "search_type": search_type,
            "max_depth": max_depth,
            "applied_optimizations": []
        }
        
        # Apply optimization level settings
        if self.config.optimization_level == OptimizationLevel.AGGRESSIVE:
            if limit and limit > 50:
                optimizations["limit"] = 50
                optimizations["applied_optimizations"].append("aggressive_limit_reduction")
            
            if max_depth and max_depth > 2:
                optimizations["max_depth"] = 2
                optimizations["applied_optimizations"].append("aggressive_depth_reduction")
        
        elif self.config.optimization_level == OptimizationLevel.EXTREME:
            if limit and limit > 25:
                optimizations["limit"] = 25
                optimizations["applied_optimizations"].append("extreme_limit_reduction")
            
            if max_depth and max_depth > 1:
                optimizations["max_depth"] = 1
                optimizations["applied_optimizations"].append("extreme_depth_reduction")
        
        # Query-specific optimizations
        if "semantic" in query_type.lower():
            opt_query, opt_limit, opt_info = self.query_optimizer.optimize_semantic_query(
                query, limit or 50
            )
            optimizations["query"] = opt_query
            optimizations["limit"] = opt_limit
            optimizations["applied_optimizations"].extend(opt_info["applied"])
        
        if "graph" in query_type.lower() and search_type and max_depth:
            opt_query, opt_search_type, opt_max_depth, opt_info = self.query_optimizer.optimize_graph_query(
                query, search_type, max_depth
            )
            optimizations["query"] = opt_query
            optimizations["search_type"] = opt_search_type
            optimizations["max_depth"] = opt_max_depth
            optimizations["applied_optimizations"].extend(opt_info["applied"])
        
        logfire.info("Search parameters optimized",
                    original_query_length=len(query),
                    optimized_query_length=len(optimizations["query"]),
                    optimizations_applied=len(optimizations["applied_optimizations"]))
        
        return optimizations
    
    @logfire.instrument("execute_with_performance_monitoring")
    async def execute_with_performance_monitoring(
        self,
        operation_name: str,
        operation_func,
        **kwargs
    ) -> Tuple[Any, Dict[str, Any]]:
        """Execute operation with comprehensive performance monitoring."""
        # Acquire concurrency slot
        async with self.query_semaphore:
            self.active_queries += 1
            start_time = time.time()
            
            try:
                # Connection pool management
                connection_acquired = await self.connection_pool.acquire()
                if not connection_acquired:
                    raise RuntimeError("Could not acquire database connection")
                
                try:
                    # Execute with timeout
                    result = await asyncio.wait_for(
                        operation_func(**kwargs),
                        timeout=self.config.query_timeout_ms / 1000.0
                    )
                    
                    execution_time = (time.time() - start_time) * 1000
                    
                    # Update metrics
                    self.metrics.query_count += 1
                    self.metrics.total_query_time_ms += execution_time
                    self.metrics.avg_query_time_ms = (
                        self.metrics.total_query_time_ms / self.metrics.query_count
                    )
                    
                    # Performance analysis
                    performance_info = {
                        "execution_time_ms": execution_time,
                        "within_target": execution_time <= self.config.target_response_time_ms,
                        "active_queries": self.active_queries,
                        "operation": operation_name
                    }
                    
                    # Detect bottlenecks
                    if execution_time > self.config.target_response_time_ms:
                        bottleneck = f"slow_{operation_name}"
                        self.bottleneck_history[bottleneck] += 1
                        self.metrics.bottlenecks_detected.append(bottleneck)
                        
                        logfire.warning("Performance target missed",
                                      operation=operation_name,
                                      execution_time_ms=execution_time,
                                      target_ms=self.config.target_response_time_ms)
                    
                    logfire.info("Operation completed with monitoring",
                               operation=operation_name,
                               execution_time_ms=execution_time,
                               within_target=performance_info["within_target"])
                    
                    return result, performance_info
                    
                finally:
                    await self.connection_pool.release()
                    
            except asyncio.TimeoutError:
                self.bottleneck_history[f"timeout_{operation_name}"] += 1
                logfire.error("Operation timeout",
                            operation=operation_name,
                            timeout_ms=self.config.query_timeout_ms)
                raise
                
            except Exception as e:
                self.bottleneck_history[f"error_{operation_name}"] += 1
                logfire.error("Operation failed",
                            operation=operation_name,
                            error=str(e))
                raise
                
            finally:
                self.active_queries -= 1
    
    @logfire.instrument("adaptive_optimization")
    async def adaptive_optimization(self) -> None:
        """Apply adaptive optimizations based on performance history."""
        with logfire.span("Adaptive optimization analysis"):
            # Analyze bottlenecks
            total_operations = sum(self.bottleneck_history.values())
            if total_operations < 10:
                return  # Not enough data
            
            optimizations_applied = []
            
            # Detect frequent timeouts
            timeout_count = sum(count for key, count in self.bottleneck_history.items() 
                              if "timeout" in key)
            if timeout_count / total_operations > 0.1:  # >10% timeouts
                # Reduce query timeout
                old_timeout = self.config.query_timeout_ms
                self.config.query_timeout_ms = max(50, int(old_timeout * 0.8))
                optimizations_applied.append(f"timeout_reduction:{old_timeout}->{self.config.query_timeout_ms}")
            
            # Detect frequent slow operations
            slow_count = sum(count for key, count in self.bottleneck_history.items() 
                           if "slow" in key)
            if slow_count / total_operations > 0.2:  # >20% slow operations
                # Increase optimization level
                if self.config.optimization_level == OptimizationLevel.MINIMAL:
                    self.config.optimization_level = OptimizationLevel.BALANCED
                    optimizations_applied.append("optimization_level:minimal->balanced")
                elif self.config.optimization_level == OptimizationLevel.BALANCED:
                    self.config.optimization_level = OptimizationLevel.AGGRESSIVE
                    optimizations_applied.append("optimization_level:balanced->aggressive")
            
            # Analyze cache performance
            caches = {
                "query": self.query_cache,
                "result": self.result_cache,
                "embedding": self.embedding_cache,
                "concept": self.concept_cache
            }
            
            for cache_name, cache in caches.items():
                stats = cache.stats()
                if stats["hit_rate"] < 0.5 and stats["size"] < stats["max_size"] * 0.8:
                    # Low hit rate but cache not full - increase TTL
                    cache.ttl_seconds = min(7200, int(cache.ttl_seconds * 1.2))
                    optimizations_applied.append(f"{cache_name}_cache_ttl_increase")
            
            if optimizations_applied:
                self.metrics.optimization_applied.extend(optimizations_applied)
                logfire.info("Adaptive optimizations applied",
                           optimizations=optimizations_applied,
                           bottleneck_count=len(self.bottleneck_history))
    
    @logfire.instrument("get_performance_report")
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        uptime_seconds = time.time() - self.start_time
        
        # Cache statistics
        cache_stats = {
            "query_cache": self.query_cache.stats(),
            "result_cache": self.result_cache.stats(),
            "embedding_cache": self.embedding_cache.stats(),
            "concept_cache": self.concept_cache.stats()
        }
        
        # Overall cache performance
        total_hits = sum(stats["hits"] for stats in cache_stats.values())
        total_misses = sum(stats["misses"] for stats in cache_stats.values())
        overall_hit_rate = total_hits / (total_hits + total_misses) if (total_hits + total_misses) > 0 else 0.0
        
        # Update metrics
        self.metrics.cache_hits = total_hits
        self.metrics.cache_misses = total_misses
        self.metrics.cache_hit_rate = overall_hit_rate
        self.metrics.concurrent_queries = self.active_queries
        
        # Performance analysis
        target_met = (
            self.metrics.avg_query_time_ms <= self.config.target_response_time_ms and
            overall_hit_rate >= self.config.target_cache_hit_rate
        )
        
        # Bottleneck analysis
        top_bottlenecks = sorted(
            self.bottleneck_history.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        report = {
            "performance_metrics": asdict(self.metrics),
            "cache_statistics": cache_stats,
            "connection_pool": self.connection_pool.stats(),
            "configuration": asdict(self.config),
            "runtime_info": {
                "uptime_seconds": uptime_seconds,
                "queries_per_second": self.metrics.query_count / max(uptime_seconds, 1),
                "target_met": target_met,
                "active_queries": self.active_queries
            },
            "bottleneck_analysis": {
                "top_bottlenecks": top_bottlenecks,
                "total_issues": sum(self.bottleneck_history.values()),
                "issue_rate": sum(self.bottleneck_history.values()) / max(self.metrics.query_count, 1)
            }
        }
        
        logfire.info("Performance report generated",
                    avg_query_time_ms=self.metrics.avg_query_time_ms,
                    cache_hit_rate=overall_hit_rate,
                    target_met=target_met,
                    total_queries=self.metrics.query_count)
        
        return report
    
    @logfire.instrument("clear_caches")
    def clear_caches(self) -> None:
        """Clear all caches."""
        self.query_cache.clear()
        self.result_cache.clear()
        self.embedding_cache.clear()
        self.concept_cache.clear()
        
        logfire.info("All caches cleared")
    
    @logfire.instrument("warmup_caches")
    async def warmup_caches(self, common_queries: List[str] = None) -> None:
        """Warm up caches with common queries."""
        if not common_queries:
            common_queries = [
                "FastAPI authentication",
                "Neo4j graph database",
                "SurrealDB vector search",
                "Python async programming",
                "API security best practices"
            ]
        
        with logfire.span("Cache warmup", query_count=len(common_queries)):
            logfire.info("Starting cache warmup", queries=len(common_queries))
            
            # Simulate cache warming (in real implementation, would execute actual queries)
            for query in common_queries:
                cache_key = self._generate_cache_key("warmup", query=query)
                self.query_cache.put(cache_key, {"warmed": True, "query": query})
            
            logfire.info("Cache warmup completed", warmed_queries=len(common_queries))

# Utility functions
def create_performance_optimizer(
    optimization_level: OptimizationLevel = OptimizationLevel.BALANCED,
    target_response_time_ms: float = 100.0
) -> PerformanceOptimizer:
    """Create performance optimizer with specified settings."""
    config = PerformanceConfig(
        optimization_level=optimization_level,
        target_response_time_ms=target_response_time_ms
    )
    return PerformanceOptimizer(config)

def analyze_query_performance(query_times: List[float], target_ms: float = 100.0) -> Dict[str, Any]:
    """Analyze query performance statistics."""
    if not query_times:
        return {"error": "No query times provided"}
    
    query_times = np.array(query_times)
    
    analysis = {
        "total_queries": len(query_times),
        "avg_time_ms": float(np.mean(query_times)),
        "median_time_ms": float(np.median(query_times)),
        "p95_time_ms": float(np.percentile(query_times, 95)),
        "p99_time_ms": float(np.percentile(query_times, 99)),
        "min_time_ms": float(np.min(query_times)),
        "max_time_ms": float(np.max(query_times)),
        "std_dev_ms": float(np.std(query_times)),
        "target_ms": target_ms,
        "queries_within_target": int(np.sum(query_times <= target_ms)),
        "target_success_rate": float(np.mean(query_times <= target_ms)),
        "outliers": int(np.sum(query_times > np.percentile(query_times, 95)))
    }
    
    # Performance assessment
    if analysis["target_success_rate"] >= 0.95:
        analysis["performance_grade"] = "Excellent"
    elif analysis["target_success_rate"] >= 0.8:
        analysis["performance_grade"] = "Good"
    elif analysis["target_success_rate"] >= 0.6:
        analysis["performance_grade"] = "Fair"
    else:
        analysis["performance_grade"] = "Poor"
    
    return analysis

if __name__ == "__main__":
    # Example usage
    async def main():
        optimizer = create_performance_optimizer(
            OptimizationLevel.BALANCED,
            target_response_time_ms=100.0
        )
        
        # Simulate some operations
        async def mock_operation(**kwargs):
            await asyncio.sleep(0.05)  # 50ms operation
            return {"result": "success"}
        
        # Test cached operation
        result, was_cached = await optimizer.cached_operation(
            "query", "test_operation", mock_operation, query="test"
        )
        
        print(f"Operation result: {result}, was cached: {was_cached}")
        
        # Generate performance report
        report = optimizer.get_performance_report()
        print(f"Performance report: {report['runtime_info']}")
    
    asyncio.run(main())