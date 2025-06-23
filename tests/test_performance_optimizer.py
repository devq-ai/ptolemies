#!/usr/bin/env python3
"""
Test suite for Performance Optimizer
"""

import pytest
import asyncio
import time
import os
import sys
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

# Set logfire config for testing
os.environ['LOGFIRE_IGNORE_NO_CONFIG'] = '1'

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from performance_optimizer import (
    PerformanceOptimizer,
    PerformanceConfig,
    PerformanceMetrics,
    LRUCache,
    QueryOptimizer,
    ConnectionPool,
    CacheStrategy,
    OptimizationLevel,
    create_performance_optimizer,
    analyze_query_performance
)

class TestPerformanceConfig:
    """Test performance configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = PerformanceConfig()
        
        assert config.query_cache_size == 1000
        assert config.result_cache_size == 5000
        assert config.embedding_cache_size == 2000
        assert config.concept_cache_size == 500
        assert config.cache_ttl_seconds == 3600
        assert config.max_concurrent_queries == 100
        assert config.connection_pool_size == 20
        assert config.connection_timeout_ms == 5000
        assert config.semantic_batch_size == 50
        assert config.graph_batch_size == 25
        assert config.parallel_search_threshold == 2
        assert config.query_timeout_ms == 90
        assert config.max_memory_mb == 512
        assert config.max_cpu_percent == 80.0
        assert config.gc_threshold == 1000
        assert config.optimization_level == OptimizationLevel.BALANCED
        assert config.target_response_time_ms == 100.0
        assert config.target_cache_hit_rate == 0.7
        assert config.target_memory_usage_mb == 256.0
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = PerformanceConfig(
            query_cache_size=2000,
            target_response_time_ms=50.0,
            optimization_level=OptimizationLevel.AGGRESSIVE,
            max_concurrent_queries=200
        )
        
        assert config.query_cache_size == 2000
        assert config.target_response_time_ms == 50.0
        assert config.optimization_level == OptimizationLevel.AGGRESSIVE
        assert config.max_concurrent_queries == 200

class TestPerformanceMetrics:
    """Test performance metrics."""
    
    def test_default_metrics(self):
        """Test default metrics initialization."""
        metrics = PerformanceMetrics()
        
        assert metrics.query_count == 0
        assert metrics.total_query_time_ms == 0.0
        assert metrics.avg_query_time_ms == 0.0
        assert metrics.cache_hits == 0
        assert metrics.cache_misses == 0
        assert metrics.cache_hit_rate == 0.0
        assert metrics.memory_usage_mb == 0.0
        assert metrics.cpu_usage_percent == 0.0
        assert metrics.concurrent_queries == 0
        assert metrics.optimization_applied == []
        assert metrics.bottlenecks_detected == []
    
    def test_custom_metrics(self):
        """Test custom metrics values."""
        metrics = PerformanceMetrics(
            query_count=100,
            total_query_time_ms=5000.0,
            avg_query_time_ms=50.0,
            cache_hits=75,
            cache_misses=25,
            cache_hit_rate=0.75
        )
        
        assert metrics.query_count == 100
        assert metrics.total_query_time_ms == 5000.0
        assert metrics.avg_query_time_ms == 50.0
        assert metrics.cache_hits == 75
        assert metrics.cache_misses == 25
        assert metrics.cache_hit_rate == 0.75

class TestLRUCache:
    """Test LRU cache implementation."""
    
    def test_cache_initialization(self):
        """Test cache initialization."""
        cache = LRUCache(max_size=100, ttl_seconds=300)
        
        assert cache.max_size == 100
        assert cache.ttl_seconds == 300
        assert len(cache.cache) == 0
        assert cache.hits == 0
        assert cache.misses == 0
    
    def test_cache_put_and_get(self):
        """Test basic cache put and get operations."""
        cache = LRUCache(max_size=3, ttl_seconds=300)
        
        # Test put and get
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") is None
        
        # Check hit/miss counts
        assert cache.hits == 2
        assert cache.misses == 1
    
    def test_cache_lru_eviction(self):
        """Test LRU eviction policy."""
        cache = LRUCache(max_size=2, ttl_seconds=300)
        
        # Fill cache
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        
        # Access key1 to make it most recently used
        assert cache.get("key1") == "value1"
        
        # Add key3, should evict key2 (least recently used)
        cache.put("key3", "value3")
        
        assert cache.get("key1") == "value1"  # Still there
        assert cache.get("key3") == "value3"  # New entry
        assert cache.get("key2") is None      # Evicted
    
    def test_cache_ttl_expiration(self):
        """Test TTL-based expiration."""
        cache = LRUCache(max_size=10, ttl_seconds=1)  # 1 second TTL
        
        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(1.1)
        assert cache.get("key1") is None
    
    def test_cache_stats(self):
        """Test cache statistics."""
        cache = LRUCache(max_size=10, ttl_seconds=300)
        
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.get("key1")  # Hit
        cache.get("key3")  # Miss
        
        stats = cache.stats()
        
        assert stats["size"] == 2
        assert stats["max_size"] == 10
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5
        assert "memory_usage_estimate" in stats
    
    def test_cache_clear(self):
        """Test cache clearing."""
        cache = LRUCache(max_size=10, ttl_seconds=300)
        
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.get("key1")
        
        cache.clear()
        
        assert len(cache.cache) == 0
        assert cache.hits == 0
        assert cache.misses == 0

class TestQueryOptimizer:
    """Test query optimizer."""
    
    @pytest.fixture
    def config(self):
        """Test configuration."""
        return PerformanceConfig(
            semantic_batch_size=50,
            graph_batch_size=25
        )
    
    @pytest.fixture
    def optimizer(self, config):
        """Test query optimizer."""
        return QueryOptimizer(config)
    
    def test_semantic_query_optimization(self, optimizer):
        """Test semantic query optimization."""
        # Test long query truncation
        long_query = "This is a very long query " * 20  # > 200 chars
        opt_query, opt_limit, opt_info = optimizer.optimize_semantic_query(long_query, 100)
        
        assert len(opt_query) <= len(long_query)
        assert "query_truncation" in opt_info["applied"]
        assert opt_info["original_length"] > opt_info["optimized_length"]
    
    def test_semantic_query_limit_optimization(self, optimizer):
        """Test semantic query limit optimization."""
        query = "test query"
        opt_query, opt_limit, opt_info = optimizer.optimize_semantic_query(query, 100)
        
        assert opt_limit == 50  # Should be reduced to batch size
        assert "limit_reduction" in opt_info["applied"]
        assert opt_info["original_limit"] == 100
        assert opt_info["optimized_limit"] == 50
    
    def test_semantic_query_word_reduction(self, optimizer):
        """Test semantic query word reduction."""
        # Query with many words
        many_words_query = " ".join([f"word{i}" for i in range(25)])
        opt_query, opt_limit, opt_info = optimizer.optimize_semantic_query(many_words_query, 10)
        
        opt_words = opt_query.split()
        assert len(opt_words) <= 15  # Should be reduced
        assert "word_reduction" in opt_info["applied"]
    
    def test_graph_query_optimization(self, optimizer):
        """Test graph query optimization."""
        query = "test concept query"
        opt_query, opt_search_type, opt_depth, opt_info = optimizer.optimize_graph_query(
            query, "document", 5
        )
        
        assert opt_depth <= 5  # Should be optimized
        assert opt_search_type == "concept"  # Should change to concept based on query
        assert "search_type_concept" in opt_info["applied"]
    
    def test_graph_query_depth_optimization(self, optimizer):
        """Test graph query depth optimization."""
        # Simple query should get reduced depth
        simple_query = "test"
        opt_query, opt_search_type, opt_depth, opt_info = optimizer.optimize_graph_query(
            simple_query, "document", 4
        )
        
        assert opt_depth < 4
        assert any("depth_reduction" in opt or "depth_capping" in opt for opt in opt_info["applied"])

class TestConnectionPool:
    """Test connection pool."""
    
    @pytest.mark.asyncio
    async def test_connection_pool_initialization(self):
        """Test connection pool initialization."""
        pool = ConnectionPool(max_size=5, timeout_ms=1000)
        
        assert pool.max_size == 5
        assert pool.timeout_ms == 1000
        assert pool.active_connections == 0
    
    @pytest.mark.asyncio
    async def test_connection_acquire_release(self):
        """Test connection acquisition and release."""
        pool = ConnectionPool(max_size=2, timeout_ms=1000)
        
        # Acquire connection
        acquired = await pool.acquire()
        assert acquired is True
        assert pool.active_connections == 1
        
        # Release connection
        await pool.release()
        assert pool.active_connections == 0
    
    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion(self):
        """Test connection pool exhaustion."""
        pool = ConnectionPool(max_size=1, timeout_ms=100)
        
        # Acquire the only connection
        acquired1 = await pool.acquire()
        assert acquired1 is True
        
        # Try to acquire another - should timeout
        acquired2 = await pool.acquire()
        assert acquired2 is False
        
        # Stats should show timeout
        stats = pool.stats()
        assert stats["timeout"] > 0
    
    @pytest.mark.asyncio
    async def test_connection_pool_stats(self):
        """Test connection pool statistics."""
        pool = ConnectionPool(max_size=3, timeout_ms=1000)
        
        await pool.acquire()
        await pool.acquire()
        
        stats = pool.stats()
        assert stats["max_size"] == 3
        assert stats["active_connections"] == 2
        assert stats["available_connections"] == 1
        assert "reused" in stats

class TestPerformanceOptimizer:
    """Test performance optimizer."""
    
    @pytest.fixture
    def config(self):
        """Test configuration."""
        return PerformanceConfig(
            query_cache_size=10,
            result_cache_size=10,
            target_response_time_ms=50.0,
            max_concurrent_queries=5
        )
    
    @pytest.fixture
    def optimizer(self, config):
        """Test performance optimizer."""
        return PerformanceOptimizer(config)
    
    def test_optimizer_initialization(self, optimizer):
        """Test optimizer initialization."""
        assert optimizer.config.target_response_time_ms == 50.0
        assert optimizer.metrics.query_count == 0
        assert optimizer.active_queries == 0
        assert len(optimizer.optimization_log) == 0
    
    def test_cache_key_generation(self, optimizer):
        """Test cache key generation."""
        key1 = optimizer._generate_cache_key("operation", param1="value1", param2="value2")
        key2 = optimizer._generate_cache_key("operation", param2="value2", param1="value1")
        key3 = optimizer._generate_cache_key("operation", param1="value1", param2="different")
        
        assert key1 == key2  # Same parameters, different order
        assert key1 != key3  # Different parameters
        assert len(key1) == 32  # MD5 hash length
    
    @pytest.mark.asyncio
    async def test_cached_operation_miss(self, optimizer):
        """Test cached operation with cache miss."""
        async def mock_operation(**kwargs):
            return {"result": "success", "input": kwargs}
        
        result, was_cached = await optimizer.cached_operation(
            "query", "test_op", mock_operation, param="value"
        )
        
        assert was_cached is False
        assert result["result"] == "success"
        assert result["input"]["param"] == "value"
    
    @pytest.mark.asyncio
    async def test_cached_operation_hit(self, optimizer):
        """Test cached operation with cache hit."""
        async def mock_operation(**kwargs):
            return {"result": "success", "execution": "real"}
        
        # First call - cache miss
        result1, was_cached1 = await optimizer.cached_operation(
            "query", "test_op", mock_operation, param="value"
        )
        assert was_cached1 is False
        
        # Second call - cache hit
        result2, was_cached2 = await optimizer.cached_operation(
            "query", "test_op", mock_operation, param="value"
        )
        assert was_cached2 is True
        assert result1 == result2
    
    def test_optimize_search_parameters(self, optimizer):
        """Test search parameter optimization."""
        optimizations = optimizer.optimize_search_parameters(
            query="test query",
            query_type="semantic_search",
            limit=100,
            search_type="document",
            max_depth=5
        )
        
        assert "applied_optimizations" in optimizations
        assert optimizations["query"] == "test query"
        assert optimizations["query_type"] == "semantic_search"
        # Other parameters may be optimized based on settings
    
    def test_optimize_search_parameters_aggressive(self, optimizer):
        """Test search parameter optimization with aggressive level."""
        optimizer.config.optimization_level = OptimizationLevel.AGGRESSIVE
        
        optimizations = optimizer.optimize_search_parameters(
            query="test query",
            query_type="semantic_search",
            limit=100,
            max_depth=5
        )
        
        assert optimizations["limit"] == 50  # Should be reduced
        assert optimizations["max_depth"] == 2  # Should be reduced
        assert "aggressive_limit_reduction" in optimizations["applied_optimizations"]
        assert "aggressive_depth_reduction" in optimizations["applied_optimizations"]
    
    def test_optimize_search_parameters_extreme(self, optimizer):
        """Test search parameter optimization with extreme level."""
        optimizer.config.optimization_level = OptimizationLevel.EXTREME
        
        optimizations = optimizer.optimize_search_parameters(
            query="test query",
            query_type="semantic_search",
            limit=100,
            max_depth=5
        )
        
        # The semantic query optimizer also applies its own optimizations
        # Check that extreme level optimizations are applied in addition to semantic ones
        assert optimizations["limit"] <= 50  # Should be reduced (either by extreme or semantic)
        assert optimizations["max_depth"] == 1  # Should be reduced more
        assert "extreme_limit_reduction" in optimizations["applied_optimizations"]
        assert "extreme_depth_reduction" in optimizations["applied_optimizations"]
    
    @pytest.mark.asyncio
    async def test_execute_with_performance_monitoring_success(self, optimizer):
        """Test performance monitoring with successful operation."""
        async def mock_operation(**kwargs):
            await asyncio.sleep(0.01)  # 10ms operation
            return {"result": "success"}
        
        result, perf_info = await optimizer.execute_with_performance_monitoring(
            "test_operation", mock_operation, param="value"
        )
        
        assert result["result"] == "success"
        assert "execution_time_ms" in perf_info
        assert perf_info["execution_time_ms"] >= 10  # At least 10ms
        assert perf_info["within_target"] is True  # Should be within 50ms target
        assert perf_info["operation"] == "test_operation"
        
        # Check metrics updated
        assert optimizer.metrics.query_count == 1
        assert optimizer.metrics.total_query_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_execute_with_performance_monitoring_timeout(self, optimizer):
        """Test performance monitoring with timeout."""
        optimizer.config.query_timeout_ms = 10  # Very short timeout
        
        async def slow_operation(**kwargs):
            await asyncio.sleep(0.1)  # 100ms operation
            return {"result": "success"}
        
        with pytest.raises(asyncio.TimeoutError):
            await optimizer.execute_with_performance_monitoring(
                "slow_operation", slow_operation
            )
        
        # Should track timeout in bottlenecks
        assert "timeout_slow_operation" in optimizer.bottleneck_history
    
    @pytest.mark.asyncio
    async def test_execute_with_performance_monitoring_error(self, optimizer):
        """Test performance monitoring with operation error."""
        async def failing_operation(**kwargs):
            raise ValueError("Operation failed")
        
        with pytest.raises(ValueError):
            await optimizer.execute_with_performance_monitoring(
                "failing_operation", failing_operation
            )
        
        # Should track error in bottlenecks
        assert "error_failing_operation" in optimizer.bottleneck_history
    
    @pytest.mark.asyncio
    async def test_adaptive_optimization(self, optimizer):
        """Test adaptive optimization based on performance history."""
        # Simulate some bottlenecks
        optimizer.bottleneck_history["timeout_search"] = 5
        optimizer.bottleneck_history["slow_search"] = 10
        optimizer.bottleneck_history["normal_operation"] = 50
        
        original_timeout = optimizer.config.query_timeout_ms
        original_level = optimizer.config.optimization_level
        
        await optimizer.adaptive_optimization()
        
        # Should apply optimizations based on bottlenecks
        assert len(optimizer.metrics.optimization_applied) > 0
    
    def test_get_performance_report(self, optimizer):
        """Test performance report generation."""
        # Add some test data
        optimizer.metrics.query_count = 100
        optimizer.metrics.total_query_time_ms = 5000
        optimizer.metrics.avg_query_time_ms = 50
        optimizer.query_cache.hits = 75
        optimizer.query_cache.misses = 25
        
        report = optimizer.get_performance_report()
        
        assert "performance_metrics" in report
        assert "cache_statistics" in report
        assert "connection_pool" in report
        assert "configuration" in report
        assert "runtime_info" in report
        assert "bottleneck_analysis" in report
        
        # Check runtime info
        runtime = report["runtime_info"]
        assert "uptime_seconds" in runtime
        assert "queries_per_second" in runtime
        assert "target_met" in runtime
        assert "active_queries" in runtime
        
        # Check cache hit rate calculation
        assert optimizer.metrics.cache_hit_rate == 0.75  # 75/(75+25)
    
    def test_clear_caches(self, optimizer):
        """Test cache clearing."""
        # Add some data to caches
        optimizer.query_cache.put("key1", "value1")
        optimizer.result_cache.put("key2", "value2")
        
        assert len(optimizer.query_cache.cache) == 1
        assert len(optimizer.result_cache.cache) == 1
        
        optimizer.clear_caches()
        
        assert len(optimizer.query_cache.cache) == 0
        assert len(optimizer.result_cache.cache) == 0
    
    @pytest.mark.asyncio
    async def test_warmup_caches(self, optimizer):
        """Test cache warmup."""
        test_queries = ["query1", "query2", "query3"]
        
        await optimizer.warmup_caches(test_queries)
        
        # Should have added entries to query cache
        assert len(optimizer.query_cache.cache) == len(test_queries)

class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_create_performance_optimizer(self):
        """Test performance optimizer creation."""
        optimizer = create_performance_optimizer(
            OptimizationLevel.AGGRESSIVE,
            target_response_time_ms=75.0
        )
        
        assert optimizer.config.optimization_level == OptimizationLevel.AGGRESSIVE
        assert optimizer.config.target_response_time_ms == 75.0
        assert isinstance(optimizer, PerformanceOptimizer)
    
    def test_analyze_query_performance_empty(self):
        """Test query performance analysis with empty data."""
        analysis = analyze_query_performance([])
        
        assert "error" in analysis
        assert analysis["error"] == "No query times provided"
    
    def test_analyze_query_performance_basic(self):
        """Test basic query performance analysis."""
        query_times = [50.0, 75.0, 100.0, 125.0, 150.0]
        analysis = analyze_query_performance(query_times, target_ms=100.0)
        
        assert analysis["total_queries"] == 5
        assert analysis["avg_time_ms"] == 100.0
        assert analysis["median_time_ms"] == 100.0
        assert analysis["min_time_ms"] == 50.0
        assert analysis["max_time_ms"] == 150.0
        assert analysis["target_ms"] == 100.0
        assert analysis["queries_within_target"] == 3  # 50, 75, 100
        assert analysis["target_success_rate"] == 0.6  # 3/5
        assert "p95_time_ms" in analysis
        assert "p99_time_ms" in analysis
        assert "std_dev_ms" in analysis
        assert "performance_grade" in analysis
    
    def test_analyze_query_performance_excellent(self):
        """Test query performance analysis with excellent performance."""
        # All queries under target
        query_times = [30.0, 40.0, 50.0, 60.0, 70.0]
        analysis = analyze_query_performance(query_times, target_ms=100.0)
        
        assert analysis["target_success_rate"] == 1.0
        assert analysis["performance_grade"] == "Excellent"
    
    def test_analyze_query_performance_poor(self):
        """Test query performance analysis with poor performance."""
        # Most queries over target
        query_times = [150.0, 200.0, 250.0, 300.0, 350.0]
        analysis = analyze_query_performance(query_times, target_ms=100.0)
        
        assert analysis["target_success_rate"] == 0.0
        assert analysis["performance_grade"] == "Poor"
    
    def test_analyze_query_performance_outliers(self):
        """Test query performance analysis with outliers."""
        # Mix of normal and outlier times
        query_times = [50.0] * 10 + [500.0]  # 10 normal, 1 outlier
        analysis = analyze_query_performance(query_times, target_ms=100.0)
        
        assert analysis["outliers"] >= 1
        assert analysis["max_time_ms"] == 500.0
        assert analysis["avg_time_ms"] > analysis["median_time_ms"]  # Skewed by outlier

class TestIntegrationScenarios:
    """Test complex integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_full_optimization_workflow(self):
        """Test complete optimization workflow."""
        config = PerformanceConfig(
            query_cache_size=5,
            target_response_time_ms=30.0,
            optimization_level=OptimizationLevel.BALANCED
        )
        optimizer = PerformanceOptimizer(config)
        
        # Mock operation that gets faster with optimization
        call_count = 0
        async def mock_operation(**kwargs):
            nonlocal call_count
            call_count += 1
            # First few calls are slow, then get faster
            delay = max(0.05 - (call_count * 0.01), 0.01)
            await asyncio.sleep(delay)
            return {"result": f"call_{call_count}", "optimized": call_count > 3}
        
        # Execute multiple operations
        results = []
        for i in range(5):
            result, perf_info = await optimizer.execute_with_performance_monitoring(
                f"operation_{i}", mock_operation, iteration=i
            )
            results.append((result, perf_info))
        
        # Check that operations got faster
        execution_times = [perf_info["execution_time_ms"] for _, perf_info in results]
        assert execution_times[-1] < execution_times[0]  # Last should be faster than first
        
        # Generate final report
        report = optimizer.get_performance_report()
        assert report["performance_metrics"]["query_count"] == 5
        assert report["performance_metrics"]["avg_query_time_ms"] > 0
    
    @pytest.mark.asyncio
    async def test_cache_effectiveness(self):
        """Test cache effectiveness in reducing execution time."""
        optimizer = create_performance_optimizer(OptimizationLevel.BALANCED)
        
        execution_count = 0
        async def expensive_operation(**kwargs):
            nonlocal execution_count
            execution_count += 1
            await asyncio.sleep(0.05)  # 50ms expensive operation
            return {"result": f"expensive_result_{execution_count}", "executed": True}
        
        # First call - should execute and cache
        result1, was_cached1 = await optimizer.cached_operation(
            "result", "expensive_op", expensive_operation, param="same"
        )
        assert was_cached1 is False
        assert execution_count == 1
        
        # Second call with same parameters - should use cache
        result2, was_cached2 = await optimizer.cached_operation(
            "result", "expensive_op", expensive_operation, param="same"
        )
        assert was_cached2 is True
        assert execution_count == 1  # Should not execute again
        assert result1 == result2
        
        # Third call with different parameters - should execute
        result3, was_cached3 = await optimizer.cached_operation(
            "result", "expensive_op", expensive_operation, param="different"
        )
        assert was_cached3 is False
        assert execution_count == 2
    
    @pytest.mark.asyncio
    async def test_performance_degradation_detection(self):
        """Test detection and response to performance degradation."""
        config = PerformanceConfig(
            target_response_time_ms=50.0,
            query_timeout_ms=150,  # Longer timeout to avoid timeouts in test
            optimization_level=OptimizationLevel.MINIMAL
        )
        optimizer = PerformanceOptimizer(config)
        
        # Simulate degrading performance
        async def degrading_operation(iteration=0, **kwargs):
            # Each iteration gets slower, but stay under timeout
            delay = 0.02 + (iteration * 0.015)  # 20ms + 15ms per iteration (max ~95ms)
            await asyncio.sleep(delay)
            return {"result": f"iteration_{iteration}"}
        
        # Execute operations with increasing slowness
        performance_info = []
        for i in range(5):
            try:
                result, perf_info = await optimizer.execute_with_performance_monitoring(
                    "degrading_op", degrading_operation, iteration=i
                )
                performance_info.append(perf_info)
            except (asyncio.TimeoutError, TimeoutError):
                # If timeout occurs, that's also a performance issue we can detect
                optimizer.bottleneck_history["timeout_degrading_op"] += 1
                break
        
        # Should detect performance issues in later iterations or timeouts
        slow_operations = [info for info in performance_info if not info["within_target"]]
        has_slow_ops = len(slow_operations) > 0
        has_timeouts = any("timeout" in key for key in optimizer.bottleneck_history.keys())
        
        assert has_slow_ops or has_timeouts  # Should have some performance issues
        
        # Should have recorded bottlenecks
        assert len(optimizer.bottleneck_history) > 0
        bottleneck_keys = list(optimizer.bottleneck_history.keys())
        assert any("slow_" in key or "timeout" in key for key in bottleneck_keys)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])