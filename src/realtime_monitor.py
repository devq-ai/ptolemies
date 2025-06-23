#!/usr/bin/env python3
"""
Real-time Monitor for Ptolemies
Advanced real-time monitoring, alerting, and live dashboard system.
"""

import asyncio
import time
import json
import threading
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime, timezone, timedelta
from collections import defaultdict, deque
import statistics
import weakref
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

from analytics_collector import AnalyticsCollector, EventType, MetricType
from metrics_dashboard import MetricsDashboard, ChartType, TimeRange
from performance_visualizer import PerformanceVisualizer, PerformanceMetricType, AlertSeverity

# Configure Logfire
logfire.configure(send_to_logfire=False)

class MonitoringLevel(Enum):
    """Monitoring detail levels."""
    BASIC = "basic"
    DETAILED = "detailed"
    COMPREHENSIVE = "comprehensive"
    DEBUG = "debug"

class NotificationChannel(Enum):
    """Notification delivery channels."""
    CONSOLE = "console"
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    DASHBOARD = "dashboard"

class MonitoringState(Enum):
    """Real-time monitoring states."""
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"

@dataclass
class MonitoringConfig:
    """Real-time monitoring configuration."""
    enabled: bool = True
    monitoring_level: MonitoringLevel = MonitoringLevel.DETAILED
    update_interval_seconds: float = 5.0
    alert_cooldown_seconds: int = 300
    max_history_size: int = 1000
    
    # Alert thresholds
    response_time_warning_ms: float = 500.0
    response_time_critical_ms: float = 1000.0
    error_rate_warning_percent: float = 2.0
    error_rate_critical_percent: float = 5.0
    cpu_usage_warning_percent: float = 70.0
    cpu_usage_critical_percent: float = 90.0
    memory_usage_warning_mb: float = 1024.0
    memory_usage_critical_mb: float = 2048.0
    
    # Notification settings
    notification_channels: List[NotificationChannel] = field(default_factory=lambda: [NotificationChannel.CONSOLE])
    webhook_url: Optional[str] = None
    email_recipients: List[str] = field(default_factory=list)
    
    # Advanced settings
    enable_predictive_alerts: bool = True
    enable_anomaly_detection: bool = True
    enable_health_checks: bool = True
    health_check_interval_seconds: int = 30

@dataclass
class RealTimeMetrics:
    """Real-time system metrics snapshot."""
    timestamp: float
    
    # Performance metrics
    avg_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0
    requests_per_second: float = 0.0
    error_rate_percent: float = 0.0
    
    # System metrics
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    memory_usage_percent: float = 0.0
    active_connections: int = 0
    
    # Application metrics
    active_sessions: int = 0
    cache_hit_rate_percent: float = 0.0
    queue_depth: int = 0
    
    # Health indicators
    system_health_score: float = 100.0
    database_healthy: bool = True
    external_services_healthy: bool = True

@dataclass
class MonitoringAlert:
    """Real-time monitoring alert."""
    alert_id: str
    timestamp: float
    severity: AlertSeverity
    metric_name: str
    current_value: float
    threshold_value: float
    message: str
    duration_seconds: int = 0
    acknowledged: bool = False
    resolved: bool = False
    resolution_timestamp: Optional[float] = None
    source_component: str = "realtime_monitor"

@dataclass
class HealthCheckResult:
    """Health check result."""
    component: str
    healthy: bool
    response_time_ms: float
    timestamp: float
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class AlertManager:
    """Manages alerts and notifications."""
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        self.active_alerts: Dict[str, MonitoringAlert] = {}
        self.alert_history: deque = deque(maxlen=1000)
        self.alert_cooldowns: Dict[str, float] = {}
        self.notification_handlers: Dict[NotificationChannel, Callable] = {}
        
        self._setup_notification_handlers()
    
    def check_threshold_alert(self, metric_name: str, current_value: float, 
                            warning_threshold: float, critical_threshold: float) -> Optional[MonitoringAlert]:
        """Check if metric exceeds thresholds and create alert if needed."""
        
        alert_key = f"{metric_name}_threshold"
        
        # Check if we're in cooldown
        if alert_key in self.alert_cooldowns:
            if time.time() - self.alert_cooldowns[alert_key] < self.config.alert_cooldown_seconds:
                return None
        
        # Determine severity
        severity = None
        threshold_value = None
        
        if current_value >= critical_threshold:
            severity = AlertSeverity.CRITICAL
            threshold_value = critical_threshold
        elif current_value >= warning_threshold:
            severity = AlertSeverity.WARNING
            threshold_value = warning_threshold
        
        if severity is None:
            # Value is below thresholds - resolve existing alert if any
            if alert_key in self.active_alerts:
                self._resolve_alert(alert_key)
            return None
        
        # Check if alert already exists with same severity
        if alert_key in self.active_alerts:
            existing_alert = self.active_alerts[alert_key]
            if existing_alert.severity == severity:
                # Update duration
                existing_alert.duration_seconds = int(time.time() - existing_alert.timestamp)
                existing_alert.current_value = current_value
                return existing_alert
            else:
                # Severity changed - resolve old and create new
                self._resolve_alert(alert_key)
        
        # Create new alert
        alert = MonitoringAlert(
            alert_id=f"{alert_key}_{int(time.time())}",
            timestamp=time.time(),
            severity=severity,
            metric_name=metric_name,
            current_value=current_value,
            threshold_value=threshold_value,
            message=f"{metric_name.replace('_', ' ').title()} is {current_value:.2f}, exceeding {severity.value} threshold of {threshold_value}"
        )
        
        self.active_alerts[alert_key] = alert
        self.alert_history.append(alert)
        self.alert_cooldowns[alert_key] = time.time()
        
        # Send notifications
        self._send_alert_notifications(alert)
        
        return alert
    
    def _resolve_alert(self, alert_key: str):
        """Resolve an active alert."""
        if alert_key in self.active_alerts:
            alert = self.active_alerts[alert_key]
            alert.resolved = True
            alert.resolution_timestamp = time.time()
            
            # Send resolution notification
            resolution_alert = MonitoringAlert(
                alert_id=f"{alert.alert_id}_resolved",
                timestamp=time.time(),
                severity=AlertSeverity.INFO,
                metric_name=alert.metric_name,
                current_value=alert.current_value,
                threshold_value=alert.threshold_value,
                message=f"{alert.metric_name.replace('_', ' ').title()} alert resolved"
            )
            
            self._send_alert_notifications(resolution_alert)
            del self.active_alerts[alert_key]
    
    def _send_alert_notifications(self, alert: MonitoringAlert):
        """Send alert notifications through configured channels."""
        for channel in self.config.notification_channels:
            if channel in self.notification_handlers:
                try:
                    self.notification_handlers[channel](alert)
                except Exception as e:
                    logfire.error(f"Failed to send notification via {channel.value}", error=str(e))
    
    def _setup_notification_handlers(self):
        """Setup notification handlers for different channels."""
        self.notification_handlers[NotificationChannel.CONSOLE] = self._console_notification
        self.notification_handlers[NotificationChannel.DASHBOARD] = self._dashboard_notification
        
        # Additional handlers would be implemented based on configuration
        if self.config.webhook_url:
            self.notification_handlers[NotificationChannel.WEBHOOK] = self._webhook_notification
    
    def _console_notification(self, alert: MonitoringAlert):
        """Send notification to console."""
        severity_symbols = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.CRITICAL: "🚨",
            AlertSeverity.EMERGENCY: "🆘"
        }
        
        symbol = severity_symbols.get(alert.severity, "🔔")
        timestamp = datetime.fromtimestamp(alert.timestamp).strftime("%H:%M:%S")
        
        print(f"{symbol} [{timestamp}] {alert.severity.value.upper()}: {alert.message}")
    
    def _dashboard_notification(self, alert: MonitoringAlert):
        """Send notification to dashboard (placeholder)."""
        # This would integrate with the dashboard system
        logfire.info("Dashboard notification sent", alert_id=alert.alert_id)
    
    def _webhook_notification(self, alert: MonitoringAlert):
        """Send notification via webhook."""
        # This would implement webhook posting
        logfire.info("Webhook notification sent", alert_id=alert.alert_id)

class HealthChecker:
    """Performs health checks on system components."""
    
    def __init__(self, analytics_collector: AnalyticsCollector):
        self.analytics_collector = analytics_collector
        self.health_checks: Dict[str, Callable] = {}
        self.last_results: Dict[str, HealthCheckResult] = {}
        
        self._register_default_health_checks()
    
    def register_health_check(self, component: str, check_func: Callable) -> None:
        """Register a health check function for a component."""
        self.health_checks[component] = check_func
    
    async def run_health_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks."""
        results = {}
        
        for component, check_func in self.health_checks.items():
            try:
                start_time = time.time()
                result = await self._run_single_check(component, check_func)
                result.response_time_ms = (time.time() - start_time) * 1000
                results[component] = result
                self.last_results[component] = result
                
            except Exception as e:
                results[component] = HealthCheckResult(
                    component=component,
                    healthy=False,
                    response_time_ms=0,
                    timestamp=time.time(),
                    error_message=str(e)
                )
        
        return results
    
    async def _run_single_check(self, component: str, check_func: Callable) -> HealthCheckResult:
        """Run a single health check."""
        if asyncio.iscoroutinefunction(check_func):
            healthy = await check_func()
        else:
            healthy = check_func()
        
        return HealthCheckResult(
            component=component,
            healthy=healthy,
            response_time_ms=0,  # Will be set by caller
            timestamp=time.time()
        )
    
    def _register_default_health_checks(self):
        """Register default health checks."""
        
        def analytics_health():
            """Check analytics collector health."""
            return (hasattr(self.analytics_collector, 'events_queue') and 
                   len(self.analytics_collector.events_queue) < 10000)  # Not overloaded
        
        def memory_health():
            """Check memory usage health."""
            try:
                import psutil
                memory = psutil.virtual_memory()
                return memory.percent < 90  # Less than 90% memory usage
            except ImportError:
                return True  # Assume healthy if psutil not available
        
        def disk_health():
            """Check disk space health."""
            try:
                import psutil
                disk = psutil.disk_usage('/')
                return (disk.free / disk.total) > 0.1  # More than 10% free space
            except ImportError:
                return True
        
        self.register_health_check("analytics", analytics_health)
        self.register_health_check("memory", memory_health)
        self.register_health_check("disk", disk_health)

class RealTimeMonitor:
    """Main real-time monitoring system."""
    
    def __init__(self, analytics_collector: AnalyticsCollector,
                 dashboard: MetricsDashboard,
                 performance_visualizer: PerformanceVisualizer,
                 config: MonitoringConfig = None):
        self.analytics_collector = analytics_collector
        self.dashboard = dashboard
        self.performance_visualizer = performance_visualizer
        self.config = config or MonitoringConfig()
        
        # Monitoring state
        self.state = MonitoringState.STOPPED
        self.monitoring_task: Optional[asyncio.Task] = None
        self.health_check_task: Optional[asyncio.Task] = None
        
        # Components
        self.alert_manager = AlertManager(self.config)
        self.health_checker = HealthChecker(analytics_collector)
        
        # Real-time data storage
        self.metrics_history: deque = deque(maxlen=self.config.max_history_size)
        self.current_metrics: Optional[RealTimeMetrics] = None
        
        # Subscribers for real-time updates
        self.metric_subscribers: Set[Callable] = set()
        self.alert_subscribers: Set[Callable] = set()
        
        # Performance tracking
        self.response_times: deque = deque(maxlen=1000)
        self.request_count = 0
        self.error_count = 0
        self.last_metrics_time = time.time()
    
    @logfire.instrument("start_monitoring")
    async def start_monitoring(self) -> bool:
        """Start real-time monitoring."""
        if self.state in [MonitoringState.RUNNING, MonitoringState.STARTING]:
            logfire.warning("Monitoring already running or starting")
            return False
        
        try:
            self.state = MonitoringState.STARTING
            logfire.info("Starting real-time monitoring")
            
            # Start monitoring task
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            
            # Start health check task if enabled
            if self.config.enable_health_checks:
                self.health_check_task = asyncio.create_task(self._health_check_loop())
            
            self.state = MonitoringState.RUNNING
            logfire.info("Real-time monitoring started successfully")
            return True
            
        except Exception as e:
            self.state = MonitoringState.ERROR
            logfire.error("Failed to start monitoring", error=str(e))
            return False
    
    @logfire.instrument("stop_monitoring")
    async def stop_monitoring(self) -> bool:
        """Stop real-time monitoring."""
        if self.state == MonitoringState.STOPPED:
            return True
        
        try:
            self.state = MonitoringState.STOPPING
            logfire.info("Stopping real-time monitoring")
            
            # Cancel tasks
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            
            if self.health_check_task:
                self.health_check_task.cancel()
                try:
                    await self.health_check_task
                except asyncio.CancelledError:
                    pass
            
            self.state = MonitoringState.STOPPED
            logfire.info("Real-time monitoring stopped")
            return True
            
        except Exception as e:
            self.state = MonitoringState.ERROR
            logfire.error("Failed to stop monitoring", error=str(e))
            return False
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.state == MonitoringState.RUNNING:
            try:
                # Collect current metrics
                current_metrics = await self._collect_current_metrics()
                
                # Store metrics
                self.current_metrics = current_metrics
                self.metrics_history.append(current_metrics)
                
                # Check for alerts
                await self._check_alerts(current_metrics)
                
                # Notify subscribers
                await self._notify_metric_subscribers(current_metrics)
                
                # Wait for next update
                await asyncio.sleep(self.config.update_interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logfire.error("Error in monitoring loop", error=str(e))
                await asyncio.sleep(self.config.update_interval_seconds)
    
    async def _health_check_loop(self):
        """Health check monitoring loop."""
        while self.state == MonitoringState.RUNNING:
            try:
                # Run health checks
                health_results = await self.health_checker.run_health_checks()
                
                # Check for health-based alerts
                for component, result in health_results.items():
                    if not result.healthy:
                        alert = MonitoringAlert(
                            alert_id=f"health_{component}_{int(time.time())}",
                            timestamp=time.time(),
                            severity=AlertSeverity.CRITICAL,
                            metric_name=f"{component}_health",
                            current_value=0,
                            threshold_value=1,
                            message=f"Health check failed for {component}: {result.error_message or 'Unknown error'}",
                            source_component=component
                        )
                        
                        await self._notify_alert_subscribers(alert)
                
                # Wait for next health check
                await asyncio.sleep(self.config.health_check_interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logfire.error("Error in health check loop", error=str(e))
                await asyncio.sleep(self.config.health_check_interval_seconds)
    
    async def _collect_current_metrics(self) -> RealTimeMetrics:
        """Collect current system metrics."""
        current_time = time.time()
        
        # Get recent events for analysis
        time_window = 60  # Last 60 seconds
        cutoff_time = current_time - time_window
        
        recent_events = [
            e for e in self.analytics_collector.events_queue
            if e.timestamp >= cutoff_time
        ]
        
        # Calculate performance metrics
        response_times = [e.duration_ms for e in recent_events 
                         if hasattr(e, 'duration_ms') and e.duration_ms is not None]
        
        avg_response_time = statistics.mean(response_times) if response_times else 0.0
        p95_response_time = (statistics.quantiles(response_times, n=20)[18] 
                           if len(response_times) >= 20 else avg_response_time)
        p99_response_time = (statistics.quantiles(response_times, n=100)[98] 
                           if len(response_times) >= 100 else avg_response_time)
        
        # Calculate request rate
        requests_per_second = len(recent_events) / time_window if time_window > 0 else 0
        
        # Calculate error rate
        failed_events = [e for e in recent_events if hasattr(e, 'success') and not e.success]
        error_rate = (len(failed_events) / len(recent_events) * 100) if recent_events else 0.0
        
        # Get system metrics
        cpu_usage, memory_usage_mb, memory_percent = await self._get_system_metrics()
        
        # Calculate cache hit rate
        cache_events = [e for e in recent_events 
                       if hasattr(e, 'data') and isinstance(e.data, dict) and 'cache_hit' in e.data]
        cache_hits = [e for e in cache_events if e.data['cache_hit']]
        cache_hit_rate = (len(cache_hits) / len(cache_events) * 100) if cache_events else 0.0
        
        # Calculate health score
        health_score = await self._calculate_health_score(avg_response_time, error_rate, cpu_usage)
        
        return RealTimeMetrics(
            timestamp=current_time,
            avg_response_time_ms=avg_response_time,
            p95_response_time_ms=p95_response_time,
            p99_response_time_ms=p99_response_time,
            requests_per_second=requests_per_second,
            error_rate_percent=error_rate,
            cpu_usage_percent=cpu_usage,
            memory_usage_mb=memory_usage_mb,
            memory_usage_percent=memory_percent,
            active_connections=len(set(e.session_id for e in recent_events 
                                     if hasattr(e, 'session_id') and e.session_id)),
            active_sessions=len(set(e.session_id for e in recent_events 
                                  if hasattr(e, 'session_id') and e.session_id)),
            cache_hit_rate_percent=cache_hit_rate,
            queue_depth=len(self.analytics_collector.events_queue),
            system_health_score=health_score,
            database_healthy=True,  # Would implement actual check
            external_services_healthy=True  # Would implement actual check
        )
    
    async def _get_system_metrics(self) -> tuple[float, float, float]:
        """Get system resource metrics."""
        try:
            import psutil
            
            # Get CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Get memory usage
            memory = psutil.virtual_memory()
            memory_mb = memory.used / (1024 * 1024)
            memory_percent = memory.percent
            
            return cpu_percent, memory_mb, memory_percent
            
        except ImportError:
            # Return mock values if psutil not available
            return 25.0, 512.0, 25.0
    
    async def _calculate_health_score(self, response_time: float, error_rate: float, cpu_usage: float) -> float:
        """Calculate overall system health score (0-100)."""
        
        # Response time score (0-40 points)
        if response_time <= 100:
            response_score = 40
        elif response_time <= 500:
            response_score = 40 - ((response_time - 100) / 400 * 20)
        elif response_time <= 1000:
            response_score = 20 - ((response_time - 500) / 500 * 15)
        else:
            response_score = 5
        
        # Error rate score (0-35 points)
        if error_rate <= 1:
            error_score = 35
        elif error_rate <= 5:
            error_score = 35 - ((error_rate - 1) / 4 * 25)
        else:
            error_score = 10 - min(error_rate - 5, 10)
        
        # CPU usage score (0-25 points)
        if cpu_usage <= 50:
            cpu_score = 25
        elif cpu_usage <= 80:
            cpu_score = 25 - ((cpu_usage - 50) / 30 * 15)
        else:
            cpu_score = 10 - min((cpu_usage - 80) / 20 * 10, 10)
        
        return max(0, response_score + error_score + cpu_score)
    
    async def _check_alerts(self, metrics: RealTimeMetrics):
        """Check metrics against thresholds and generate alerts."""
        
        # Response time alerts
        response_alert = self.alert_manager.check_threshold_alert(
            "response_time",
            metrics.avg_response_time_ms,
            self.config.response_time_warning_ms,
            self.config.response_time_critical_ms
        )
        
        # Error rate alerts
        error_alert = self.alert_manager.check_threshold_alert(
            "error_rate",
            metrics.error_rate_percent,
            self.config.error_rate_warning_percent,
            self.config.error_rate_critical_percent
        )
        
        # CPU usage alerts
        cpu_alert = self.alert_manager.check_threshold_alert(
            "cpu_usage",
            metrics.cpu_usage_percent,
            self.config.cpu_usage_warning_percent,
            self.config.cpu_usage_critical_percent
        )
        
        # Memory usage alerts
        memory_alert = self.alert_manager.check_threshold_alert(
            "memory_usage",
            metrics.memory_usage_mb,
            self.config.memory_usage_warning_mb,
            self.config.memory_usage_critical_mb
        )
        
        # Notify alert subscribers for any new alerts
        for alert in [response_alert, error_alert, cpu_alert, memory_alert]:
            if alert:
                await self._notify_alert_subscribers(alert)
    
    async def _notify_metric_subscribers(self, metrics: RealTimeMetrics):
        """Notify subscribers about new metrics."""
        for subscriber in self.metric_subscribers.copy():
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    await subscriber(metrics)
                else:
                    subscriber(metrics)
            except Exception as e:
                logfire.error("Error notifying metric subscriber", error=str(e))
                # Remove invalid subscribers
                self.metric_subscribers.discard(subscriber)
    
    async def _notify_alert_subscribers(self, alert: MonitoringAlert):
        """Notify subscribers about new alerts."""
        for subscriber in self.alert_subscribers.copy():
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    await subscriber(alert)
                else:
                    subscriber(alert)
            except Exception as e:
                logfire.error("Error notifying alert subscriber", error=str(e))
                self.alert_subscribers.discard(subscriber)
    
    def subscribe_to_metrics(self, callback: Callable[[RealTimeMetrics], None]) -> None:
        """Subscribe to real-time metric updates."""
        self.metric_subscribers.add(callback)
    
    def subscribe_to_alerts(self, callback: Callable[[MonitoringAlert], None]) -> None:
        """Subscribe to alert notifications."""
        self.alert_subscribers.add(callback)
    
    def unsubscribe_from_metrics(self, callback: Callable) -> None:
        """Unsubscribe from metric updates."""
        self.metric_subscribers.discard(callback)
    
    def unsubscribe_from_alerts(self, callback: Callable) -> None:
        """Unsubscribe from alert notifications."""
        self.alert_subscribers.discard(callback)
    
    def get_current_metrics(self) -> Optional[RealTimeMetrics]:
        """Get the most recent metrics."""
        return self.current_metrics
    
    def get_metrics_history(self, minutes: int = 60) -> List[RealTimeMetrics]:
        """Get metrics history for the specified time period."""
        cutoff_time = time.time() - (minutes * 60)
        return [m for m in self.metrics_history if m.timestamp >= cutoff_time]
    
    def get_active_alerts(self) -> List[MonitoringAlert]:
        """Get currently active alerts."""
        return list(self.alert_manager.active_alerts.values())
    
    def get_alert_history(self, hours: int = 24) -> List[MonitoringAlert]:
        """Get alert history for the specified time period."""
        cutoff_time = time.time() - (hours * 3600)
        return [a for a in self.alert_manager.alert_history if a.timestamp >= cutoff_time]

# Utility functions
def create_realtime_monitor(analytics_collector: AnalyticsCollector,
                          dashboard: MetricsDashboard,
                          performance_visualizer: PerformanceVisualizer,
                          config: MonitoringConfig = None) -> RealTimeMonitor:
    """Create and initialize real-time monitor."""
    monitor = RealTimeMonitor(analytics_collector, dashboard, performance_visualizer, config)
    logfire.info("Real-time monitor created and initialized")
    return monitor

if __name__ == "__main__":
    # Example usage and testing
    async def main():
        print("📊 Testing Real-time Monitor")
        
        # Mock dependencies for testing
        from unittest.mock import Mock
        
        mock_collector = Mock()
        mock_collector.events_queue = []
        
        # Add mock events
        for i in range(20):
            mock_event = Mock()
            mock_event.timestamp = time.time() - (i * 10)  # Events over last 200 seconds
            mock_event.duration_ms = 100 + (i % 5) * 50  # Varying response times
            mock_event.success = i % 10 != 0  # 90% success rate
            mock_event.session_id = f"session_{i % 3}"
            mock_event.data = {"cache_hit": i % 4 == 0}  # 25% cache hit rate
            mock_collector.events_queue.append(mock_event)
        
        mock_dashboard = Mock()
        mock_visualizer = Mock()
        
        # Create monitor with test configuration
        config = MonitoringConfig(
            update_interval_seconds=1.0,
            response_time_warning_ms=200.0,
            response_time_critical_ms=400.0,
            error_rate_warning_percent=5.0,
            error_rate_critical_percent=10.0
        )
        
        monitor = create_realtime_monitor(mock_collector, mock_dashboard, mock_visualizer, config)
        
        print(f"Monitor state: {monitor.state.value}")
        
        # Test metric collection
        metrics = await monitor._collect_current_metrics()
        print(f"Current metrics: avg_response_time={metrics.avg_response_time_ms:.1f}ms, "
              f"error_rate={metrics.error_rate_percent:.1f}%, "
              f"rps={metrics.requests_per_second:.1f}")
        
        # Test health checks
        health_results = await monitor.health_checker.run_health_checks()
        print(f"Health checks: {len(health_results)} components checked")
        
        for component, result in health_results.items():
            status = "✅" if result.healthy else "❌"
            print(f"  {status} {component}: {result.response_time_ms:.1f}ms")
        
        # Test alert system
        alert = monitor.alert_manager.check_threshold_alert(
            "test_metric", 300.0, 200.0, 400.0
        )
        
        if alert:
            print(f"Alert generated: {alert.severity.value} - {alert.message}")
        
        # Test monitoring start/stop
        print("\nTesting monitoring lifecycle...")
        
        start_success = await monitor.start_monitoring()
        print(f"Start monitoring: {'✅' if start_success else '❌'}")
        
        # Let it run briefly
        await asyncio.sleep(2)
        
        # Check current metrics
        current = monitor.get_current_metrics()
        if current:
            print(f"Real-time metrics collected: {current.timestamp}")
        
        # Stop monitoring
        stop_success = await monitor.stop_monitoring()
        print(f"Stop monitoring: {'✅' if stop_success else '❌'}")
        
        print(f"Final state: {monitor.state.value}")
        
        print("\n✅ Real-time monitor test completed")
    
    asyncio.run(main())