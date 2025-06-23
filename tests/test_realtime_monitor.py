#!/usr/bin/env python3
"""
Test suite for Real-time Monitor
"""

import pytest
import asyncio
import time
import os
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

# Set logfire config for testing
os.environ['LOGFIRE_IGNORE_NO_CONFIG'] = '1'

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from realtime_monitor import (
    RealTimeMonitor,
    MonitoringConfig,
    MonitoringLevel,
    NotificationChannel,
    MonitoringState,
    AlertSeverity,
    RealTimeMetrics,
    MonitoringAlert,
    HealthCheckResult,
    AlertManager,
    HealthChecker,
    create_realtime_monitor
)

class TestMonitoringConfig:
    """Test monitoring configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = MonitoringConfig()
        
        assert config.enabled is True
        assert config.monitoring_level == MonitoringLevel.DETAILED
        assert config.update_interval_seconds == 5.0
        assert config.alert_cooldown_seconds == 300
        assert config.max_history_size == 1000
        assert config.response_time_warning_ms == 500.0
        assert config.response_time_critical_ms == 1000.0
        assert config.error_rate_warning_percent == 2.0
        assert config.error_rate_critical_percent == 5.0
        assert NotificationChannel.CONSOLE in config.notification_channels
        assert config.enable_predictive_alerts is True
        assert config.enable_anomaly_detection is True
        assert config.enable_health_checks is True
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = MonitoringConfig(
            enabled=False,
            monitoring_level=MonitoringLevel.BASIC,
            update_interval_seconds=10.0,
            response_time_warning_ms=300.0,
            notification_channels=[NotificationChannel.EMAIL, NotificationChannel.WEBHOOK],
            enable_health_checks=False
        )
        
        assert config.enabled is False
        assert config.monitoring_level == MonitoringLevel.BASIC
        assert config.update_interval_seconds == 10.0
        assert config.response_time_warning_ms == 300.0
        assert NotificationChannel.EMAIL in config.notification_channels
        assert NotificationChannel.WEBHOOK in config.notification_channels
        assert config.enable_health_checks is False

class TestRealTimeMetrics:
    """Test real-time metrics data structure."""
    
    def test_metrics_creation(self):
        """Test metrics creation."""
        timestamp = time.time()
        metrics = RealTimeMetrics(
            timestamp=timestamp,
            avg_response_time_ms=150.5,
            p95_response_time_ms=250.0,
            p99_response_time_ms=400.0,
            requests_per_second=25.3,
            error_rate_percent=1.5,
            cpu_usage_percent=45.2,
            memory_usage_mb=512.0,
            memory_usage_percent=32.1,
            active_connections=42,
            active_sessions=15,
            cache_hit_rate_percent=85.0,
            queue_depth=10,
            system_health_score=92.5
        )
        
        assert metrics.timestamp == timestamp
        assert metrics.avg_response_time_ms == 150.5
        assert metrics.p95_response_time_ms == 250.0
        assert metrics.requests_per_second == 25.3
        assert metrics.error_rate_percent == 1.5
        assert metrics.cpu_usage_percent == 45.2
        assert metrics.memory_usage_mb == 512.0
        assert metrics.active_sessions == 15
        assert metrics.cache_hit_rate_percent == 85.0
        assert metrics.system_health_score == 92.5

class TestMonitoringAlert:
    """Test monitoring alert system."""
    
    def test_alert_creation(self):
        """Test alert creation."""
        timestamp = time.time()
        alert = MonitoringAlert(
            alert_id="alert_001",
            timestamp=timestamp,
            severity=AlertSeverity.WARNING,
            metric_name="response_time",
            current_value=750.0,
            threshold_value=500.0,
            message="Response time exceeded warning threshold",
            duration_seconds=120,
            source_component="api_server"
        )
        
        assert alert.alert_id == "alert_001"
        assert alert.timestamp == timestamp
        assert alert.severity == AlertSeverity.WARNING
        assert alert.metric_name == "response_time"
        assert alert.current_value == 750.0
        assert alert.threshold_value == 500.0
        assert alert.duration_seconds == 120
        assert alert.acknowledged is False
        assert alert.resolved is False
        assert alert.source_component == "api_server"

class TestHealthCheckResult:
    """Test health check result structure."""
    
    def test_health_result_creation(self):
        """Test health check result creation."""
        timestamp = time.time()
        result = HealthCheckResult(
            component="database",
            healthy=True,
            response_time_ms=25.5,
            timestamp=timestamp,
            metadata={"version": "1.0", "connections": 10}
        )
        
        assert result.component == "database"
        assert result.healthy is True
        assert result.response_time_ms == 25.5
        assert result.timestamp == timestamp
        assert result.error_message is None
        assert result.metadata["version"] == "1.0"
        assert result.metadata["connections"] == 10

class TestAlertManager:
    """Test alert management functionality."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return MonitoringConfig(
            alert_cooldown_seconds=60,
            notification_channels=[NotificationChannel.CONSOLE]
        )
    
    @pytest.fixture
    def alert_manager(self, config):
        """Create test alert manager."""
        return AlertManager(config)
    
    def test_alert_manager_initialization(self, alert_manager):
        """Test alert manager initialization."""
        assert len(alert_manager.active_alerts) == 0
        assert len(alert_manager.alert_history) == 0
        assert len(alert_manager.alert_cooldowns) == 0
        assert NotificationChannel.CONSOLE in alert_manager.notification_handlers
    
    def test_threshold_alert_creation(self, alert_manager):
        """Test threshold alert creation."""
        # Test warning alert
        alert = alert_manager.check_threshold_alert(
            "response_time", 750.0, 500.0, 1000.0
        )
        
        assert alert is not None
        assert alert.severity == AlertSeverity.WARNING
        assert alert.current_value == 750.0
        assert alert.threshold_value == 500.0
        assert "response_time_threshold" in alert_manager.active_alerts
        assert len(alert_manager.alert_history) == 1
    
    def test_critical_alert_creation(self, alert_manager):
        """Test critical alert creation."""
        alert = alert_manager.check_threshold_alert(
            "error_rate", 8.0, 2.0, 5.0
        )
        
        assert alert is not None
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.current_value == 8.0
        assert alert.threshold_value == 5.0
    
    def test_no_alert_below_threshold(self, alert_manager):
        """Test no alert creation when below thresholds."""
        alert = alert_manager.check_threshold_alert(
            "cpu_usage", 30.0, 70.0, 90.0
        )
        
        assert alert is None
        assert len(alert_manager.active_alerts) == 0
    
    def test_alert_cooldown(self, alert_manager):
        """Test alert cooldown mechanism."""
        # Create first alert
        alert1 = alert_manager.check_threshold_alert(
            "memory_usage", 800.0, 500.0, 1000.0
        )
        assert alert1 is not None
        
        # Try to create another alert immediately (should be in cooldown)
        alert2 = alert_manager.check_threshold_alert(
            "memory_usage", 850.0, 500.0, 1000.0
        )
        assert alert2 is None  # Should be blocked by cooldown
    
    def test_alert_resolution(self, alert_manager):
        """Test alert resolution when metric returns to normal."""
        # Create alert
        alert = alert_manager.check_threshold_alert(
            "response_time", 1200.0, 500.0, 1000.0
        )
        assert alert is not None
        assert len(alert_manager.active_alerts) == 1
        
        # Return to normal value
        resolved_alert = alert_manager.check_threshold_alert(
            "response_time", 300.0, 500.0, 1000.0
        )
        assert resolved_alert is None
        assert len(alert_manager.active_alerts) == 0  # Should be resolved

class TestHealthChecker:
    """Test health checking functionality."""
    
    @pytest.fixture
    def mock_analytics_collector(self):
        """Create mock analytics collector."""
        collector = Mock()
        collector.events_queue = []
        return collector
    
    @pytest.fixture
    def health_checker(self, mock_analytics_collector):
        """Create test health checker."""
        return HealthChecker(mock_analytics_collector)
    
    def test_health_checker_initialization(self, health_checker):
        """Test health checker initialization."""
        assert len(health_checker.health_checks) >= 3  # Default health checks
        assert "analytics" in health_checker.health_checks
        assert "memory" in health_checker.health_checks
        assert "disk" in health_checker.health_checks
    
    def test_register_health_check(self, health_checker):
        """Test registering custom health check."""
        def custom_check():
            return True
        
        health_checker.register_health_check("custom", custom_check)
        
        assert "custom" in health_checker.health_checks
        assert health_checker.health_checks["custom"] == custom_check
    
    @pytest.mark.asyncio
    async def test_run_health_checks(self, health_checker):
        """Test running health checks."""
        # Register a test health check
        def test_check():
            return True
        
        health_checker.register_health_check("test", test_check)
        
        results = await health_checker.run_health_checks()
        
        assert isinstance(results, dict)
        assert "test" in results
        assert results["test"].healthy is True
        assert results["test"].component == "test"
        assert results["test"].response_time_ms >= 0
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, health_checker):
        """Test health check failure handling."""
        def failing_check():
            raise Exception("Test failure")
        
        health_checker.register_health_check("failing", failing_check)
        
        results = await health_checker.run_health_checks()
        
        assert "failing" in results
        assert results["failing"].healthy is False
        assert "Test failure" in results["failing"].error_message
    
    @pytest.mark.asyncio
    async def test_async_health_check(self, health_checker):
        """Test asynchronous health check."""
        async def async_check():
            await asyncio.sleep(0.01)
            return True
        
        health_checker.register_health_check("async_test", async_check)
        
        results = await health_checker.run_health_checks()
        
        assert "async_test" in results
        assert results["async_test"].healthy is True

class TestRealTimeMonitor:
    """Test real-time monitoring functionality."""
    
    @pytest.fixture
    def mock_analytics_collector(self):
        """Create mock analytics collector."""
        collector = Mock()
        collector.events_queue = []
        
        # Add mock events
        current_time = time.time()
        for i in range(10):
            event = Mock()
            event.timestamp = current_time - (i * 10)
            event.duration_ms = 100 + (i * 20)
            event.success = i % 5 != 0  # 80% success rate
            event.session_id = f"session_{i % 3}"
            event.data = {"cache_hit": i % 4 == 0}
            collector.events_queue.append(event)
        
        return collector
    
    @pytest.fixture
    def mock_dashboard(self):
        """Create mock dashboard."""
        return Mock()
    
    @pytest.fixture
    def mock_performance_visualizer(self):
        """Create mock performance visualizer."""
        return Mock()
    
    @pytest.fixture
    def test_config(self):
        """Create test configuration."""
        return MonitoringConfig(
            update_interval_seconds=0.1,  # Fast updates for testing
            alert_cooldown_seconds=1,     # Short cooldown for testing
            health_check_interval_seconds=1
        )
    
    @pytest.fixture
    def monitor(self, mock_analytics_collector, mock_dashboard, 
                mock_performance_visualizer, test_config):
        """Create test monitor."""
        return RealTimeMonitor(
            mock_analytics_collector,
            mock_dashboard,
            mock_performance_visualizer,
            test_config
        )
    
    def test_monitor_initialization(self, monitor):
        """Test monitor initialization."""
        assert monitor.state == MonitoringState.STOPPED
        assert monitor.monitoring_task is None
        assert monitor.health_check_task is None
        assert isinstance(monitor.alert_manager, AlertManager)
        assert isinstance(monitor.health_checker, HealthChecker)
        assert len(monitor.metrics_history) == 0
        assert monitor.current_metrics is None
    
    @pytest.mark.asyncio
    async def test_collect_current_metrics(self, monitor):
        """Test current metrics collection."""
        metrics = await monitor._collect_current_metrics()
        
        assert isinstance(metrics, RealTimeMetrics)
        assert metrics.timestamp > 0
        assert metrics.avg_response_time_ms >= 0
        assert metrics.requests_per_second >= 0
        assert metrics.error_rate_percent >= 0
        assert 0 <= metrics.system_health_score <= 100
    
    @pytest.mark.asyncio
    async def test_system_metrics_collection(self, monitor):
        """Test system metrics collection."""
        cpu, memory_mb, memory_percent = await monitor._get_system_metrics()
        
        assert isinstance(cpu, float)
        assert isinstance(memory_mb, float)
        assert isinstance(memory_percent, float)
        assert cpu >= 0
        assert memory_mb >= 0
        assert memory_percent >= 0
    
    @pytest.mark.asyncio
    async def test_health_score_calculation(self, monitor):
        """Test health score calculation."""
        # Test perfect score
        score = await monitor._calculate_health_score(50.0, 0.0, 20.0)
        assert score > 90
        
        # Test degraded score
        score = await monitor._calculate_health_score(800.0, 10.0, 95.0)
        assert score < 50
    
    @pytest.mark.asyncio
    async def test_alert_checking(self, monitor):
        """Test alert checking against thresholds."""
        # Create metrics that should trigger alerts
        metrics = RealTimeMetrics(
            timestamp=time.time(),
            avg_response_time_ms=1200.0,  # Above critical threshold
            error_rate_percent=8.0,       # Above critical threshold
            cpu_usage_percent=95.0,       # Above critical threshold
            memory_usage_mb=3000.0        # Above critical threshold
        )
        
        await monitor._check_alerts(metrics)
        
        # Should have created alerts
        active_alerts = monitor.get_active_alerts()
        assert len(active_alerts) > 0
        
        # Check for specific alert types
        alert_metrics = {alert.metric_name for alert in active_alerts}
        assert "response_time" in alert_metrics
        assert "error_rate" in alert_metrics
    
    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, monitor):
        """Test monitoring lifecycle."""
        # Test start
        assert monitor.state == MonitoringState.STOPPED
        
        start_result = await monitor.start_monitoring()
        assert start_result is True
        assert monitor.state == MonitoringState.RUNNING
        assert monitor.monitoring_task is not None
        
        # Let it run briefly
        await asyncio.sleep(0.2)
        
        # Check that metrics are being collected
        assert monitor.current_metrics is not None
        assert len(monitor.metrics_history) > 0
        
        # Test stop
        stop_result = await monitor.stop_monitoring()
        assert stop_result is True
        assert monitor.state == MonitoringState.STOPPED
    
    @pytest.mark.asyncio
    async def test_double_start_monitoring(self, monitor):
        """Test starting monitoring when already running."""
        # Start first time
        result1 = await monitor.start_monitoring()
        assert result1 is True
        
        # Try to start again
        result2 = await monitor.start_monitoring()
        assert result2 is False  # Should fail
        
        # Cleanup
        await monitor.stop_monitoring()
    
    def test_subscriber_management(self, monitor):
        """Test metric and alert subscriber management."""
        metric_callback = Mock()
        alert_callback = Mock()
        
        # Test subscription
        monitor.subscribe_to_metrics(metric_callback)
        monitor.subscribe_to_alerts(alert_callback)
        
        assert metric_callback in monitor.metric_subscribers
        assert alert_callback in monitor.alert_subscribers
        
        # Test unsubscription
        monitor.unsubscribe_from_metrics(metric_callback)
        monitor.unsubscribe_from_alerts(alert_callback)
        
        assert metric_callback not in monitor.metric_subscribers
        assert alert_callback not in monitor.alert_subscribers
    
    @pytest.mark.asyncio
    async def test_metric_subscriber_notification(self, monitor):
        """Test metric subscriber notifications."""
        received_metrics = []
        
        def metric_callback(metrics):
            received_metrics.append(metrics)
        
        monitor.subscribe_to_metrics(metric_callback)
        
        # Trigger metric collection
        test_metrics = RealTimeMetrics(timestamp=time.time())
        await monitor._notify_metric_subscribers(test_metrics)
        
        assert len(received_metrics) == 1
        assert received_metrics[0] == test_metrics
    
    @pytest.mark.asyncio
    async def test_alert_subscriber_notification(self, monitor):
        """Test alert subscriber notifications."""
        received_alerts = []
        
        def alert_callback(alert):
            received_alerts.append(alert)
        
        monitor.subscribe_to_alerts(alert_callback)
        
        # Trigger alert
        test_alert = MonitoringAlert(
            alert_id="test",
            timestamp=time.time(),
            severity=AlertSeverity.WARNING,
            metric_name="test",
            current_value=100.0,
            threshold_value=50.0,
            message="Test alert"
        )
        
        await monitor._notify_alert_subscribers(test_alert)
        
        assert len(received_alerts) == 1
        assert received_alerts[0] == test_alert
    
    def test_get_current_metrics(self, monitor):
        """Test getting current metrics."""
        assert monitor.get_current_metrics() is None
        
        # Set current metrics
        test_metrics = RealTimeMetrics(timestamp=time.time())
        monitor.current_metrics = test_metrics
        
        retrieved = monitor.get_current_metrics()
        assert retrieved == test_metrics
    
    def test_get_metrics_history(self, monitor):
        """Test getting metrics history."""
        current_time = time.time()
        
        # Add test metrics to history
        for i in range(5):
            metrics = RealTimeMetrics(timestamp=current_time - (i * 60))
            monitor.metrics_history.append(metrics)
        
        # Get last 3 minutes
        recent_metrics = monitor.get_metrics_history(minutes=3)
        assert len(recent_metrics) >= 3
        
        # Get last 10 minutes (should get all)
        all_metrics = monitor.get_metrics_history(minutes=10)
        assert len(all_metrics) == 5
    
    def test_get_active_alerts(self, monitor):
        """Test getting active alerts."""
        assert len(monitor.get_active_alerts()) == 0
        
        # Add test alert
        test_alert = MonitoringAlert(
            alert_id="test",
            timestamp=time.time(),
            severity=AlertSeverity.WARNING,
            metric_name="test",
            current_value=100.0,
            threshold_value=50.0,
            message="Test alert"
        )
        
        monitor.alert_manager.active_alerts["test"] = test_alert
        
        active_alerts = monitor.get_active_alerts()
        assert len(active_alerts) == 1
        assert active_alerts[0] == test_alert
    
    def test_get_alert_history(self, monitor):
        """Test getting alert history."""
        current_time = time.time()
        
        # Add test alerts to history
        for i in range(3):
            alert = MonitoringAlert(
                alert_id=f"test_{i}",
                timestamp=current_time - (i * 3600),  # Every hour
                severity=AlertSeverity.WARNING,
                metric_name="test",
                current_value=100.0,
                threshold_value=50.0,
                message=f"Test alert {i}"
            )
            monitor.alert_manager.alert_history.append(alert)
        
        # Get last 2 hours
        recent_alerts = monitor.get_alert_history(hours=2)
        assert len(recent_alerts) >= 2
        
        # Get last 24 hours (should get all)
        all_alerts = monitor.get_alert_history(hours=24)
        assert len(all_alerts) == 3

class TestEnums:
    """Test enum values."""
    
    def test_monitoring_level_values(self):
        """Test monitoring level enum values."""
        assert MonitoringLevel.BASIC.value == "basic"
        assert MonitoringLevel.DETAILED.value == "detailed"
        assert MonitoringLevel.COMPREHENSIVE.value == "comprehensive"
        assert MonitoringLevel.DEBUG.value == "debug"
    
    def test_notification_channel_values(self):
        """Test notification channel enum values."""
        assert NotificationChannel.CONSOLE.value == "console"
        assert NotificationChannel.EMAIL.value == "email"
        assert NotificationChannel.WEBHOOK.value == "webhook"
        assert NotificationChannel.SLACK.value == "slack"
        assert NotificationChannel.DASHBOARD.value == "dashboard"
    
    def test_monitoring_state_values(self):
        """Test monitoring state enum values."""
        assert MonitoringState.STARTING.value == "starting"
        assert MonitoringState.RUNNING.value == "running"
        assert MonitoringState.PAUSED.value == "paused"
        assert MonitoringState.STOPPING.value == "stopping"
        assert MonitoringState.STOPPED.value == "stopped"
        assert MonitoringState.ERROR.value == "error"

class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_create_realtime_monitor(self):
        """Test monitor creation utility."""
        mock_collector = Mock()
        mock_dashboard = Mock()
        mock_visualizer = Mock()
        config = MonitoringConfig()
        
        monitor = create_realtime_monitor(mock_collector, mock_dashboard, mock_visualizer, config)
        
        assert isinstance(monitor, RealTimeMonitor)
        assert monitor.analytics_collector == mock_collector
        assert monitor.dashboard == mock_dashboard
        assert monitor.performance_visualizer == mock_visualizer
        assert monitor.config == config

if __name__ == "__main__":
    pytest.main([__file__, "-v"])