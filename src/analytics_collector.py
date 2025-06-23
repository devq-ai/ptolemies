#!/usr/bin/env python3
"""
Analytics Data Collection for Ptolemies
Comprehensive analytics system to collect, store, and analyze usage data.
"""

import asyncio
import time
import json
import uuid
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime, timezone, timedelta
from collections import defaultdict, deque
import threading
from pathlib import Path

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

# Configure Logfire
logfire.configure(send_to_logfire=False)

class EventType(Enum):
    """Types of analytics events."""
    QUERY_STARTED = "query_started"
    QUERY_COMPLETED = "query_completed"
    QUERY_FAILED = "query_failed"
    SEARCH_EXECUTED = "search_executed"
    TOOL_REGISTERED = "tool_registered"
    TOOL_EXECUTED = "tool_executed"
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    ERROR_OCCURRED = "error_occurred"
    PERFORMANCE_METRIC = "performance_metric"
    USER_INTERACTION = "user_interaction"
    SYSTEM_HEALTH = "system_health"

class MetricType(Enum):
    """Types of metrics to collect."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMING = "timing"
    RATE = "rate"

@dataclass
class AnalyticsEvent:
    """Represents an analytics event."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = EventType.USER_INTERACTION
    timestamp: float = field(default_factory=time.time)
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # Event data
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Context information
    query: Optional[str] = None
    intent: Optional[str] = None
    search_strategy: Optional[str] = None
    
    # Performance metrics
    duration_ms: Optional[float] = None
    success: Optional[bool] = None
    error_message: Optional[str] = None
    
    # System metrics
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    
    # Metadata
    source_component: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for storage."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict(), default=str)

@dataclass
class Metric:
    """Represents a collected metric."""
    name: str
    type: MetricType
    value: Union[int, float]
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)
    unit: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary."""
        return asdict(self)

@dataclass
class AnalyticsConfig:
    """Configuration for analytics collection."""
    # Collection settings
    enabled: bool = True
    batch_size: int = 100
    flush_interval_seconds: int = 60
    max_memory_events: int = 10000
    
    # Storage settings
    storage_backend: str = "file"  # file, redis, database
    storage_path: str = "analytics"
    retention_days: int = 30
    
    # Performance settings
    async_processing: bool = True
    max_worker_threads: int = 4
    
    # Privacy settings
    anonymize_user_data: bool = False
    collect_system_metrics: bool = True
    collect_query_content: bool = True
    
    # Aggregation settings
    enable_real_time_aggregation: bool = True
    aggregation_intervals: List[int] = field(default_factory=lambda: [60, 300, 3600])  # 1m, 5m, 1h
    
    # Alert settings
    enable_alerting: bool = True
    error_rate_threshold: float = 0.1  # 10%
    response_time_threshold_ms: float = 5000  # 5 seconds

class AnalyticsCollector:
    """Main analytics collection system."""
    
    def __init__(self, config: AnalyticsConfig = None):
        self.config = config or AnalyticsConfig()
        
        # Event storage
        self.events_queue: deque = deque(maxlen=self.config.max_memory_events)
        self.metrics_queue: deque = deque(maxlen=self.config.max_memory_events)
        
        # Aggregated data
        self.real_time_stats = defaultdict(lambda: defaultdict(float))
        self.session_stats = defaultdict(dict)
        self.query_stats = defaultdict(list)
        
        # Threading for async processing
        self.processing_thread: Optional[threading.Thread] = None
        self.should_stop = threading.Event()
        self.queue_lock = threading.RLock()
        
        # Storage
        self.storage_path = Path(self.config.storage_path)
        self.storage_path.mkdir(exist_ok=True)
        
        # Performance tracking
        self.start_time = time.time()
        self.last_flush = time.time()
        
        # Start background processing if enabled
        if self.config.enabled and self.config.async_processing:
            self._start_background_processing()
    
    @logfire.instrument("record_event")
    def record_event(self, event: AnalyticsEvent):
        """Record an analytics event."""
        if not self.config.enabled:
            return
        
        try:
            with logfire.span("Recording analytics event", event_type=event.event_type.value):
                # Apply privacy settings
                if self.config.anonymize_user_data:
                    event.user_id = self._anonymize_user_id(event.user_id)
                
                if not self.config.collect_query_content:
                    event.query = None
                
                # Add system metrics if enabled
                if self.config.collect_system_metrics:
                    self._add_system_metrics(event)
                
                # Store event
                with self.queue_lock:
                    self.events_queue.append(event)
                
                # Update real-time aggregations
                if self.config.enable_real_time_aggregation:
                    self._update_real_time_stats(event)
                
                logfire.info("Analytics event recorded", 
                           event_type=event.event_type.value,
                           session_id=event.session_id)
                
        except Exception as e:
            logfire.error("Failed to record analytics event", error=str(e))
    
    @logfire.instrument("record_metric")
    def record_metric(self, name: str, value: Union[int, float], 
                     metric_type: MetricType = MetricType.GAUGE,
                     tags: Dict[str, str] = None, unit: str = None):
        """Record a metric."""
        if not self.config.enabled:
            return
        
        try:
            metric = Metric(
                name=name,
                type=metric_type,
                value=value,
                tags=tags or {},
                unit=unit
            )
            
            with self.queue_lock:
                self.metrics_queue.append(metric)
            
            logfire.info("Metric recorded", 
                       metric_name=name, 
                       metric_value=value,
                       metric_type=metric_type.value)
                       
        except Exception as e:
            logfire.error("Failed to record metric", error=str(e))
    
    def record_query_analytics(self, query: str, intent: str, 
                             session_id: str, user_id: str = None,
                             processing_time_ms: float = None,
                             success: bool = True, error: str = None,
                             results_count: int = None,
                             search_strategy: str = None):
        """Record comprehensive query analytics."""
        
        # Record query event
        event_type = EventType.QUERY_COMPLETED if success else EventType.QUERY_FAILED
        
        event = AnalyticsEvent(
            event_type=event_type,
            session_id=session_id,
            user_id=user_id,
            query=query,
            intent=intent,
            search_strategy=search_strategy,
            duration_ms=processing_time_ms,
            success=success,
            error_message=error,
            source_component="query_processor",
            data={
                "results_count": results_count,
                "query_length": len(query) if query else 0,
                "intent": intent,
                "search_strategy": search_strategy
            }
        )
        
        self.record_event(event)
        
        # Record related metrics
        if processing_time_ms:
            self.record_metric("query_processing_time_ms", processing_time_ms, 
                             MetricType.TIMING, {"intent": intent})
        
        if results_count is not None:
            self.record_metric("query_results_count", results_count,
                             MetricType.GAUGE, {"intent": intent})
        
        # Update query statistics
        with self.queue_lock:
            self.query_stats[intent].append({
                "timestamp": time.time(),
                "processing_time_ms": processing_time_ms,
                "success": success,
                "results_count": results_count
            })
    
    def record_search_analytics(self, search_type: str, query: str,
                              duration_ms: float, results_found: int,
                              cache_hit: bool = False):
        """Record search-specific analytics."""
        
        event = AnalyticsEvent(
            event_type=EventType.SEARCH_EXECUTED,
            duration_ms=duration_ms,
            success=results_found > 0,
            source_component="search_engine",
            data={
                "search_type": search_type,
                "query": query if self.config.collect_query_content else None,
                "results_found": results_found,
                "cache_hit": cache_hit
            },
            tags=[search_type, "cache_hit" if cache_hit else "cache_miss"]
        )
        
        self.record_event(event)
        
        # Record search metrics
        self.record_metric(f"search_{search_type}_duration_ms", duration_ms,
                         MetricType.TIMING)
        self.record_metric(f"search_{search_type}_results", results_found,
                         MetricType.GAUGE)
    
    def record_tool_analytics(self, tool_name: str, operation: str,
                            duration_ms: float = None, success: bool = True,
                            error: str = None):
        """Record tool usage analytics."""
        
        event_type = EventType.TOOL_EXECUTED
        if operation == "register":
            event_type = EventType.TOOL_REGISTERED
        
        event = AnalyticsEvent(
            event_type=event_type,
            duration_ms=duration_ms,
            success=success,
            error_message=error,
            source_component="tool_registry",
            data={
                "tool_name": tool_name,
                "operation": operation
            },
            tags=[tool_name, operation]
        )
        
        self.record_event(event)
        
        # Record tool metrics
        if duration_ms:
            self.record_metric("tool_execution_duration_ms", duration_ms,
                             MetricType.TIMING, {"tool": tool_name})
    
    def record_session_analytics(self, session_id: str, user_id: str = None,
                                action: str = "start", duration_seconds: float = None,
                                queries_count: int = None):
        """Record session analytics."""
        
        event_type = EventType.SESSION_STARTED if action == "start" else EventType.SESSION_ENDED
        
        event = AnalyticsEvent(
            event_type=event_type,
            session_id=session_id,
            user_id=user_id,
            duration_ms=duration_seconds * 1000 if duration_seconds else None,
            source_component="session_manager",
            data={
                "action": action,
                "queries_count": queries_count
            }
        )
        
        self.record_event(event)
        
        # Update session statistics
        with self.queue_lock:
            if action == "start":
                self.session_stats[session_id] = {
                    "start_time": time.time(),
                    "user_id": user_id,
                    "queries_count": 0
                }
            elif action == "end" and session_id in self.session_stats:
                session_data = self.session_stats[session_id]
                session_data["end_time"] = time.time()
                session_data["duration_seconds"] = duration_seconds
                session_data["queries_count"] = queries_count
    
    def record_performance_metrics(self):
        """Record current system performance metrics."""
        try:
            import psutil
            
            # CPU and memory metrics
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            
            event = AnalyticsEvent(
                event_type=EventType.PERFORMANCE_METRIC,
                cpu_usage_percent=cpu_percent,
                memory_usage_mb=memory.used / 1024 / 1024,
                source_component="system_monitor",
                data={
                    "memory_total_mb": memory.total / 1024 / 1024,
                    "memory_available_mb": memory.available / 1024 / 1024,
                    "memory_percent": memory.percent,
                    "cpu_count": psutil.cpu_count()
                }
            )
            
            self.record_event(event)
            
            # Record as metrics too
            self.record_metric("system_cpu_percent", cpu_percent, MetricType.GAUGE, unit="%")
            self.record_metric("system_memory_used_mb", memory.used / 1024 / 1024, 
                             MetricType.GAUGE, unit="MB")
            self.record_metric("system_memory_percent", memory.percent, 
                             MetricType.GAUGE, unit="%")
                             
        except ImportError:
            # psutil not available, record basic metrics
            event = AnalyticsEvent(
                event_type=EventType.SYSTEM_HEALTH,
                source_component="basic_monitor",
                data={
                    "uptime_seconds": time.time() - self.start_time,
                    "events_queued": len(self.events_queue),
                    "metrics_queued": len(self.metrics_queue)
                }
            )
            self.record_event(event)
        except Exception as e:
            logfire.error("Failed to record performance metrics", error=str(e))
    
    def get_analytics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get analytics summary for the specified time period."""
        cutoff_time = time.time() - (hours * 3600)
        
        summary = {
            "time_period_hours": hours,
            "total_events": 0,
            "total_metrics": 0,
            "event_types": defaultdict(int),
            "query_intents": defaultdict(int),
            "error_rate": 0.0,
            "avg_response_time_ms": 0.0,
            "active_sessions": 0,
            "top_queries": [],
            "system_health": "healthy"
        }
        
        # Analyze events
        recent_events = [e for e in self.events_queue if e.timestamp >= cutoff_time]
        summary["total_events"] = len(recent_events)
        
        successful_queries = []
        failed_queries = 0
        response_times = []
        
        for event in recent_events:
            summary["event_types"][event.event_type.value] += 1
            
            if event.intent:
                summary["query_intents"][event.intent] += 1
            
            if event.event_type in [EventType.QUERY_COMPLETED, EventType.QUERY_FAILED]:
                if event.success:
                    successful_queries.append(event)
                    if event.duration_ms:
                        response_times.append(event.duration_ms)
                else:
                    failed_queries += 1
        
        # Calculate error rate
        total_queries = len(successful_queries) + failed_queries
        if total_queries > 0:
            summary["error_rate"] = failed_queries / total_queries
        
        # Calculate average response time
        if response_times:
            summary["avg_response_time_ms"] = sum(response_times) / len(response_times)
        
        # Count active sessions
        current_time = time.time()
        active_sessions = 0
        for session_id, session_data in self.session_stats.items():
            if "end_time" not in session_data:  # Session still active
                if current_time - session_data.get("start_time", 0) < 3600:  # Active within last hour
                    active_sessions += 1
        
        summary["active_sessions"] = active_sessions
        
        # Top queries (if query content collection is enabled)
        if self.config.collect_query_content:
            query_counts = defaultdict(int)
            for event in recent_events:
                if event.query:
                    query_counts[event.query] += 1
            
            summary["top_queries"] = sorted(query_counts.items(), 
                                          key=lambda x: x[1], reverse=True)[:10]
        
        # System health assessment
        if summary["error_rate"] > self.config.error_rate_threshold:
            summary["system_health"] = "degraded"
        elif summary["avg_response_time_ms"] > self.config.response_time_threshold_ms:
            summary["system_health"] = "slow"
        
        return summary
    
    def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time metrics and statistics."""
        current_time = time.time()
        
        # Calculate rates for different time windows
        metrics = {
            "current_timestamp": current_time,
            "queries_per_minute": 0,
            "errors_per_minute": 0,
            "avg_response_time_ms": 0,
            "cache_hit_rate": 0,
            "active_sessions": len([s for s in self.session_stats.values() 
                                   if "end_time" not in s]),
            "system_uptime_seconds": current_time - self.start_time
        }
        
        # Calculate rates from recent events (last 5 minutes)
        five_minutes_ago = current_time - 300
        recent_events = [e for e in self.events_queue if e.timestamp >= five_minutes_ago]
        
        queries = [e for e in recent_events if e.event_type in [EventType.QUERY_COMPLETED, EventType.QUERY_FAILED]]
        errors = [e for e in recent_events if e.event_type == EventType.QUERY_FAILED]
        
        metrics["queries_per_minute"] = len(queries) / 5  # Average per minute over 5 minutes
        metrics["errors_per_minute"] = len(errors) / 5
        
        # Calculate average response time
        response_times = [e.duration_ms for e in queries if e.duration_ms]
        if response_times:
            metrics["avg_response_time_ms"] = sum(response_times) / len(response_times)
        
        # Calculate cache hit rate
        cache_events = [e for e in recent_events if e.event_type in [EventType.CACHE_HIT, EventType.CACHE_MISS]]
        cache_hits = [e for e in cache_events if e.event_type == EventType.CACHE_HIT]
        if cache_events:
            metrics["cache_hit_rate"] = len(cache_hits) / len(cache_events)
        
        return metrics
    
    def flush_data(self):
        """Flush pending data to storage."""
        if not self.config.enabled:
            return
        
        try:
            with logfire.span("Flushing analytics data"):
                current_time = time.time()
                
                # Copy and clear queues
                with self.queue_lock:
                    events_to_flush = list(self.events_queue)
                    metrics_to_flush = list(self.metrics_queue)
                    self.events_queue.clear()
                    self.metrics_queue.clear()
                
                if events_to_flush or metrics_to_flush:
                    self._write_to_storage(events_to_flush, metrics_to_flush)
                    
                    logfire.info("Analytics data flushed",
                               events_count=len(events_to_flush),
                               metrics_count=len(metrics_to_flush))
                
                self.last_flush = current_time
                
        except Exception as e:
            logfire.error("Failed to flush analytics data", error=str(e))
    
    def _start_background_processing(self):
        """Start background processing thread."""
        self.processing_thread = threading.Thread(
            target=self._background_worker,
            daemon=True,
            name="analytics_processor"
        )
        self.processing_thread.start()
        logfire.info("Analytics background processing started")
    
    def _background_worker(self):
        """Background worker for processing analytics data."""
        while not self.should_stop.is_set():
            try:
                # Check if it's time to flush
                if time.time() - self.last_flush >= self.config.flush_interval_seconds:
                    self.flush_data()
                
                # Record performance metrics periodically
                if self.config.collect_system_metrics:
                    self.record_performance_metrics()
                
                # Sleep for a bit
                time.sleep(min(30, self.config.flush_interval_seconds / 2))
                
            except Exception as e:
                logfire.error("Background analytics processing error", error=str(e))
                time.sleep(60)  # Wait longer on error
    
    def _write_to_storage(self, events: List[AnalyticsEvent], metrics: List[Metric]):
        """Write events and metrics to storage."""
        timestamp = datetime.now(timezone.utc)
        
        if self.config.storage_backend == "file":
            # Write to files organized by date
            date_str = timestamp.strftime("%Y-%m-%d")
            
            # Events file
            if events:
                events_file = self.storage_path / f"events_{date_str}.jsonl"
                with open(events_file, "a", encoding="utf-8") as f:
                    for event in events:
                        f.write(event.to_json() + "\n")
            
            # Metrics file
            if metrics:
                metrics_file = self.storage_path / f"metrics_{date_str}.jsonl"
                with open(metrics_file, "a", encoding="utf-8") as f:
                    for metric in metrics:
                        f.write(json.dumps(metric.to_dict()) + "\n")
        
        # Additional storage backends can be implemented here
        # elif self.config.storage_backend == "redis":
        #     self._write_to_redis(events, metrics)
        # elif self.config.storage_backend == "database":
        #     self._write_to_database(events, metrics)
    
    def _update_real_time_stats(self, event: AnalyticsEvent):
        """Update real-time statistics."""
        current_time = time.time()
        
        # Update counters
        self.real_time_stats["events"]["total"] += 1
        self.real_time_stats["events"][event.event_type.value] += 1
        
        if event.intent:
            self.real_time_stats["intents"][event.intent] += 1
        
        if event.success is not None:
            if event.success:
                self.real_time_stats["outcomes"]["success"] += 1
            else:
                self.real_time_stats["outcomes"]["failure"] += 1
        
        # Update timing stats
        if event.duration_ms:
            timing_key = f"timing_{event.event_type.value}"
            if timing_key not in self.real_time_stats:
                self.real_time_stats[timing_key] = []
            
            self.real_time_stats[timing_key].append(event.duration_ms)
            
            # Keep only recent timings (last 100)
            if len(self.real_time_stats[timing_key]) > 100:
                self.real_time_stats[timing_key] = self.real_time_stats[timing_key][-100:]
    
    def _add_system_metrics(self, event: AnalyticsEvent):
        """Add system metrics to an event."""
        try:
            import psutil
            
            # Add basic system metrics
            memory = psutil.virtual_memory()
            event.memory_usage_mb = memory.used / 1024 / 1024
            event.cpu_usage_percent = psutil.cpu_percent(interval=None)
            
        except ImportError:
            # Basic metrics without psutil
            event.data["queue_size"] = len(self.events_queue)
            event.data["uptime_seconds"] = time.time() - self.start_time
        except Exception:
            pass  # Don't fail event recording due to system metrics
    
    def _anonymize_user_id(self, user_id: str) -> Optional[str]:
        """Anonymize user ID for privacy."""
        if not user_id:
            return None
        
        # Simple hash-based anonymization
        import hashlib
        return hashlib.sha256(user_id.encode()).hexdigest()[:16]
    
    def close(self):
        """Clean shutdown of analytics collector."""
        logfire.info("Shutting down analytics collector")
        
        # Stop background processing
        self.should_stop.set()
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=10)
        
        # Flush remaining data
        self.flush_data()
        
        logfire.info("Analytics collector shutdown complete")

# Utility functions for easy integration
def create_analytics_collector(config: AnalyticsConfig = None) -> AnalyticsCollector:
    """Create and initialize analytics collector."""
    collector = AnalyticsCollector(config)
    logfire.info("Analytics collector created and initialized")
    return collector

# Context manager for automatic analytics
class analytics_context:
    """Context manager for automatic analytics collection."""
    
    def __init__(self, collector: AnalyticsCollector, event_type: EventType,
                 session_id: str = None, **kwargs):
        self.collector = collector
        self.event_type = event_type
        self.session_id = session_id
        self.kwargs = kwargs
        self.start_time = None
        self.event = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.event = AnalyticsEvent(
            event_type=self.event_type,
            session_id=self.session_id,
            **self.kwargs
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration_ms = (time.time() - self.start_time) * 1000
            self.event.duration_ms = duration_ms
        
        if exc_type:
            self.event.success = False
            self.event.error_message = str(exc_val)
        else:
            self.event.success = True
        
        self.collector.record_event(self.event)

if __name__ == "__main__":
    # Example usage and testing
    async def main():
        print("🔍 Testing Analytics Collector")
        
        # Create collector with test config
        config = AnalyticsConfig(
            enabled=True,
            batch_size=5,
            flush_interval_seconds=10,
            storage_path="test_analytics"
        )
        
        collector = create_analytics_collector(config)
        
        # Test different types of events
        print("Recording test events...")
        
        # Query analytics
        collector.record_query_analytics(
            query="How to use FastAPI?",
            intent="explain",
            session_id="test_session_1",
            user_id="test_user",
            processing_time_ms=150.5,
            success=True,
            results_count=5,
            search_strategy="hybrid"
        )
        
        # Search analytics
        collector.record_search_analytics(
            search_type="semantic",
            query="FastAPI tutorial",
            duration_ms=75.2,
            results_found=3,
            cache_hit=False
        )
        
        # Tool analytics
        collector.record_tool_analytics(
            tool_name="calculator",
            operation="execute",
            duration_ms=25.1,
            success=True
        )
        
        # Session analytics
        collector.record_session_analytics(
            session_id="test_session_1",
            user_id="test_user",
            action="start"
        )
        
        # Wait a bit for background processing
        await asyncio.sleep(2)
        
        # Get analytics summary
        summary = collector.get_analytics_summary(hours=1)
        print(f"\nAnalytics Summary:")
        print(f"Total events: {summary['total_events']}")
        print(f"Event types: {dict(summary['event_types'])}")
        print(f"Query intents: {dict(summary['query_intents'])}")
        print(f"Error rate: {summary['error_rate']:.2%}")
        print(f"Avg response time: {summary['avg_response_time_ms']:.1f}ms")
        
        # Get real-time metrics
        metrics = collector.get_real_time_metrics()
        print(f"\nReal-time Metrics:")
        print(f"Queries per minute: {metrics['queries_per_minute']:.1f}")
        print(f"System uptime: {metrics['system_uptime_seconds']:.0f}s")
        
        # Test context manager
        with analytics_context(collector, EventType.TOOL_EXECUTED, 
                             session_id="test_session_1", 
                             source_component="test") as ctx:
            await asyncio.sleep(0.1)  # Simulate work
        
        print("\n✅ Analytics collector test completed")
        
        # Clean shutdown
        collector.close()
    
    asyncio.run(main())