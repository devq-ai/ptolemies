#!/usr/bin/env python3
"""
Redis Caching Layer for Ptolemies
Implements distributed caching with Redis/Upstash integration for improved performance
and scalability across multiple instances.
"""

import asyncio
import json
import pickle
import time
import hashlib
import gzip
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import os
from datetime import datetime, timedelta

import redis.asyncio as redis
import logfire
import numpy as np

# Configure Logfire
logfire.configure(send_to_logfire=False)  # Configure appropriately for production

class CacheMode(Enum):
    """Redis cache operation modes."""
    LOCAL_ONLY = "local_only"
    REDIS_ONLY = "redis_only"
    HYBRID = "hybrid"
    WRITE_THROUGH = "write_through"
    WRITE_BACK = "write_back"

class SerializationFormat(Enum):
    """Data serialization formats for Redis storage."""
    JSON = "json"
    PICKLE = "pickle"
    COMPRESSED_JSON = "compressed_json"
    COMPRESSED_PICKLE = "compressed_pickle"

class CacheStrategy(Enum):
    """Cache invalidation and management strategies."""
    TTL_ONLY = "ttl_only"
    LRU_TTL = "lru_ttl"
    WRITE_THROUGH = "write_through"
    ADAPTIVE = "adaptive"

@dataclass
class RedisCacheConfig:
    """Configuration for Redis cache layer."""
    # Redis connection
    redis_url: str = "redis://localhost:6379"
    redis_password: Optional[str] = None
    redis_db: int = 0
    
    # Upstash configuration
    upstash_url: Optional[str] = None
    upstash_token: Optional[str] = None
    
    # Cache behavior
    cache_mode: CacheMode = CacheMode.HYBRID
    serialization_format: SerializationFormat = SerializationFormat.COMPRESSED_JSON
    cache_strategy: CacheStrategy = CacheStrategy.ADAPTIVE
    
    # Performance settings
    default_ttl_seconds: int = 3600
    max_key_size: int = 250
    max_value_size_mb: float = 16.0
    compression_threshold: int = 1024
    
    # Connection pooling
    max_connections: int = 20
    connection_timeout_seconds: int = 5
    socket_keepalive: bool = True
    socket_keepalive_options: Dict[str, int] = None
    
    # Retry and circuit breaker
    max_retries: int = 3
    retry_delay_ms: int = 100
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout_seconds: int = 60
    
    # Cache namespaces
    key_prefix: str = "ptolemies"
    query_namespace: str = "query"
    result_namespace: str = "result"
    embedding_namespace: str = "embedding"
    concept_namespace: str = "concept"
    analytics_namespace: str = "analytics"
    
    def __post_init__(self):
        if self.socket_keepalive_options is None:
            self.socket_keepalive_options = {}

@dataclass
class CacheMetrics:
    """Metrics for Redis cache performance."""
    hits: int = 0
    misses: int = 0
    errors: int = 0
    timeouts: int = 0
    total_operations: int = 0
    total_bytes_read: int = 0
    total_bytes_written: int = 0
    avg_read_time_ms: float = 0.0
    avg_write_time_ms: float = 0.0
    hit_rate: float = 0.0
    error_rate: float = 0.0
    circuit_breaker_trips: int = 0
    compression_ratio: float = 0.0

@dataclass
class CacheEntry:
    """Represents a cache entry with metadata."""
    key: str
    value: Any
    ttl_seconds: Optional[int] = None
    created_at: Optional[float] = None
    accessed_at: Optional[float] = None
    access_count: int = 0
    size_bytes: int = 0
    compressed: bool = False
    namespace: str = "default"

class CircuitBreaker:
    """Circuit breaker for Redis operations."""
    
    def __init__(self, threshold: int = 5, timeout_seconds: int = 60):
        self.threshold = threshold
        self.timeout_seconds = timeout_seconds
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def can_execute(self) -> bool:
        """Check if operation can be executed."""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout_seconds:
                self.state = "HALF_OPEN"
                return True
            return False
        elif self.state == "HALF_OPEN":
            return True
        return False
    
    def record_success(self):
        """Record successful operation."""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def record_failure(self):
        """Record failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.threshold:
            self.state = "OPEN"

class RedisSerializer:
    """Handles serialization/deserialization for Redis storage."""
    
    def __init__(self, format_type: SerializationFormat = SerializationFormat.COMPRESSED_JSON):
        self.format_type = format_type
    
    @logfire.instrument("serialize_data")
    def serialize(self, data: Any, compress_threshold: int = 1024) -> Tuple[bytes, bool]:
        """Serialize data for Redis storage."""
        with logfire.span("Serializing data", format=self.format_type.value):
            try:
                if self.format_type in [SerializationFormat.JSON, SerializationFormat.COMPRESSED_JSON]:
                    serialized = json.dumps(data, default=str).encode('utf-8')
                else:  # PICKLE or COMPRESSED_PICKLE
                    serialized = pickle.dumps(data)
                
                # Apply compression if needed
                compressed = False
                if (self.format_type in [SerializationFormat.COMPRESSED_JSON, SerializationFormat.COMPRESSED_PICKLE] 
                    and len(serialized) > compress_threshold):
                    serialized = gzip.compress(serialized)
                    compressed = True
                
                logfire.info("Data serialized", 
                           format=self.format_type.value,
                           original_size=len(serialized),
                           compressed=compressed)
                
                return serialized, compressed
                
            except Exception as e:
                logfire.error("Serialization failed", error=str(e))
                raise
    
    @logfire.instrument("deserialize_data")
    def deserialize(self, data: bytes, compressed: bool = False) -> Any:
        """Deserialize data from Redis storage."""
        with logfire.span("Deserializing data", format=self.format_type.value, compressed=compressed):
            try:
                # Decompress if needed
                if compressed:
                    data = gzip.decompress(data)
                
                # Deserialize based on format
                if self.format_type in [SerializationFormat.JSON, SerializationFormat.COMPRESSED_JSON]:
                    result = json.loads(data.decode('utf-8'))
                else:  # PICKLE or COMPRESSED_PICKLE
                    result = pickle.loads(data)
                
                logfire.info("Data deserialized", 
                           format=self.format_type.value,
                           decompressed=compressed)
                
                return result
                
            except Exception as e:
                logfire.error("Deserialization failed", error=str(e))
                raise

class RedisCacheLayer:
    """Redis-based distributed caching layer with Upstash support."""
    
    def __init__(self, config: RedisCacheConfig = None):
        self.config = config or RedisCacheConfig()
        self.redis_client: Optional[redis.Redis] = None
        self.serializer = RedisSerializer(self.config.serialization_format)
        self.circuit_breaker = CircuitBreaker(
            threshold=self.config.circuit_breaker_threshold,
            timeout_seconds=self.config.circuit_breaker_timeout_seconds
        )
        self.metrics = CacheMetrics()
        self.local_cache = {}  # Simple local cache for hybrid mode
        self.start_time = time.time()
        
        # Initialize from environment
        self._initialize_from_environment()
    
    def _initialize_from_environment(self):
        """Initialize configuration from environment variables."""
        self.config.upstash_url = os.getenv("UPSTASH_REDIS_REST_URL", self.config.upstash_url)
        self.config.upstash_token = os.getenv("UPSTASH_REDIS_REST_TOKEN", self.config.upstash_token)
        self.config.redis_url = os.getenv("REDIS_URL", self.config.redis_url)
        self.config.redis_password = os.getenv("REDIS_PASSWORD", self.config.redis_password)
    
    @logfire.instrument("connect_redis")
    async def connect(self) -> bool:
        """Connect to Redis instance."""
        try:
            with logfire.span("Connecting to Redis"):
                if self.config.upstash_url and self.config.upstash_token:
                    # Use Upstash configuration
                    logfire.info("Connecting to Upstash Redis", url=self.config.upstash_url[:50])
                    
                    self.redis_client = redis.from_url(
                        self.config.upstash_url,
                        password=self.config.upstash_token,
                        db=self.config.redis_db,
                        max_connections=self.config.max_connections,
                        socket_connect_timeout=self.config.connection_timeout_seconds,
                        socket_keepalive=self.config.socket_keepalive,
                        socket_keepalive_options=self.config.socket_keepalive_options,
                        decode_responses=False  # We handle encoding ourselves
                    )
                else:
                    # Use standard Redis configuration
                    logfire.info("Connecting to Redis", url=self.config.redis_url)
                    
                    self.redis_client = redis.from_url(
                        self.config.redis_url,
                        password=self.config.redis_password,
                        db=self.config.redis_db,
                        max_connections=self.config.max_connections,
                        socket_connect_timeout=self.config.connection_timeout_seconds,
                        socket_keepalive=self.config.socket_keepalive,
                        socket_keepalive_options=self.config.socket_keepalive_options,
                        decode_responses=False
                    )
                
                # Test connection
                await self.redis_client.ping()
                
                logfire.info("Redis connection established successfully")
                return True
                
        except Exception as e:
            logfire.error("Failed to connect to Redis", error=str(e))
            self.redis_client = None
            return False
    
    def _generate_cache_key(self, namespace: str, key: str) -> str:
        """Generate Redis cache key with namespace."""
        # Ensure key is within size limits
        if len(key) > self.config.max_key_size:
            # Hash long keys
            key = hashlib.md5(key.encode()).hexdigest()
        
        return f"{self.config.key_prefix}:{namespace}:{key}"
    
    @logfire.instrument("redis_get")
    async def get(self, key: str, namespace: str = "default") -> Tuple[Any, bool]:
        """Get value from cache."""
        if not self.circuit_breaker.can_execute():
            logfire.warning("Circuit breaker open, skipping Redis operation")
            return None, False
        
        redis_key = self._generate_cache_key(namespace, key)
        
        start_time = time.time()
        try:
            with logfire.span("Redis GET operation", key=redis_key[:50], namespace=namespace):
                # Try local cache first in hybrid and local-only modes
                if self.config.cache_mode in [CacheMode.HYBRID, CacheMode.LOCAL_ONLY] and redis_key in self.local_cache:
                    entry = self.local_cache[redis_key]
                    if entry.ttl_seconds is None or time.time() - entry.created_at < entry.ttl_seconds:
                        self.metrics.hits += 1
                        self.metrics.total_operations += 1
                        logfire.info("Local cache hit", key=redis_key[:50])
                        return entry.value, True
                    else:
                        # Remove expired entry
                        del self.local_cache[redis_key]
                
                if self.config.cache_mode == CacheMode.LOCAL_ONLY:
                    self.metrics.misses += 1
                    self.metrics.total_operations += 1
                    return None, False
                
                # Get from Redis
                if not self.redis_client:
                    await self.connect()
                
                if not self.redis_client:
                    self.metrics.errors += 1
                    self.metrics.total_operations += 1
                    return None, False
                
                # Get value and metadata
                pipe = self.redis_client.pipeline()
                pipe.get(redis_key)
                pipe.get(f"{redis_key}:meta")
                
                results = await pipe.execute()
                value_data, meta_data = results
                
                if value_data is None:
                    self.metrics.misses += 1
                    self.metrics.total_operations += 1
                    logfire.debug("Redis cache miss", key=redis_key[:50])
                    return None, False
                
                # Deserialize metadata
                compressed = False
                if meta_data:
                    try:
                        meta = json.loads(meta_data.decode('utf-8'))
                        compressed = meta.get('compressed', False)
                    except:
                        pass
                
                # Deserialize value
                value = self.serializer.deserialize(value_data, compressed)
                
                # Update local cache in hybrid mode
                if self.config.cache_mode == CacheMode.HYBRID:
                    entry = CacheEntry(
                        key=key,
                        value=value,
                        created_at=time.time(),
                        namespace=namespace,
                        compressed=compressed
                    )
                    self.local_cache[redis_key] = entry
                
                read_time = (time.time() - start_time) * 1000
                self.metrics.hits += 1
                self.metrics.total_operations += 1
                self.metrics.total_bytes_read += len(value_data)
                self.metrics.avg_read_time_ms = (
                    (self.metrics.avg_read_time_ms * (self.metrics.hits - 1) + read_time) / self.metrics.hits
                )
                
                self.circuit_breaker.record_success()
                
                logfire.info("Redis cache hit", 
                           key=redis_key[:50],
                           read_time_ms=read_time,
                           compressed=compressed,
                           size_bytes=len(value_data))
                
                return value, True
                
        except asyncio.TimeoutError:
            self.metrics.timeouts += 1
            self.metrics.total_operations += 1
            self.circuit_breaker.record_failure()
            logfire.warning("Redis GET timeout", key=redis_key[:50])
            return None, False
            
        except Exception as e:
            self.metrics.errors += 1
            self.metrics.total_operations += 1
            self.circuit_breaker.record_failure()
            logfire.error("Redis GET failed", key=redis_key[:50], error=str(e))
            return None, False
    
    @logfire.instrument("redis_set")
    async def set(
        self, 
        key: str, 
        value: Any, 
        namespace: str = "default",
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """Set value in cache."""
        if not self.circuit_breaker.can_execute():
            logfire.warning("Circuit breaker open, skipping Redis operation")
            return False
        
        redis_key = self._generate_cache_key(namespace, key)
        ttl = ttl_seconds or self.config.default_ttl_seconds
        
        start_time = time.time()
        try:
            with logfire.span("Redis SET operation", key=redis_key[:50], namespace=namespace):
                # Serialize value
                serialized_data, compressed = self.serializer.serialize(
                    value, self.config.compression_threshold
                )
                
                # Check size limits
                size_mb = len(serialized_data) / (1024 * 1024)
                if size_mb > self.config.max_value_size_mb:
                    logfire.warning("Value too large for cache", 
                                  size_mb=size_mb, 
                                  max_mb=self.config.max_value_size_mb)
                    return False
                
                # Update local cache in hybrid and local-only modes
                if self.config.cache_mode in [CacheMode.HYBRID, CacheMode.LOCAL_ONLY]:
                    entry = CacheEntry(
                        key=key,
                        value=value,
                        ttl_seconds=ttl,
                        created_at=time.time(),
                        namespace=namespace,
                        size_bytes=len(serialized_data),
                        compressed=compressed
                    )
                    self.local_cache[redis_key] = entry
                
                if self.config.cache_mode == CacheMode.LOCAL_ONLY:
                    self.metrics.total_operations += 1
                    return True
                
                # Set in Redis
                if not self.redis_client:
                    await self.connect()
                
                if not self.redis_client:
                    self.metrics.errors += 1
                    return False
                
                # Store value and metadata
                metadata = {
                    'compressed': compressed,
                    'size_bytes': len(serialized_data),
                    'created_at': time.time(),
                    'namespace': namespace
                }
                
                pipe = self.redis_client.pipeline()
                pipe.setex(redis_key, ttl, serialized_data)
                pipe.setex(f"{redis_key}:meta", ttl, json.dumps(metadata))
                
                await pipe.execute()
                
                write_time = (time.time() - start_time) * 1000
                self.metrics.total_operations += 1
                self.metrics.total_bytes_written += len(serialized_data)
                write_count = getattr(self.metrics, '_write_count', 0) + 1
                setattr(self.metrics, '_write_count', write_count)
                self.metrics.avg_write_time_ms = (
                    (self.metrics.avg_write_time_ms * (write_count - 1) + write_time) / write_count
                )
                
                self.circuit_breaker.record_success()
                
                logfire.info("Redis cache set", 
                           key=redis_key[:50],
                           write_time_ms=write_time,
                           compressed=compressed,
                           size_bytes=len(serialized_data),
                           ttl_seconds=ttl)
                
                return True
                
        except asyncio.TimeoutError:
            self.metrics.timeouts += 1
            self.circuit_breaker.record_failure()
            logfire.warning("Redis SET timeout", key=redis_key[:50])
            return False
            
        except Exception as e:
            self.metrics.errors += 1
            self.circuit_breaker.record_failure()
            logfire.error("Redis SET failed", key=redis_key[:50], error=str(e))
            return False
    
    @logfire.instrument("redis_delete")
    async def delete(self, key: str, namespace: str = "default") -> bool:
        """Delete value from cache."""
        redis_key = self._generate_cache_key(namespace, key)
        
        try:
            with logfire.span("Redis DELETE operation", key=redis_key[:50]):
                # Remove from local cache
                if redis_key in self.local_cache:
                    del self.local_cache[redis_key]
                
                if self.config.cache_mode == CacheMode.LOCAL_ONLY:
                    return True
                
                if not self.redis_client:
                    return False
                
                # Delete from Redis
                pipe = self.redis_client.pipeline()
                pipe.delete(redis_key)
                pipe.delete(f"{redis_key}:meta")
                
                results = await pipe.execute()
                deleted = results[0] > 0
                
                logfire.info("Redis cache delete", key=redis_key[:50], deleted=deleted)
                return deleted
                
        except Exception as e:
            logfire.error("Redis DELETE failed", key=redis_key[:50], error=str(e))
            return False
    
    @logfire.instrument("redis_exists")
    async def exists(self, key: str, namespace: str = "default") -> bool:
        """Check if key exists in cache."""
        redis_key = self._generate_cache_key(namespace, key)
        
        try:
            # Check local cache first
            if self.config.cache_mode in [CacheMode.HYBRID, CacheMode.LOCAL_ONLY] and redis_key in self.local_cache:
                entry = self.local_cache[redis_key]
                if entry.ttl_seconds is None or time.time() - entry.created_at < entry.ttl_seconds:
                    return True
                else:
                    del self.local_cache[redis_key]
            
            if self.config.cache_mode == CacheMode.LOCAL_ONLY:
                return False
            
            if not self.redis_client:
                return False
            
            return bool(await self.redis_client.exists(redis_key))
            
        except Exception as e:
            logfire.error("Redis EXISTS failed", key=redis_key[:50], error=str(e))
            return False
    
    @logfire.instrument("redis_clear_namespace")
    async def clear_namespace(self, namespace: str) -> int:
        """Clear all keys in a namespace."""
        try:
            with logfire.span("Clearing namespace", namespace=namespace):
                pattern = f"{self.config.key_prefix}:{namespace}:*"
                
                # Clear local cache
                local_cleared = 0
                keys_to_remove = [k for k in self.local_cache.keys() if k.startswith(f"{self.config.key_prefix}:{namespace}:")]
                for key in keys_to_remove:
                    del self.local_cache[key]
                    local_cleared += 1
                
                if self.config.cache_mode == CacheMode.LOCAL_ONLY:
                    logfire.info("Local namespace cleared", namespace=namespace, keys_cleared=local_cleared)
                    return local_cleared
                
                if not self.redis_client:
                    return local_cleared
                
                # Clear Redis
                redis_cleared = 0
                async for key in self.redis_client.scan_iter(match=pattern):
                    await self.redis_client.delete(key)
                    redis_cleared += 1
                
                total_cleared = local_cleared + redis_cleared
                logfire.info("Namespace cleared", 
                           namespace=namespace, 
                           total_keys_cleared=total_cleared,
                           local_cleared=local_cleared,
                           redis_cleared=redis_cleared)
                
                return total_cleared
                
        except Exception as e:
            logfire.error("Clear namespace failed", namespace=namespace, error=str(e))
            return 0
    
    @logfire.instrument("get_cache_stats")
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        try:
            # Update hit rate and error rate
            total_ops = self.metrics.total_operations
            if total_ops > 0:
                self.metrics.hit_rate = self.metrics.hits / total_ops
                self.metrics.error_rate = self.metrics.errors / total_ops
            
            # Calculate compression ratio
            if self.metrics.total_bytes_written > 0:
                # This is a simplified compression ratio calculation
                self.metrics.compression_ratio = 0.8  # Placeholder
            
            stats = {
                "cache_metrics": asdict(self.metrics),
                "configuration": {
                    "cache_mode": self.config.cache_mode.value,
                    "serialization_format": self.config.serialization_format.value,
                    "default_ttl_seconds": self.config.default_ttl_seconds,
                    "max_connections": self.config.max_connections
                },
                "circuit_breaker": {
                    "state": self.circuit_breaker.state,
                    "failure_count": self.circuit_breaker.failure_count,
                    "threshold": self.circuit_breaker.threshold
                },
                "local_cache": {
                    "size": len(self.local_cache),
                    "estimated_memory_mb": len(self.local_cache) * 0.001  # Rough estimate
                },
                "runtime_info": {
                    "uptime_seconds": time.time() - self.start_time,
                    "operations_per_second": total_ops / max(time.time() - self.start_time, 1)
                }
            }
            
            # Add Redis-specific stats if available
            if self.redis_client and self.config.cache_mode != CacheMode.LOCAL_ONLY:
                try:
                    redis_info = await self.redis_client.info()
                    stats["redis_info"] = {
                        "connected_clients": redis_info.get("connected_clients", 0),
                        "used_memory": redis_info.get("used_memory", 0),
                        "used_memory_human": redis_info.get("used_memory_human", "0B"),
                        "keyspace_hits": redis_info.get("keyspace_hits", 0),
                        "keyspace_misses": redis_info.get("keyspace_misses", 0)
                    }
                except:
                    stats["redis_info"] = {"error": "Unable to retrieve Redis info"}
            
            logfire.info("Cache statistics retrieved", 
                       hit_rate=self.metrics.hit_rate,
                       error_rate=self.metrics.error_rate,
                       total_operations=total_ops)
            
            return stats
            
        except Exception as e:
            logfire.error("Failed to get cache stats", error=str(e))
            return {"error": str(e)}
    
    @logfire.instrument("redis_close")
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            with logfire.span("Closing Redis connection"):
                await self.redis_client.close()
                self.redis_client = None
                logfire.info("Redis connection closed")

# Cache decorators and utilities
def redis_cached(
    namespace: str = "default",
    ttl_seconds: Optional[int] = None,
    key_generator: Optional[Callable] = None
):
    """Decorator for caching function results in Redis."""
    def decorator(func):
        async def wrapper(*args, cache_layer: RedisCacheLayer, **kwargs):
            # Generate cache key
            if key_generator:
                cache_key = key_generator(*args, **kwargs)
            else:
                key_parts = [func.__name__] + [str(arg) for arg in args]
                cache_key = ":".join(key_parts)
            
            # Try to get from cache
            cached_result, found = await cache_layer.get(cache_key, namespace)
            if found:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_layer.set(cache_key, result, namespace, ttl_seconds)
            
            return result
        return wrapper
    return decorator

# Utility functions
async def create_redis_cache_layer(
    redis_url: Optional[str] = None,
    upstash_url: Optional[str] = None,
    upstash_token: Optional[str] = None
) -> RedisCacheLayer:
    """Create and connect Redis cache layer."""
    config = RedisCacheConfig()
    
    if redis_url:
        config.redis_url = redis_url
    if upstash_url:
        config.upstash_url = upstash_url
    if upstash_token:
        config.upstash_token = upstash_token
    
    cache_layer = RedisCacheLayer(config)
    connected = await cache_layer.connect()
    
    if not connected:
        logfire.warning("Failed to connect to Redis, falling back to local cache only")
        config.cache_mode = CacheMode.LOCAL_ONLY
        cache_layer = RedisCacheLayer(config)
    
    return cache_layer

async def warm_cache_with_common_data(
    cache_layer: RedisCacheLayer,
    common_queries: List[str] = None,
    common_results: Dict[str, Any] = None
) -> None:
    """Warm cache with commonly accessed data."""
    if common_queries is None:
        common_queries = [
            "FastAPI authentication middleware",
            "Neo4j graph relationships",
            "SurrealDB vector search",
            "Python async programming",
            "API security best practices"
        ]
    
    with logfire.span("Cache warmup", items_to_warm=len(common_queries)):
        for query in common_queries:
            await cache_layer.set(f"warmup_{query}", {"query": query, "warmed": True}, "warmup", 7200)
        
        if common_results:
            for key, value in common_results.items():
                await cache_layer.set(key, value, "common", 3600)
        
        logfire.info("Cache warmup completed", queries_warmed=len(common_queries))

if __name__ == "__main__":
    # Example usage
    async def main():
        # Create cache layer
        cache_layer = await create_redis_cache_layer()
        
        # Test basic operations
        await cache_layer.set("test_key", {"message": "Hello Redis!"}, "test")
        
        result, found = await cache_layer.get("test_key", "test")
        print(f"Retrieved from cache: {result}, found: {found}")
        
        # Get statistics
        stats = await cache_layer.get_cache_stats()
        print(f"Cache stats: {stats['cache_metrics']}")
        
        await cache_layer.close()
    
    asyncio.run(main())