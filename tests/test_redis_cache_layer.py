#!/usr/bin/env python3
"""
Test suite for Redis Cache Layer
"""

import pytest
import asyncio
import os
import sys
import time
import json
import pickle
import gzip
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path

# Set logfire config for testing
os.environ['LOGFIRE_IGNORE_NO_CONFIG'] = '1'

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from redis_cache_layer import (
    RedisCacheLayer,
    RedisCacheConfig,
    CacheMetrics,
    CacheEntry,
    CircuitBreaker,
    RedisSerializer,
    CacheMode,
    SerializationFormat,
    CacheStrategy,
    redis_cached,
    create_redis_cache_layer,
    warm_cache_with_common_data
)

class TestRedisCacheConfig:
    """Test Redis cache configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = RedisCacheConfig()
        
        assert config.redis_url == "redis://localhost:6379"
        assert config.redis_password is None
        assert config.redis_db == 0
        assert config.upstash_url is None
        assert config.upstash_token is None
        assert config.cache_mode == CacheMode.HYBRID
        assert config.serialization_format == SerializationFormat.COMPRESSED_JSON
        assert config.cache_strategy == CacheStrategy.ADAPTIVE
        assert config.default_ttl_seconds == 3600
        assert config.max_key_size == 250
        assert config.max_value_size_mb == 16.0
        assert config.compression_threshold == 1024
        assert config.max_connections == 20
        assert config.connection_timeout_seconds == 5
        assert config.socket_keepalive is True
        assert config.socket_keepalive_options == {}
        assert config.max_retries == 3
        assert config.retry_delay_ms == 100
        assert config.circuit_breaker_threshold == 5
        assert config.circuit_breaker_timeout_seconds == 60
        assert config.key_prefix == "ptolemies"
        assert config.query_namespace == "query"
        assert config.result_namespace == "result"
        assert config.embedding_namespace == "embedding"
        assert config.concept_namespace == "concept"
        assert config.analytics_namespace == "analytics"
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = RedisCacheConfig(
            redis_url="redis://custom:6380",
            cache_mode=CacheMode.REDIS_ONLY,
            serialization_format=SerializationFormat.PICKLE,
            default_ttl_seconds=7200,
            max_connections=50
        )
        
        assert config.redis_url == "redis://custom:6380"
        assert config.cache_mode == CacheMode.REDIS_ONLY
        assert config.serialization_format == SerializationFormat.PICKLE
        assert config.default_ttl_seconds == 7200
        assert config.max_connections == 50
    
    def test_post_init_socket_options(self):
        """Test post_init sets empty socket options."""
        config = RedisCacheConfig()
        assert isinstance(config.socket_keepalive_options, dict)
        assert len(config.socket_keepalive_options) == 0

class TestCacheMetrics:
    """Test cache metrics."""
    
    def test_default_metrics(self):
        """Test default metrics initialization."""
        metrics = CacheMetrics()
        
        assert metrics.hits == 0
        assert metrics.misses == 0
        assert metrics.errors == 0
        assert metrics.timeouts == 0
        assert metrics.total_operations == 0
        assert metrics.total_bytes_read == 0
        assert metrics.total_bytes_written == 0
        assert metrics.avg_read_time_ms == 0.0
        assert metrics.avg_write_time_ms == 0.0
        assert metrics.hit_rate == 0.0
        assert metrics.error_rate == 0.0
        assert metrics.circuit_breaker_trips == 0
        assert metrics.compression_ratio == 0.0
    
    def test_custom_metrics(self):
        """Test custom metrics values."""
        metrics = CacheMetrics(
            hits=100,
            misses=25,
            errors=5,
            total_operations=130,
            total_bytes_read=1024000,
            total_bytes_written=2048000,
            avg_read_time_ms=15.5,
            avg_write_time_ms=25.8,
            hit_rate=0.8,
            error_rate=0.04,
            circuit_breaker_trips=2,
            compression_ratio=0.6
        )
        
        assert metrics.hits == 100
        assert metrics.misses == 25
        assert metrics.errors == 5
        assert metrics.total_operations == 130
        assert metrics.total_bytes_read == 1024000
        assert metrics.total_bytes_written == 2048000
        assert metrics.avg_read_time_ms == 15.5
        assert metrics.avg_write_time_ms == 25.8
        assert metrics.hit_rate == 0.8
        assert metrics.error_rate == 0.04
        assert metrics.circuit_breaker_trips == 2
        assert metrics.compression_ratio == 0.6

class TestCacheEntry:
    """Test cache entry."""
    
    def test_cache_entry_creation(self):
        """Test cache entry creation."""
        entry = CacheEntry(
            key="test_key",
            value={"data": "test"},
            ttl_seconds=3600,
            created_at=time.time(),
            accessed_at=time.time(),
            access_count=5,
            size_bytes=1024,
            compressed=True,
            namespace="test"
        )
        
        assert entry.key == "test_key"
        assert entry.value == {"data": "test"}
        assert entry.ttl_seconds == 3600
        assert entry.access_count == 5
        assert entry.size_bytes == 1024
        assert entry.compressed is True
        assert entry.namespace == "test"
    
    def test_cache_entry_defaults(self):
        """Test cache entry with default values."""
        entry = CacheEntry(
            key="test_key",
            value="test_value"
        )
        
        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.ttl_seconds is None
        assert entry.created_at is None
        assert entry.accessed_at is None
        assert entry.access_count == 0
        assert entry.size_bytes == 0
        assert entry.compressed is False
        assert entry.namespace == "default"

class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initialization."""
        breaker = CircuitBreaker(threshold=10, timeout_seconds=120)
        
        assert breaker.threshold == 10
        assert breaker.timeout_seconds == 120
        assert breaker.failure_count == 0
        assert breaker.last_failure_time == 0
        assert breaker.state == "CLOSED"
    
    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state."""
        breaker = CircuitBreaker()
        
        assert breaker.can_execute() is True
        
        # Record a few failures - should stay closed
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.can_execute() is True
        assert breaker.state == "CLOSED"
    
    def test_circuit_breaker_open_state(self):
        """Test circuit breaker opening."""
        breaker = CircuitBreaker(threshold=3, timeout_seconds=1)
        
        # Record enough failures to open circuit
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_failure()
        
        assert breaker.state == "OPEN"
        assert breaker.can_execute() is False
    
    def test_circuit_breaker_half_open_state(self):
        """Test circuit breaker half-open state."""
        breaker = CircuitBreaker(threshold=2, timeout_seconds=0.1)
        
        # Open the circuit
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == "OPEN"
        
        # Wait for timeout
        time.sleep(0.2)
        
        # Should now be half-open
        assert breaker.can_execute() is True
        assert breaker.state == "HALF_OPEN"
    
    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery."""
        breaker = CircuitBreaker(threshold=2)
        
        # Open the circuit
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == "OPEN"
        
        # Record success should close circuit
        breaker.record_success()
        assert breaker.state == "CLOSED"
        assert breaker.failure_count == 0

class TestRedisSerializer:
    """Test Redis serializer."""
    
    def test_json_serialization(self):
        """Test JSON serialization."""
        serializer = RedisSerializer(SerializationFormat.JSON)
        
        data = {"key": "value", "number": 42}
        serialized, compressed = serializer.serialize(data)
        
        assert isinstance(serialized, bytes)
        assert compressed is False
        
        deserialized = serializer.deserialize(serialized, compressed)
        assert deserialized == data
    
    def test_pickle_serialization(self):
        """Test pickle serialization."""
        serializer = RedisSerializer(SerializationFormat.PICKLE)
        
        data = {"key": "value", "complex": [1, 2, {"nested": True}]}
        serialized, compressed = serializer.serialize(data)
        
        assert isinstance(serialized, bytes)
        assert compressed is False
        
        deserialized = serializer.deserialize(serialized, compressed)
        assert deserialized == data
    
    def test_compressed_json_serialization(self):
        """Test compressed JSON serialization."""
        serializer = RedisSerializer(SerializationFormat.COMPRESSED_JSON)
        
        # Large data that will trigger compression
        large_data = {"data": "x" * 2000}
        serialized, compressed = serializer.serialize(large_data, compress_threshold=1000)
        
        assert isinstance(serialized, bytes)
        assert compressed is True
        
        deserialized = serializer.deserialize(serialized, compressed)
        assert deserialized == large_data
    
    def test_compressed_pickle_serialization(self):
        """Test compressed pickle serialization."""
        serializer = RedisSerializer(SerializationFormat.COMPRESSED_PICKLE)
        
        # Large data that will trigger compression
        large_data = {"items": ["item_" + str(i) for i in range(1000)]}
        serialized, compressed = serializer.serialize(large_data, compress_threshold=500)
        
        assert isinstance(serialized, bytes)
        assert compressed is True
        
        deserialized = serializer.deserialize(serialized, compressed)
        assert deserialized == large_data
    
    def test_serialization_no_compression_small_data(self):
        """Test that small data doesn't get compressed."""
        serializer = RedisSerializer(SerializationFormat.COMPRESSED_JSON)
        
        small_data = {"key": "value"}
        serialized, compressed = serializer.serialize(small_data, compress_threshold=1000)
        
        assert compressed is False
    
    def test_serialization_error_handling(self):
        """Test serialization error handling."""
        # Create a serializer without default handling
        serializer = RedisSerializer(SerializationFormat.JSON)
        
        # Mock json.dumps to raise an error
        with patch('json.dumps') as mock_dumps:
            mock_dumps.side_effect = TypeError("Test serialization error")
            
            with pytest.raises(TypeError):
                serializer.serialize({"test": "data"})
    
    def test_deserialization_error_handling(self):
        """Test deserialization error handling."""
        serializer = RedisSerializer(SerializationFormat.JSON)
        
        # Try to deserialize invalid JSON
        with pytest.raises(json.JSONDecodeError):
            serializer.deserialize(b"invalid json", False)

class TestRedisCacheLayer:
    """Test Redis cache layer functionality."""
    
    @pytest.fixture
    def config(self):
        """Test configuration."""
        return RedisCacheConfig(
            cache_mode=CacheMode.LOCAL_ONLY,  # Use local only for testing
            default_ttl_seconds=3600,
            max_key_size=100
        )
    
    @pytest.fixture
    def cache_layer(self, config):
        """Test cache layer."""
        return RedisCacheLayer(config)
    
    def test_cache_layer_initialization(self, cache_layer):
        """Test cache layer initialization."""
        assert cache_layer.config.cache_mode == CacheMode.LOCAL_ONLY
        assert cache_layer.redis_client is None
        assert isinstance(cache_layer.serializer, RedisSerializer)
        assert isinstance(cache_layer.circuit_breaker, CircuitBreaker)
        assert isinstance(cache_layer.metrics, CacheMetrics)
        assert isinstance(cache_layer.local_cache, dict)
        assert cache_layer.start_time > 0
    
    def test_environment_initialization(self):
        """Test environment variable initialization."""
        with patch.dict(os.environ, {
            'UPSTASH_REDIS_REST_URL': 'https://test.upstash.io',
            'UPSTASH_REDIS_REST_TOKEN': 'test_token',
            'REDIS_URL': 'redis://test:6379',
            'REDIS_PASSWORD': 'test_password'
        }):
            cache_layer = RedisCacheLayer()
            
            assert cache_layer.config.upstash_url == 'https://test.upstash.io'
            assert cache_layer.config.upstash_token == 'test_token'
            assert cache_layer.config.redis_url == 'redis://test:6379'
            assert cache_layer.config.redis_password == 'test_password'
    
    @pytest.mark.asyncio
    async def test_connect_upstash(self):
        """Test connecting to Upstash Redis."""
        config = RedisCacheConfig(
            upstash_url="https://test.upstash.io",
            upstash_token="test_token"
        )
        cache_layer = RedisCacheLayer(config)
        
        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_redis = AsyncMock()
            mock_redis.ping.return_value = True
            mock_from_url.return_value = mock_redis
            
            connected = await cache_layer.connect()
            
            assert connected is True
            assert cache_layer.redis_client == mock_redis
            mock_from_url.assert_called_once()
            mock_redis.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect_standard_redis(self):
        """Test connecting to standard Redis."""
        config = RedisCacheConfig(
            redis_url="redis://localhost:6379",
            redis_password="password"
        )
        cache_layer = RedisCacheLayer(config)
        
        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_redis = AsyncMock()
            mock_redis.ping.return_value = True
            mock_from_url.return_value = mock_redis
            
            connected = await cache_layer.connect()
            
            assert connected is True
            assert cache_layer.redis_client == mock_redis
            mock_from_url.assert_called_once()
            mock_redis.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test connection failure handling."""
        cache_layer = RedisCacheLayer()
        
        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_from_url.side_effect = Exception("Connection failed")
            
            connected = await cache_layer.connect()
            
            assert connected is False
            assert cache_layer.redis_client is None
    
    def test_generate_cache_key(self, cache_layer):
        """Test cache key generation."""
        key1 = cache_layer._generate_cache_key("test", "simple_key")
        key2 = cache_layer._generate_cache_key("test", "simple_key")
        key3 = cache_layer._generate_cache_key("test", "different_key")
        
        assert key1 == key2  # Same inputs should generate same key
        assert key1 != key3  # Different inputs should generate different keys
        assert key1.startswith("ptolemies:test:")
    
    def test_generate_cache_key_long_key(self, cache_layer):
        """Test cache key generation with long key."""
        long_key = "x" * 300  # Longer than max_key_size
        cache_key = cache_layer._generate_cache_key("test", long_key)
        
        # Should hash long keys
        assert len(cache_key.split(":")[-1]) == 32  # MD5 hash length
    
    @pytest.mark.asyncio
    async def test_local_cache_get_miss(self, cache_layer):
        """Test local cache get with miss."""
        result, found = await cache_layer.get("nonexistent_key", "test")
        
        assert result is None
        assert found is False
        assert cache_layer.metrics.misses == 1
        assert cache_layer.metrics.total_operations == 1
    
    @pytest.mark.asyncio
    async def test_local_cache_set_and_get(self, cache_layer):
        """Test local cache set and get."""
        test_data = {"message": "Hello World"}
        
        # Set value
        success = await cache_layer.set("test_key", test_data, "test")
        assert success is True
        
        # Get value
        result, found = await cache_layer.get("test_key", "test")
        assert result == test_data
        assert found is True
        assert cache_layer.metrics.hits == 1
    
    @pytest.mark.asyncio
    async def test_local_cache_delete(self, cache_layer):
        """Test local cache delete."""
        test_data = {"message": "Hello World"}
        
        # Set and verify
        await cache_layer.set("test_key", test_data, "test")
        result, found = await cache_layer.get("test_key", "test")
        assert found is True
        
        # Delete
        deleted = await cache_layer.delete("test_key", "test")
        assert deleted is True
        
        # Verify deletion
        result, found = await cache_layer.get("test_key", "test")
        assert found is False
    
    @pytest.mark.asyncio
    async def test_local_cache_exists(self, cache_layer):
        """Test local cache exists check."""
        test_data = {"message": "Hello World"}
        
        # Check non-existent key
        exists = await cache_layer.exists("test_key", "test")
        assert exists is False
        
        # Set value
        await cache_layer.set("test_key", test_data, "test")
        
        # Check existing key
        exists = await cache_layer.exists("test_key", "test")
        assert exists is True
    
    @pytest.mark.asyncio
    async def test_clear_namespace(self, cache_layer):
        """Test namespace clearing."""
        # Set values in different namespaces
        await cache_layer.set("key1", "value1", "test")
        await cache_layer.set("key2", "value2", "test")
        await cache_layer.set("key3", "value3", "other")
        
        # Clear test namespace
        cleared = await cache_layer.clear_namespace("test")
        assert cleared == 2
        
        # Verify test namespace cleared but other preserved
        result1, found1 = await cache_layer.get("key1", "test")
        result2, found2 = await cache_layer.get("key2", "test")
        result3, found3 = await cache_layer.get("key3", "other")
        
        assert found1 is False
        assert found2 is False
        assert found3 is True
    
    @pytest.mark.asyncio
    async def test_cache_stats(self, cache_layer):
        """Test cache statistics."""
        # Perform some operations
        await cache_layer.set("key1", "value1", "test")
        await cache_layer.get("key1", "test")  # Hit
        await cache_layer.get("key2", "test")  # Miss
        
        stats = await cache_layer.get_cache_stats()
        
        assert "cache_metrics" in stats
        assert "configuration" in stats
        assert "circuit_breaker" in stats
        assert "local_cache" in stats
        assert "runtime_info" in stats
        
        # Check metrics
        metrics = stats["cache_metrics"]
        assert metrics["hits"] >= 1
        assert metrics["misses"] >= 1
        assert metrics["total_operations"] >= 2
        
        # Check runtime info
        runtime = stats["runtime_info"]
        assert "uptime_seconds" in runtime
        assert "operations_per_second" in runtime
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self):
        """Test circuit breaker integration."""
        config = RedisCacheConfig(
            circuit_breaker_threshold=2,
            cache_mode=CacheMode.REDIS_ONLY
        )
        cache_layer = RedisCacheLayer(config)
        
        # Simulate circuit breaker opening
        cache_layer.circuit_breaker.record_failure()
        cache_layer.circuit_breaker.record_failure()
        
        # Operations should be skipped
        result, found = await cache_layer.get("test_key", "test")
        assert result is None
        assert found is False
        
        success = await cache_layer.set("test_key", "value", "test")
        assert success is False
    
    @pytest.mark.asyncio
    async def test_redis_operations_with_mock(self):
        """Test Redis operations with mocked Redis client."""
        config = RedisCacheConfig(cache_mode=CacheMode.REDIS_ONLY)
        cache_layer = RedisCacheLayer(config)
        
        # Mock Redis client
        mock_redis = AsyncMock()
        mock_pipeline = AsyncMock()
        mock_redis.pipeline.return_value = mock_pipeline
        
        # Mock pipeline methods
        mock_pipeline.get = Mock()
        mock_pipeline.setex = Mock()
        
        # Make execute return actual awaitable result for GET
        async def mock_execute_get():
            return [
                b'{"test": "data"}',  # Value
                b'{"compressed": false, "size_bytes": 16}'  # Metadata
            ]
        
        mock_pipeline.execute = mock_execute_get
        
        cache_layer.redis_client = mock_redis
        
        # Test get
        result, found = await cache_layer.get("test_key", "test")
        assert found is True
        assert result == {"test": "data"}
        
        # Test set - mock different execute for set operation
        async def mock_execute_set():
            return [True, True]  # Success for both operations
        
        mock_pipeline.execute = mock_execute_set
        success = await cache_layer.set("test_key", {"test": "data"}, "test")
        assert success is True
    
    @pytest.mark.asyncio
    async def test_value_size_limit(self, cache_layer):
        """Test value size limit enforcement."""
        # Create data larger than limit (disable compression to ensure size check works)
        cache_layer.config.max_value_size_mb = 0.1  # Set very small limit to 0.1MB
        cache_layer.config.compression_threshold = 999999999  # Disable compression
        large_string = "abcdefghij" * 50000  # Large varied string that won't compress well
        large_data = {"data": large_string}
        
        success = await cache_layer.set("large_key", large_data, "test")
        assert success is False  # Should reject oversized value
    
    @pytest.mark.asyncio
    async def test_ttl_expiration_simulation(self):
        """Test TTL expiration simulation."""
        config = RedisCacheConfig(cache_mode=CacheMode.LOCAL_ONLY)
        cache_layer = RedisCacheLayer(config)
        
        # Set value with short TTL
        test_data = {"message": "Hello World"}
        redis_key = cache_layer._generate_cache_key("test", "test_key")
        
        # Manually add to local cache with TTL
        entry = CacheEntry(
            key="test_key",
            value=test_data,
            ttl_seconds=1,  # 1 second TTL
            created_at=time.time() - 2,  # Created 2 seconds ago (expired)
            namespace="test"
        )
        cache_layer.local_cache[redis_key] = entry
        
        # Should not find expired entry
        result, found = await cache_layer.get("test_key", "test")
        assert found is False
        assert redis_key not in cache_layer.local_cache  # Should be removed
    
    @pytest.mark.asyncio
    async def test_close_connection(self, cache_layer):
        """Test closing Redis connection."""
        # Mock Redis client
        mock_redis = AsyncMock()
        cache_layer.redis_client = mock_redis
        
        await cache_layer.close()
        
        mock_redis.close.assert_called_once()
        assert cache_layer.redis_client is None

class TestRedisDecorator:
    """Test Redis caching decorator."""
    
    @pytest.mark.asyncio
    async def test_redis_cached_decorator(self):
        """Test the redis_cached decorator."""
        cache_layer = RedisCacheLayer(RedisCacheConfig(cache_mode=CacheMode.LOCAL_ONLY))
        
        call_count = 0
        
        @redis_cached(namespace="test", ttl_seconds=3600)
        async def expensive_function(param1, param2, cache_layer):
            nonlocal call_count
            call_count += 1
            return f"result_{param1}_{param2}"
        
        # First call - should execute function
        result1 = await expensive_function("a", "b", cache_layer=cache_layer)
        assert result1 == "result_a_b"
        assert call_count == 1
        
        # Second call with same params - should use cache
        result2 = await expensive_function("a", "b", cache_layer=cache_layer)
        assert result2 == "result_a_b"
        assert call_count == 1  # Function not called again
        
        # Third call with different params - should execute function
        result3 = await expensive_function("c", "d", cache_layer=cache_layer)
        assert result3 == "result_c_d"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_redis_cached_decorator_custom_key_generator(self):
        """Test the redis_cached decorator with custom key generator."""
        cache_layer = RedisCacheLayer(RedisCacheConfig(cache_mode=CacheMode.LOCAL_ONLY))
        
        def custom_key_generator(*args, **kwargs):
            return f"custom_{kwargs.get('param1', 'default')}"
        
        call_count = 0
        
        @redis_cached(namespace="test", key_generator=custom_key_generator)
        async def test_function(cache_layer, param1=None):
            nonlocal call_count
            call_count += 1
            return f"result_{param1}"
        
        # Test with custom key generation
        result1 = await test_function(cache_layer=cache_layer, param1="test")
        assert result1 == "result_test"
        assert call_count == 1
        
        # Should use cache
        result2 = await test_function(cache_layer=cache_layer, param1="test")
        assert result2 == "result_test"
        assert call_count == 1

class TestUtilityFunctions:
    """Test utility functions."""
    
    @pytest.mark.asyncio
    async def test_create_redis_cache_layer_default(self):
        """Test creating Redis cache layer with defaults."""
        with patch('redis_cache_layer.RedisCacheLayer.connect') as mock_connect:
            mock_connect.return_value = True
            
            cache_layer = await create_redis_cache_layer()
            
            assert isinstance(cache_layer, RedisCacheLayer)
            mock_connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_redis_cache_layer_custom_config(self):
        """Test creating Redis cache layer with custom config."""
        with patch('redis_cache_layer.RedisCacheLayer.connect') as mock_connect:
            mock_connect.return_value = True
            
            cache_layer = await create_redis_cache_layer(
                redis_url="redis://custom:6379",
                upstash_url="https://custom.upstash.io",
                upstash_token="custom_token"
            )
            
            assert isinstance(cache_layer, RedisCacheLayer)
            assert cache_layer.config.redis_url == "redis://custom:6379"
            assert cache_layer.config.upstash_url == "https://custom.upstash.io"
            assert cache_layer.config.upstash_token == "custom_token"
            mock_connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_redis_cache_layer_connection_failure(self):
        """Test creating Redis cache layer with connection failure."""
        with patch('redis_cache_layer.RedisCacheLayer.connect') as mock_connect:
            mock_connect.return_value = False
            
            cache_layer = await create_redis_cache_layer()
            
            assert isinstance(cache_layer, RedisCacheLayer)
            assert cache_layer.config.cache_mode == CacheMode.LOCAL_ONLY
    
    @pytest.mark.asyncio
    async def test_warm_cache_with_common_data_default(self):
        """Test cache warming with default data."""
        cache_layer = RedisCacheLayer(RedisCacheConfig(cache_mode=CacheMode.LOCAL_ONLY))
        
        await warm_cache_with_common_data(cache_layer)
        
        # Check that default queries were cached
        stats = await cache_layer.get_cache_stats()
        assert stats["cache_metrics"]["total_operations"] > 0
    
    @pytest.mark.asyncio
    async def test_warm_cache_with_custom_data(self):
        """Test cache warming with custom data."""
        cache_layer = RedisCacheLayer(RedisCacheConfig(cache_mode=CacheMode.LOCAL_ONLY))
        
        custom_queries = ["custom query 1", "custom query 2"]
        common_results = {"common_key": "common_value"}
        
        await warm_cache_with_common_data(
            cache_layer, 
            common_queries=custom_queries,
            common_results=common_results
        )
        
        # Verify custom data was cached
        result, found = await cache_layer.get("common_key", "common")
        assert found is True
        assert result == "common_value"

class TestIntegrationScenarios:
    """Test complex integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_hybrid_cache_mode_workflow(self):
        """Test complete hybrid cache workflow."""
        config = RedisCacheConfig(
            cache_mode=CacheMode.HYBRID,
            default_ttl_seconds=3600
        )
        cache_layer = RedisCacheLayer(config)
        
        # Mock Redis client for hybrid mode
        mock_redis = AsyncMock()
        mock_pipeline = AsyncMock()
        mock_redis.pipeline.return_value = mock_pipeline
        
        # Test local cache hit first
        test_data = {"hybrid": "test"}
        redis_key = cache_layer._generate_cache_key("test", "hybrid_key")
        
        # Add to local cache
        entry = CacheEntry(
            key="hybrid_key",
            value=test_data,
            created_at=time.time(),
            namespace="test"
        )
        cache_layer.local_cache[redis_key] = entry
        
        # Should hit local cache
        result, found = await cache_layer.get("hybrid_key", "test")
        assert found is True
        assert result == test_data
        assert cache_layer.metrics.hits == 1
    
    @pytest.mark.asyncio
    async def test_cache_performance_under_load(self):
        """Test cache performance under load."""
        cache_layer = RedisCacheLayer(RedisCacheConfig(cache_mode=CacheMode.LOCAL_ONLY))
        
        # Perform many operations
        num_operations = 100
        start_time = time.time()
        
        # Set many values
        for i in range(num_operations):
            await cache_layer.set(f"key_{i}", {"value": i}, "performance")
        
        # Get many values
        hit_count = 0
        for i in range(num_operations):
            result, found = await cache_layer.get(f"key_{i}", "performance")
            if found:
                hit_count += 1
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify performance
        assert hit_count == num_operations
        assert total_time < 1.0  # Should complete in under 1 second
        
        # Check statistics
        stats = await cache_layer.get_cache_stats()
        assert stats["cache_metrics"]["total_operations"] >= num_operations * 2
        assert stats["runtime_info"]["operations_per_second"] > 0
    
    @pytest.mark.asyncio
    async def test_error_recovery_and_metrics(self):
        """Test error recovery and metrics tracking."""
        config = RedisCacheConfig(
            cache_mode=CacheMode.REDIS_ONLY,
            circuit_breaker_threshold=3
        )
        cache_layer = RedisCacheLayer(config)
        
        # Mock Redis client that fails
        mock_redis = AsyncMock()
        mock_redis.pipeline.side_effect = Exception("Redis error")
        cache_layer.redis_client = mock_redis
        
        # Perform operations that will fail
        for i in range(5):
            result, found = await cache_layer.get(f"key_{i}", "error_test")
            assert found is False
        
        # Check error metrics
        assert cache_layer.metrics.errors >= 3
        assert cache_layer.circuit_breaker.state == "OPEN"
        
        # Operations should now be skipped due to circuit breaker
        result, found = await cache_layer.get("skip_key", "error_test")
        assert found is False
    
    @pytest.mark.asyncio
    async def test_namespace_isolation(self):
        """Test namespace isolation."""
        cache_layer = RedisCacheLayer(RedisCacheConfig(cache_mode=CacheMode.LOCAL_ONLY))
        
        # Set values in different namespaces
        await cache_layer.set("same_key", "value_1", "namespace_1")
        await cache_layer.set("same_key", "value_2", "namespace_2")
        await cache_layer.set("same_key", "value_3", "namespace_3")
        
        # Verify isolation
        result_1, found_1 = await cache_layer.get("same_key", "namespace_1")
        result_2, found_2 = await cache_layer.get("same_key", "namespace_2")
        result_3, found_3 = await cache_layer.get("same_key", "namespace_3")
        
        assert all([found_1, found_2, found_3])
        assert result_1 == "value_1"
        assert result_2 == "value_2"
        assert result_3 == "value_3"
        
        # Clear one namespace
        cleared = await cache_layer.clear_namespace("namespace_2")
        assert cleared == 1
        
        # Verify only target namespace cleared
        result_1, found_1 = await cache_layer.get("same_key", "namespace_1")
        result_2, found_2 = await cache_layer.get("same_key", "namespace_2")
        result_3, found_3 = await cache_layer.get("same_key", "namespace_3")
        
        assert found_1 is True
        assert found_2 is False
        assert found_3 is True

if __name__ == "__main__":
    pytest.main([__file__, "-v"])