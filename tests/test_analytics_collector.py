#!/usr/bin/env python3
"""
Test suite for Analytics Collector
"""

import pytest
import asyncio
import time
import json
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import threading

# Set logfire config for testing
os.environ['LOGFIRE_IGNORE_NO_CONFIG'] = '1'

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from analytics_collector import (
    AnalyticsCollector,
    AnalyticsConfig,
    AnalyticsEvent,
    Metric,
    EventType,
    MetricType,
    create_analytics_collector,
    analytics_context
)

class TestAnalyticsConfig:
    """Test analytics configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = AnalyticsConfig()
        
        assert config.enabled is True
        assert config.batch_size == 100
        assert config.flush_interval_seconds == 60
        assert config.max_memory_events == 10000
        assert config.storage_backend == "file"
        assert config.retention_days == 30
        assert config.async_processing is True
        assert config.anonymize_user_data is False
        assert config.collect_system_metrics is True
        assert config.enable_real_time_aggregation is True
        assert config.error_rate_threshold == 0.1
        assert config.response_time_threshold_ms == 5000
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = AnalyticsConfig(
            enabled=False,
            batch_size=50,
            flush_interval_seconds=30,
            storage_backend="redis",
            anonymize_user_data=True,
            error_rate_threshold=0.05
        )
        
        assert config.enabled is False
        assert config.batch_size == 50
        assert config.flush_interval_seconds == 30
        assert config.storage_backend == "redis"
        assert config.anonymize_user_data is True
        assert config.error_rate_threshold == 0.05

class TestAnalyticsEvent:
    """Test analytics event data structure."""
    
    def test_event_creation(self):
        """Test analytics event creation."""
        event = AnalyticsEvent(
            event_type=EventType.QUERY_COMPLETED,
            session_id="test_session",
            user_id="test_user",
            query="test query",
            intent="search",
            duration_ms=100.5,
            success=True
        )
        
        assert event.event_type == EventType.QUERY_COMPLETED
        assert event.session_id == "test_session"
        assert event.user_id == "test_user"
        assert event.query == "test query"
        assert event.intent == "search"
        assert event.duration_ms == 100.5
        assert event.success is True
        assert isinstance(event.event_id, str)
        assert isinstance(event.timestamp, float)
        assert isinstance(event.data, dict)
        assert isinstance(event.tags, list)
    
    def test_event_to_dict(self):
        """Test event serialization to dictionary."""
        event = AnalyticsEvent(
            event_type=EventType.SEARCH_EXECUTED,
            query="test",
            data={"test_key": "test_value"}
        )
        
        event_dict = event.to_dict()
        
        assert isinstance(event_dict, dict)
        assert event_dict["event_type"] == EventType.SEARCH_EXECUTED
        assert event_dict["query"] == "test"
        assert event_dict["data"]["test_key"] == "test_value"
    
    def test_event_to_json(self):
        """Test event serialization to JSON."""
        event = AnalyticsEvent(
            event_type=EventType.TOOL_EXECUTED,
            success=True
        )
        
        json_str = event.to_json()
        
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["event_type"] == "tool_executed"
        assert parsed["success"] is True

class TestMetric:
    """Test metric data structure."""
    
    def test_metric_creation(self):
        """Test metric creation."""
        metric = Metric(
            name="response_time",
            type=MetricType.TIMING,
            value=150.5,
            tags={"endpoint": "/search"},
            unit="ms"
        )
        
        assert metric.name == "response_time"
        assert metric.type == MetricType.TIMING
        assert metric.value == 150.5
        assert metric.tags["endpoint"] == "/search"
        assert metric.unit == "ms"
        assert isinstance(metric.timestamp, float)
    
    def test_metric_to_dict(self):
        """Test metric serialization."""
        metric = Metric(
            name="cpu_usage",
            type=MetricType.GAUGE,
            value=75.2
        )
        
        metric_dict = metric.to_dict()
        
        assert isinstance(metric_dict, dict)
        assert metric_dict["name"] == "cpu_usage"
        assert metric_dict["type"] == MetricType.GAUGE
        assert metric_dict["value"] == 75.2

class TestAnalyticsCollector:
    """Test analytics collector functionality."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def collector(self, temp_storage):
        """Create test analytics collector."""
        config = AnalyticsConfig(
            enabled=True,
            storage_path=temp_storage,
            async_processing=False,  # Disable for testing
            flush_interval_seconds=1
        )
        collector = AnalyticsCollector(config)
        yield collector
        collector.close()
    
    @pytest.fixture
    def disabled_collector(self, temp_storage):
        """Create disabled analytics collector."""
        config = AnalyticsConfig(
            enabled=False,
            storage_path=temp_storage
        )
        collector = AnalyticsCollector(config)
        yield collector
        collector.close()
    
    def test_collector_initialization(self, temp_storage):
        """Test collector initialization."""
        config = AnalyticsConfig(storage_path=temp_storage)
        collector = AnalyticsCollector(config)
        
        assert collector.config == config
        assert len(collector.events_queue) == 0
        assert len(collector.metrics_queue) == 0
        assert isinstance(collector.start_time, float)
        assert collector.storage_path.exists()
        
        collector.close()
    
    def test_record_event(self, collector):
        """Test event recording."""
        event = AnalyticsEvent(
            event_type=EventType.QUERY_COMPLETED,
            session_id="test_session",
            success=True
        )
        
        collector.record_event(event)
        
        assert len(collector.events_queue) == 1
        recorded_event = collector.events_queue[0]
        assert recorded_event.event_type == EventType.QUERY_COMPLETED
        assert recorded_event.session_id == "test_session"
        assert recorded_event.success is True
    
    def test_record_event_disabled(self, disabled_collector):
        """Test event recording when disabled."""
        event = AnalyticsEvent(event_type=EventType.QUERY_COMPLETED)
        
        disabled_collector.record_event(event)
        
        assert len(disabled_collector.events_queue) == 0
    
    def test_record_metric(self, collector):
        """Test metric recording."""
        collector.record_metric(
            name="test_metric",
            value=100.5,
            metric_type=MetricType.GAUGE,
            tags={"test": "value"},
            unit="ms"
        )
        
        assert len(collector.metrics_queue) == 1
        metric = collector.metrics_queue[0]
        assert metric.name == "test_metric"
        assert metric.value == 100.5
        assert metric.type == MetricType.GAUGE
        assert metric.tags["test"] == "value"
        assert metric.unit == "ms"
    
    def test_record_metric_disabled(self, disabled_collector):
        """Test metric recording when disabled."""
        disabled_collector.record_metric("test", 100)
        
        assert len(disabled_collector.metrics_queue) == 0
    
    def test_record_query_analytics(self, collector):
        """Test query analytics recording."""
        collector.record_query_analytics(
            query="How to use Python?",
            intent="explain",
            session_id="test_session",
            user_id="test_user",
            processing_time_ms=150.5,
            success=True,
            results_count=5,
            search_strategy="hybrid"
        )
        
        # Should record event and metrics
        assert len(collector.events_queue) == 1
        assert len(collector.metrics_queue) == 2  # processing time + results count
        
        event = collector.events_queue[0]
        assert event.event_type == EventType.QUERY_COMPLETED
        assert event.query == "How to use Python?"
        assert event.intent == "explain"
        assert event.session_id == "test_session"
        assert event.duration_ms == 150.5
        assert event.success is True
        assert event.data["results_count"] == 5
        assert event.data["search_strategy"] == "hybrid"
    
    def test_record_query_analytics_failure(self, collector):
        """Test query analytics recording for failures."""
        collector.record_query_analytics(
            query="test query",
            intent="search",
            session_id="test_session",
            success=False,
            error="Test error"
        )
        
        event = collector.events_queue[0]
        assert event.event_type == EventType.QUERY_FAILED
        assert event.success is False
        assert event.error_message == "Test error"
    
    def test_record_search_analytics(self, collector):
        """Test search analytics recording."""
        collector.record_search_analytics(
            search_type="semantic",
            query="test query",
            duration_ms=75.2,
            results_found=3,
            cache_hit=True
        )
        
        assert len(collector.events_queue) == 1
        assert len(collector.metrics_queue) == 2  # duration + results
        
        event = collector.events_queue[0]
        assert event.event_type == EventType.SEARCH_EXECUTED
        assert event.duration_ms == 75.2
        assert event.data["search_type"] == "semantic"
        assert event.data["results_found"] == 3
        assert event.data["cache_hit"] is True
        assert "cache_hit" in event.tags
    
    def test_record_tool_analytics(self, collector):
        """Test tool analytics recording."""
        collector.record_tool_analytics(
            tool_name="calculator",
            operation="execute",
            duration_ms=25.1,
            success=True
        )
        
        assert len(collector.events_queue) == 1
        assert len(collector.metrics_queue) == 1
        
        event = collector.events_queue[0]
        assert event.event_type == EventType.TOOL_EXECUTED
        assert event.duration_ms == 25.1
        assert event.success is True
        assert event.data["tool_name"] == "calculator"
        assert event.data["operation"] == "execute"
    
    def test_record_tool_registration(self, collector):
        """Test tool registration analytics."""
        collector.record_tool_analytics(
            tool_name="new_tool",
            operation="register",
            success=True
        )
        
        event = collector.events_queue[0]
        assert event.event_type == EventType.TOOL_REGISTERED
        assert event.data["operation"] == "register"
    
    def test_record_session_analytics(self, collector):
        """Test session analytics recording."""
        # Start session
        collector.record_session_analytics(
            session_id="test_session",
            user_id="test_user",
            action="start"
        )
        
        assert len(collector.events_queue) == 1
        assert "test_session" in collector.session_stats
        
        session_data = collector.session_stats["test_session"]
        assert session_data["user_id"] == "test_user"
        assert "start_time" in session_data
        
        # End session
        collector.record_session_analytics(
            session_id="test_session",
            action="end",
            duration_seconds=300,
            queries_count=5
        )
        
        assert len(collector.events_queue) == 2
        session_data = collector.session_stats["test_session"]
        assert session_data["duration_seconds"] == 300
        assert session_data["queries_count"] == 5
    
    @patch('analytics_collector.psutil')
    def test_record_performance_metrics(self, mock_psutil, collector):
        """Test performance metrics recording."""
        # Mock psutil
        mock_psutil.cpu_percent.return_value = 75.5
        mock_memory = Mock()
        mock_memory.used = 1024 * 1024 * 512  # 512MB
        mock_memory.total = 1024 * 1024 * 1024 * 8  # 8GB
        mock_memory.available = 1024 * 1024 * 1024 * 4  # 4GB
        mock_memory.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_psutil.cpu_count.return_value = 8
        
        collector.record_performance_metrics()
        
        assert len(collector.events_queue) == 1
        assert len(collector.metrics_queue) == 3  # CPU, memory used, memory percent
        
        event = collector.events_queue[0]
        assert event.event_type == EventType.PERFORMANCE_METRIC
        assert event.cpu_usage_percent == 75.5
        assert event.memory_usage_mb == 512.0
    
    def test_record_performance_metrics_no_psutil(self, collector):
        """Test performance metrics without psutil."""
        with patch.dict('sys.modules', {'psutil': None}):
            collector.record_performance_metrics()
        
        assert len(collector.events_queue) == 1
        event = collector.events_queue[0]
        assert event.event_type == EventType.SYSTEM_HEALTH
        assert "uptime_seconds" in event.data
    
    def test_get_analytics_summary(self, collector):
        """Test analytics summary generation."""
        # Add some test events
        current_time = time.time()
        
        # Successful query
        event1 = AnalyticsEvent(
            event_type=EventType.QUERY_COMPLETED,
            intent="search",
            duration_ms=100.0,
            success=True,
            timestamp=current_time
        )
        collector.record_event(event1)
        
        # Failed query
        event2 = AnalyticsEvent(
            event_type=EventType.QUERY_FAILED,
            intent="explain",
            success=False,
            timestamp=current_time
        )
        collector.record_event(event2)
        
        # Session start
        collector.record_session_analytics("session1", "user1", "start")
        
        summary = collector.get_analytics_summary(hours=1)
        
        assert summary["total_events"] == 3
        assert summary["event_types"]["query_completed"] == 1
        assert summary["event_types"]["query_failed"] == 1
        assert summary["event_types"]["session_started"] == 1
        assert summary["query_intents"]["search"] == 1
        assert summary["query_intents"]["explain"] == 1
        assert summary["error_rate"] == 0.5  # 1 failure out of 2 queries
        assert summary["avg_response_time_ms"] == 100.0
        assert summary["active_sessions"] == 1
    
    def test_get_real_time_metrics(self, collector):
        """Test real-time metrics generation."""
        # Add some recent events
        current_time = time.time()
        
        for i in range(3):
            event = AnalyticsEvent(
                event_type=EventType.QUERY_COMPLETED,
                duration_ms=100.0 + i * 10,
                timestamp=current_time - 60  # 1 minute ago
            )
            collector.record_event(event)
        
        metrics = collector.get_real_time_metrics()
        
        assert "current_timestamp" in metrics
        assert "queries_per_minute" in metrics
        assert "avg_response_time_ms" in metrics
        assert "system_uptime_seconds" in metrics
        assert metrics["queries_per_minute"] > 0
        assert metrics["avg_response_time_ms"] > 0
    
    def test_flush_data(self, collector, temp_storage):
        """Test data flushing to storage."""
        # Add some events and metrics
        event = AnalyticsEvent(event_type=EventType.QUERY_COMPLETED)
        collector.record_event(event)
        
        collector.record_metric("test_metric", 100.0)
        
        # Flush data
        collector.flush_data()
        
        # Check that queues are cleared
        assert len(collector.events_queue) == 0
        assert len(collector.metrics_queue) == 0
        
        # Check that files were created
        storage_path = Path(temp_storage)
        event_files = list(storage_path.glob("events_*.jsonl"))
        metric_files = list(storage_path.glob("metrics_*.jsonl"))
        
        assert len(event_files) == 1
        assert len(metric_files) == 1
        
        # Check file contents
        with open(event_files[0], 'r') as f:
            event_data = json.loads(f.readline())
            assert event_data["event_type"] == "query_completed"
        
        with open(metric_files[0], 'r') as f:
            metric_data = json.loads(f.readline())
            assert metric_data["name"] == "test_metric"
            assert metric_data["value"] == 100.0
    
    def test_privacy_anonymization(self, temp_storage):
        """Test user data anonymization."""
        config = AnalyticsConfig(
            storage_path=temp_storage,
            anonymize_user_data=True,
            async_processing=False
        )
        collector = AnalyticsCollector(config)
        
        event = AnalyticsEvent(
            event_type=EventType.QUERY_COMPLETED,
            user_id="sensitive_user_id"
        )
        
        collector.record_event(event)
        
        recorded_event = collector.events_queue[0]
        assert recorded_event.user_id != "sensitive_user_id"
        assert len(recorded_event.user_id) == 16  # Anonymized hash
        
        collector.close()
    
    def test_query_content_privacy(self, temp_storage):
        """Test query content privacy setting."""
        config = AnalyticsConfig(
            storage_path=temp_storage,
            collect_query_content=False,
            async_processing=False
        )
        collector = AnalyticsCollector(config)
        
        event = AnalyticsEvent(
            event_type=EventType.QUERY_COMPLETED,
            query="sensitive query content"
        )
        
        collector.record_event(event)
        
        recorded_event = collector.events_queue[0]
        assert recorded_event.query is None
        
        collector.close()
    
    def test_real_time_aggregation(self, collector):
        """Test real-time statistics aggregation."""
        # Record some events
        for i in range(5):
            event = AnalyticsEvent(
                event_type=EventType.QUERY_COMPLETED,
                intent="search",
                duration_ms=100.0 + i * 10,
                success=True
            )
            collector.record_event(event)
        
        # Check aggregated stats
        assert collector.real_time_stats["events"]["total"] == 5
        assert collector.real_time_stats["events"]["query_completed"] == 5
        assert collector.real_time_stats["intents"]["search"] == 5
        assert collector.real_time_stats["outcomes"]["success"] == 5
        
        # Check timing stats
        timing_key = "timing_query_completed"
        assert timing_key in collector.real_time_stats
        assert len(collector.real_time_stats[timing_key]) == 5
    
    def test_collector_close(self, collector):
        """Test collector shutdown."""
        # Add some data
        collector.record_event(AnalyticsEvent(event_type=EventType.QUERY_COMPLETED))
        
        # Close collector
        collector.close()
        
        # Should have flushed data
        assert len(collector.events_queue) == 0

class TestAnalyticsContext:
    """Test analytics context manager."""
    
    @pytest.fixture
    def collector(self, tmp_path):
        """Create test collector."""
        config = AnalyticsConfig(
            storage_path=str(tmp_path),
            async_processing=False
        )
        collector = AnalyticsCollector(config)
        yield collector
        collector.close()
    
    def test_context_manager_success(self, collector):
        """Test context manager for successful operations."""
        with analytics_context(collector, EventType.TOOL_EXECUTED, 
                             session_id="test_session") as ctx:
            time.sleep(0.01)  # Simulate some work
        
        assert len(collector.events_queue) == 1
        event = collector.events_queue[0]
        assert event.event_type == EventType.TOOL_EXECUTED
        assert event.session_id == "test_session"
        assert event.success is True
        assert event.duration_ms > 0
    
    def test_context_manager_error(self, collector):
        """Test context manager for failed operations."""
        try:
            with analytics_context(collector, EventType.QUERY_COMPLETED) as ctx:
                raise ValueError("Test error")
        except ValueError:
            pass
        
        assert len(collector.events_queue) == 1
        event = collector.events_queue[0]
        assert event.event_type == EventType.QUERY_COMPLETED
        assert event.success is False
        assert event.error_message == "Test error"
        assert event.duration_ms > 0

class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_create_analytics_collector(self, tmp_path):
        """Test collector creation utility."""
        config = AnalyticsConfig(storage_path=str(tmp_path))
        collector = create_analytics_collector(config)
        
        assert isinstance(collector, AnalyticsCollector)
        assert collector.config == config
        
        collector.close()

class TestBackgroundProcessing:
    """Test background processing functionality."""
    
    def test_background_processing_disabled(self, tmp_path):
        """Test with background processing disabled."""
        config = AnalyticsConfig(
            storage_path=str(tmp_path),
            async_processing=False
        )
        collector = AnalyticsCollector(config)
        
        assert collector.processing_thread is None
        
        collector.close()
    
    def test_background_processing_enabled(self, tmp_path):
        """Test with background processing enabled."""
        config = AnalyticsConfig(
            storage_path=str(tmp_path),
            async_processing=True,
            flush_interval_seconds=1
        )
        collector = AnalyticsCollector(config)
        
        assert collector.processing_thread is not None
        assert collector.processing_thread.is_alive()
        
        collector.close()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])