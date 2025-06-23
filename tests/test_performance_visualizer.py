#!/usr/bin/env python3
"""
Test suite for Performance Visualizer
"""

import pytest
import asyncio
import time
import os
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timezone

# Set logfire config for testing
os.environ['LOGFIRE_IGNORE_NO_CONFIG'] = '1'

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from performance_visualizer import (
    PerformanceVisualizer,
    PerformanceMetricType,
    TrendDirection,
    AlertSeverity,
    PerformanceThreshold,
    PerformanceTrend,
    PerformanceAlert,
    PerformanceSnapshot,
    create_performance_visualizer
)
from metrics_dashboard import ChartType, TimeRange

class TestPerformanceThreshold:
    """Test performance threshold configuration."""
    
    def test_threshold_creation(self):
        """Test threshold creation."""
        threshold = PerformanceThreshold(
            metric_name="response_time",
            warning_value=500.0,
            critical_value=1000.0,
            emergency_value=2000.0,
            comparison_operator=">",
            duration_seconds=300
        )
        
        assert threshold.metric_name == "response_time"
        assert threshold.warning_value == 500.0
        assert threshold.critical_value == 1000.0
        assert threshold.emergency_value == 2000.0
        assert threshold.comparison_operator == ">"
        assert threshold.duration_seconds == 300
        assert threshold.enabled is True

class TestPerformanceTrend:
    """Test performance trend analysis."""
    
    def test_trend_creation(self):
        """Test trend analysis result creation."""
        trend = PerformanceTrend(
            metric_name="response_time",
            time_period="24h",
            direction=TrendDirection.IMPROVING,
            change_percentage=-15.5,
            confidence_score=0.85,
            data_points=100,
            start_value=200.0,
            end_value=169.0,
            slope=-0.5,
            r_squared=0.85
        )
        
        assert trend.metric_name == "response_time"
        assert trend.direction == TrendDirection.IMPROVING
        assert trend.change_percentage == -15.5
        assert trend.confidence_score == 0.85
        assert trend.data_points == 100

class TestPerformanceAlert:
    """Test performance alert system."""
    
    def test_alert_creation(self):
        """Test alert creation."""
        alert = PerformanceAlert(
            alert_id="alert_001",
            metric_name="error_rate",
            severity=AlertSeverity.WARNING,
            threshold_value=2.0,
            current_value=3.5,
            message="Error rate exceeded warning threshold"
        )
        
        assert alert.alert_id == "alert_001"
        assert alert.severity == AlertSeverity.WARNING
        assert alert.threshold_value == 2.0
        assert alert.current_value == 3.5
        assert alert.resolved is False
        assert alert.resolution_timestamp is None

class TestPerformanceVisualizer:
    """Test performance visualizer functionality."""
    
    @pytest.fixture
    def mock_analytics_collector(self):
        """Create mock analytics collector."""
        collector = Mock()
        collector.events_queue = []
        
        # Add mock events with performance data
        current_time = time.time()
        
        for i in range(50):
            event = Mock()
            event.timestamp = current_time - (i * 60)  # Events every minute
            event.duration_ms = 100 + (i % 10) * 20  # Response times 100-280ms
            event.success = i % 5 != 0  # 80% success rate
            event.cpu_usage_percent = 60 + (i % 20)  # CPU 60-80%
            event.memory_usage_mb = 512 + (i % 50)   # Memory varies
            event.data = {"cache_hit": i % 3 == 0}    # 33% cache hit
            collector.events_queue.append(event)
        
        return collector
    
    @pytest.fixture
    def mock_dashboard(self):
        """Create mock dashboard."""
        dashboard = Mock()
        dashboard.create_dashboard = Mock(return_value=True)
        return dashboard
    
    @pytest.fixture
    def visualizer(self, mock_analytics_collector, mock_dashboard):
        """Create test performance visualizer."""
        return PerformanceVisualizer(mock_analytics_collector, mock_dashboard)
    
    def test_visualizer_initialization(self, mock_analytics_collector, mock_dashboard):
        """Test visualizer initialization."""
        visualizer = PerformanceVisualizer(mock_analytics_collector, mock_dashboard)
        
        assert visualizer.analytics_collector == mock_analytics_collector
        assert visualizer.dashboard == mock_dashboard
        assert len(visualizer.performance_history) == 0
        assert len(visualizer.active_alerts) == 0
        assert len(visualizer.thresholds) > 0  # Should have default thresholds
        assert visualizer.anomaly_detection_enabled is True
    
    @pytest.mark.asyncio
    async def test_create_performance_chart_line(self, visualizer):
        """Test line chart creation for performance metrics."""
        chart_data = await visualizer.create_performance_chart(
            PerformanceMetricType.RESPONSE_TIME,
            TimeRange.LAST_24_HOURS,
            ChartType.LINE
        )
        
        assert "labels" in chart_data
        assert "datasets" in chart_data
        assert isinstance(chart_data["labels"], list)
        assert isinstance(chart_data["datasets"], list)
        
        if chart_data["datasets"]:
            dataset = chart_data["datasets"][0]
            assert "label" in dataset
            assert "data" in dataset
            assert "borderColor" in dataset
    
    @pytest.mark.asyncio
    async def test_create_performance_chart_histogram(self, visualizer):
        """Test histogram chart creation."""
        chart_data = await visualizer.create_performance_chart(
            PerformanceMetricType.RESPONSE_TIME,
            TimeRange.LAST_24_HOURS,
            ChartType.HISTOGRAM
        )
        
        assert "labels" in chart_data
        assert "datasets" in chart_data
        assert "statistics" in chart_data
        
        stats = chart_data["statistics"]
        assert "mean" in stats
        assert "median" in stats
        assert "std_dev" in stats
        assert "min" in stats
        assert "max" in stats
        assert "count" in stats
    
    @pytest.mark.asyncio
    async def test_create_performance_chart_heatmap(self, visualizer):
        """Test heatmap chart creation."""
        chart_data = await visualizer.create_performance_chart(
            PerformanceMetricType.RESPONSE_TIME,
            TimeRange.LAST_24_HOURS,
            ChartType.HEATMAP
        )
        
        assert "data" in chart_data
        assert "days" in chart_data
        assert "hours" in chart_data
        assert "metric_type" in chart_data
        
        assert isinstance(chart_data["data"], list)
        assert isinstance(chart_data["hours"], list)
        assert len(chart_data["hours"]) == 24
    
    @pytest.mark.asyncio
    async def test_create_performance_chart_gauge(self, visualizer):
        """Test gauge chart creation."""
        chart_data = await visualizer.create_performance_chart(
            PerformanceMetricType.ERROR_RATE,
            TimeRange.LAST_24_HOURS,
            ChartType.GAUGE,
            warning_threshold=2.0,
            critical_threshold=5.0
        )
        
        assert "value" in chart_data
        assert "max" in chart_data
        assert "warning_threshold" in chart_data
        assert "critical_threshold" in chart_data
        assert "unit" in chart_data
        assert "status" in chart_data
        
        assert isinstance(chart_data["value"], (int, float))
        assert chart_data["warning_threshold"] == 2.0
        assert chart_data["critical_threshold"] == 5.0
    
    @pytest.mark.asyncio
    async def test_analyze_performance_trends(self, visualizer):
        """Test performance trend analysis."""
        trends = await visualizer.analyze_performance_trends(["1h", "24h"])
        
        assert isinstance(trends, dict)
        
        for trend_key, trend in trends.items():
            assert isinstance(trend, PerformanceTrend)
            assert trend.metric_name in [mt.value for mt in PerformanceMetricType]
            assert trend.time_period in ["1h", "24h"]
            assert isinstance(trend.direction, TrendDirection)
            assert isinstance(trend.change_percentage, (int, float))
            assert isinstance(trend.confidence_score, (int, float))
            assert trend.data_points >= 0
    
    @pytest.mark.asyncio
    async def test_detect_performance_anomalies(self, visualizer):
        """Test anomaly detection."""
        anomalies = await visualizer.detect_performance_anomalies(TimeRange.LAST_24_HOURS)
        
        assert isinstance(anomalies, list)
        
        for anomaly in anomalies:
            assert "metric_type" in anomaly
            assert "timestamp" in anomaly
            assert "value" in anomaly
            assert "expected_value" in anomaly
            assert "deviation" in anomaly
            assert "severity" in anomaly
            assert "z_score" in anomaly
            
            assert anomaly["severity"] in ["info", "warning", "critical"]
            assert isinstance(anomaly["z_score"], (int, float))
    
    @pytest.mark.asyncio
    async def test_create_performance_dashboard(self, visualizer):
        """Test performance dashboard creation."""
        dashboard_id = await visualizer.create_performance_dashboard()
        
        assert dashboard_id == "performance_analysis"
        visualizer.dashboard.create_dashboard.assert_called_once()
        
        # Check that the dashboard was created with proper configuration
        call_args = visualizer.dashboard.create_dashboard.call_args[0][0]
        assert call_args.dashboard_id == "performance_analysis"
        assert call_args.title == "Performance Analysis & Monitoring"
        assert len(call_args.charts) > 0
    
    def test_process_events_for_response_time(self, visualizer):
        """Test event processing for response time metrics."""
        # Create mock events with duration_ms
        events = []
        for i in range(10):
            event = Mock()
            event.timestamp = time.time() - i * 60
            event.duration_ms = 100 + i * 10
            events.append(event)
        
        data = visualizer._process_events_for_metric(events, PerformanceMetricType.RESPONSE_TIME)
        
        assert len(data) == 10
        for i, point in enumerate(data):
            assert point["value"] == 100 + i * 10
            assert point["metric"] == "response_time_ms"
    
    def test_process_events_for_error_rate(self, visualizer):
        """Test event processing for error rate metrics."""
        events = []
        for i in range(10):
            event = Mock()
            event.timestamp = time.time() - i * 60
            event.success = i % 3 != 0  # 2/3 success rate
            events.append(event)
        
        data = visualizer._process_events_for_metric(events, PerformanceMetricType.ERROR_RATE)
        
        assert len(data) == 10
        success_count = sum(1 for point in data if point["value"] == 0)
        error_count = sum(1 for point in data if point["value"] == 1)
        assert success_count + error_count == 10
    
    def test_process_events_for_throughput(self, visualizer):
        """Test event processing for throughput metrics."""
        events = []
        for i in range(5):
            event = Mock()
            event.timestamp = time.time() - i * 60
            events.append(event)
        
        data = visualizer._process_events_for_metric(events, PerformanceMetricType.THROUGHPUT)
        
        assert len(data) == 5
        for point in data:
            assert point["value"] == 1
            assert point["metric"] == "throughput"
    
    def test_calculate_trend_improving(self, visualizer):
        """Test trend calculation for improving metrics."""
        # Create data with improving trend (decreasing response times)
        data = []
        for i in range(10):
            data.append({
                "timestamp": time.time() - (10 - i) * 60,
                "value": 200 - i * 10  # Decreasing from 200 to 110
            })
        
        trend = visualizer._calculate_trend(data, "response_time", "1h")
        
        assert trend.metric_name == "response_time"
        assert trend.time_period == "1h"
        assert trend.data_points == 10
        assert trend.start_value == 200
        assert trend.end_value == 110
        assert trend.change_percentage < 0  # Negative change for improvement
    
    def test_calculate_trend_stable(self, visualizer):
        """Test trend calculation for stable metrics."""
        # Create data with stable values
        data = []
        for i in range(10):
            data.append({
                "timestamp": time.time() - (10 - i) * 60,
                "value": 150 + (i % 2)  # Values oscillate between 150-151
            })
        
        trend = visualizer._calculate_trend(data, "response_time", "1h")
        
        assert trend.metric_name == "response_time"
        assert abs(trend.change_percentage) < 10  # Small change
    
    def test_get_metric_unit(self, visualizer):
        """Test metric unit retrieval."""
        assert visualizer._get_metric_unit(PerformanceMetricType.RESPONSE_TIME) == "ms"
        assert visualizer._get_metric_unit(PerformanceMetricType.THROUGHPUT) == "qps"
        assert visualizer._get_metric_unit(PerformanceMetricType.ERROR_RATE) == "%"
        assert visualizer._get_metric_unit(PerformanceMetricType.RESOURCE_USAGE) == "%"
        assert visualizer._get_metric_unit(PerformanceMetricType.CACHE_HIT_RATE) == "%"
    
    def test_get_metric_status(self, visualizer):
        """Test metric status determination."""
        assert visualizer._get_metric_status(50, 100, 200) == "good"
        assert visualizer._get_metric_status(150, 100, 200) == "warning"
        assert visualizer._get_metric_status(250, 100, 200) == "critical"
    
    def test_period_to_time_range(self, visualizer):
        """Test period string to TimeRange conversion."""
        assert visualizer._period_to_time_range("1h") == TimeRange.LAST_HOUR
        assert visualizer._period_to_time_range("6h") == TimeRange.LAST_6_HOURS
        assert visualizer._period_to_time_range("24h") == TimeRange.LAST_24_HOURS
        assert visualizer._period_to_time_range("7d") == TimeRange.LAST_7_DAYS
        assert visualizer._period_to_time_range("30d") == TimeRange.LAST_30_DAYS
        assert visualizer._period_to_time_range("invalid") == TimeRange.LAST_24_HOURS
    
    def test_get_time_interval(self, visualizer):
        """Test time interval calculation."""
        assert visualizer._get_time_interval(30) == 300     # 5 minutes
        assert visualizer._get_time_interval(100) == 900    # 15 minutes
        assert visualizer._get_time_interval(300) == 1800   # 30 minutes
        assert visualizer._get_time_interval(1000) == 3600  # 1 hour
    
    def test_calculate_anomaly_severity(self, visualizer):
        """Test anomaly severity calculation."""
        threshold = 100.0
        
        assert visualizer._calculate_anomaly_severity(350, threshold) == "critical"  # 3.5x threshold
        assert visualizer._calculate_anomaly_severity(250, threshold) == "warning"   # 2.5x threshold
        assert visualizer._calculate_anomaly_severity(150, threshold) == "info"      # 1.5x threshold
    
    def test_default_thresholds_setup(self, visualizer):
        """Test default threshold configuration."""
        assert "response_time" in visualizer.thresholds
        assert "error_rate" in visualizer.thresholds
        assert "resource_usage" in visualizer.thresholds
        
        response_threshold = visualizer.thresholds["response_time"]
        assert response_threshold.warning_value == 500.0
        assert response_threshold.critical_value == 1000.0
        assert response_threshold.emergency_value == 2000.0
        
        error_threshold = visualizer.thresholds["error_rate"]
        assert error_threshold.warning_value == 2.0
        assert error_threshold.critical_value == 5.0
        assert error_threshold.emergency_value == 10.0

class TestPerformanceMetricTypes:
    """Test performance metric type enums."""
    
    def test_metric_type_values(self):
        """Test metric type enum values."""
        assert PerformanceMetricType.RESPONSE_TIME.value == "response_time"
        assert PerformanceMetricType.THROUGHPUT.value == "throughput"
        assert PerformanceMetricType.ERROR_RATE.value == "error_rate"
        assert PerformanceMetricType.RESOURCE_USAGE.value == "resource_usage"
        assert PerformanceMetricType.LATENCY_PERCENTILES.value == "latency_percentiles"
        assert PerformanceMetricType.CONCURRENCY.value == "concurrency"
        assert PerformanceMetricType.CACHE_HIT_RATE.value == "cache_hit_rate"
        assert PerformanceMetricType.QUERY_COMPLEXITY.value == "query_complexity"

class TestTrendDirection:
    """Test trend direction enum."""
    
    def test_trend_direction_values(self):
        """Test trend direction enum values."""
        assert TrendDirection.IMPROVING.value == "improving"
        assert TrendDirection.DEGRADING.value == "degrading"
        assert TrendDirection.STABLE.value == "stable"
        assert TrendDirection.VOLATILE.value == "volatile"

class TestAlertSeverity:
    """Test alert severity enum."""
    
    def test_alert_severity_values(self):
        """Test alert severity enum values."""
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.CRITICAL.value == "critical"
        assert AlertSeverity.EMERGENCY.value == "emergency"

class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_create_performance_visualizer(self):
        """Test visualizer creation utility."""
        mock_collector = Mock()
        mock_dashboard = Mock()
        
        visualizer = create_performance_visualizer(mock_collector, mock_dashboard)
        
        assert isinstance(visualizer, PerformanceVisualizer)
        assert visualizer.analytics_collector == mock_collector
        assert visualizer.dashboard == mock_dashboard

class TestPerformanceSnapshot:
    """Test performance snapshot data structure."""
    
    def test_snapshot_creation(self):
        """Test performance snapshot creation."""
        snapshot = PerformanceSnapshot(
            timestamp=time.time(),
            response_time_ms=150.5,
            throughput_qps=25.3,
            error_rate_percent=1.5,
            cpu_usage_percent=75.2,
            memory_usage_mb=512.0,
            active_sessions=42,
            cache_hit_rate_percent=85.0,
            query_complexity_avg=3.2
        )
        
        assert isinstance(snapshot.timestamp, float)
        assert snapshot.response_time_ms == 150.5
        assert snapshot.throughput_qps == 25.3
        assert snapshot.error_rate_percent == 1.5
        assert snapshot.cpu_usage_percent == 75.2
        assert snapshot.memory_usage_mb == 512.0
        assert snapshot.active_sessions == 42
        assert snapshot.cache_hit_rate_percent == 85.0
        assert snapshot.query_complexity_avg == 3.2

if __name__ == "__main__":
    pytest.main([__file__, "-v"])