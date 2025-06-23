#!/usr/bin/env python3
"""
Performance Visualizer for Ptolemies
Advanced performance metrics visualization and trend analysis system.
"""

import asyncio
import time
import math
import json
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime, timezone, timedelta
from collections import defaultdict, deque
import statistics
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

# Configure Logfire
logfire.configure(send_to_logfire=False)

class PerformanceMetricType(Enum):
    """Types of performance metrics."""
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    RESOURCE_USAGE = "resource_usage"
    LATENCY_PERCENTILES = "latency_percentiles"
    CONCURRENCY = "concurrency"
    CACHE_HIT_RATE = "cache_hit_rate"
    QUERY_COMPLEXITY = "query_complexity"

class TrendDirection(Enum):
    """Trend analysis directions."""
    IMPROVING = "improving"
    DEGRADING = "degrading"
    STABLE = "stable"
    VOLATILE = "volatile"

class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

@dataclass
class PerformanceThreshold:
    """Performance threshold configuration."""
    metric_name: str
    warning_value: float
    critical_value: float
    emergency_value: Optional[float] = None
    comparison_operator: str = ">"  # >, <, >=, <=, ==
    duration_seconds: int = 300  # How long threshold must be exceeded
    enabled: bool = True

@dataclass
class PerformanceTrend:
    """Performance trend analysis result."""
    metric_name: str
    time_period: str
    direction: TrendDirection
    change_percentage: float
    confidence_score: float
    data_points: int
    start_value: float
    end_value: float
    slope: float
    r_squared: float

@dataclass
class PerformanceAlert:
    """Performance alert notification."""
    alert_id: str
    metric_name: str
    severity: AlertSeverity
    threshold_value: float
    current_value: float
    message: str
    timestamp: float = field(default_factory=time.time)
    duration_seconds: int = 0
    resolved: bool = False
    resolution_timestamp: Optional[float] = None

@dataclass
class PerformanceSnapshot:
    """Point-in-time performance snapshot."""
    timestamp: float
    response_time_ms: float
    throughput_qps: float
    error_rate_percent: float
    cpu_usage_percent: float
    memory_usage_mb: float
    active_sessions: int
    cache_hit_rate_percent: float
    query_complexity_avg: float

class PerformanceVisualizer:
    """Advanced performance visualization and analysis system."""
    
    def __init__(self, analytics_collector: AnalyticsCollector, 
                 dashboard: MetricsDashboard):
        self.analytics_collector = analytics_collector
        self.dashboard = dashboard
        
        # Performance data storage
        self.performance_history: deque = deque(maxlen=10000)
        self.active_alerts: Dict[str, PerformanceAlert] = {}
        self.resolved_alerts: List[PerformanceAlert] = []
        
        # Threshold configurations
        self.thresholds: Dict[str, PerformanceThreshold] = {}
        self._setup_default_thresholds()
        
        # Trend analysis cache
        self.trend_cache: Dict[str, PerformanceTrend] = {}
        self.trend_cache_ttl = 300  # 5 minutes
        
        # Performance baselines
        self.baselines: Dict[str, float] = {}
        
        # Anomaly detection
        self.anomaly_detection_enabled = True
        self.anomaly_threshold_multiplier = 3.0  # Standard deviations
        
    @logfire.instrument("create_performance_chart")
    async def create_performance_chart(self, metric_type: PerformanceMetricType,
                                     time_range: TimeRange = TimeRange.LAST_24_HOURS,
                                     chart_type: ChartType = ChartType.LINE,
                                     **kwargs) -> Dict[str, Any]:
        """Create performance visualization chart."""
        
        with logfire.span("Creating performance chart", metric_type=metric_type.value):
            try:
                # Get performance data
                data = await self._get_performance_data(metric_type, time_range)
                
                # Process data based on chart type
                if chart_type == ChartType.LINE:
                    chart_data = self._create_line_chart(data, metric_type, **kwargs)
                elif chart_type == ChartType.HISTOGRAM:
                    chart_data = self._create_histogram_chart(data, metric_type, **kwargs)
                elif chart_type == ChartType.HEATMAP:
                    chart_data = self._create_heatmap_chart(data, metric_type, **kwargs)
                elif chart_type == ChartType.GAUGE:
                    chart_data = self._create_gauge_chart(data, metric_type, **kwargs)
                else:
                    raise ValueError(f"Unsupported chart type for performance: {chart_type}")
                
                # Add performance annotations
                chart_data = self._add_performance_annotations(chart_data, metric_type, time_range)
                
                logfire.info("Performance chart created successfully",
                           metric_type=metric_type.value,
                           chart_type=chart_type.value,
                           data_points=len(data))
                
                return chart_data
                
            except Exception as e:
                logfire.error("Failed to create performance chart", error=str(e))
                raise
    
    @logfire.instrument("analyze_performance_trends")
    async def analyze_performance_trends(self, 
                                       time_periods: List[str] = None) -> Dict[str, PerformanceTrend]:
        """Analyze performance trends across different time periods."""
        
        if time_periods is None:
            time_periods = ["1h", "6h", "24h", "7d"]
        
        trends = {}
        
        for period in time_periods:
            for metric_type in PerformanceMetricType:
                cache_key = f"{metric_type.value}_{period}"
                
                # Check cache first
                if (cache_key in self.trend_cache and 
                    time.time() - self.trend_cache[cache_key].timestamp < self.trend_cache_ttl):
                    trends[cache_key] = self.trend_cache[cache_key]
                    continue
                
                try:
                    # Get data for trend analysis
                    time_range = self._period_to_time_range(period)
                    data = await self._get_performance_data(metric_type, time_range)
                    
                    if len(data) < 2:
                        continue
                    
                    # Perform trend analysis
                    trend = self._calculate_trend(data, metric_type.value, period)
                    trends[cache_key] = trend
                    self.trend_cache[cache_key] = trend
                    
                except Exception as e:
                    logfire.error("Failed to analyze trend", 
                                metric=metric_type.value, 
                                period=period, 
                                error=str(e))
        
        return trends
    
    @logfire.instrument("detect_performance_anomalies")
    async def detect_performance_anomalies(self, 
                                         time_range: TimeRange = TimeRange.LAST_24_HOURS) -> List[Dict[str, Any]]:
        """Detect performance anomalies using statistical methods."""
        
        if not self.anomaly_detection_enabled:
            return []
        
        anomalies = []
        
        for metric_type in PerformanceMetricType:
            try:
                data = await self._get_performance_data(metric_type, time_range)
                
                if len(data) < 10:  # Need minimum data points
                    continue
                
                # Extract values for statistical analysis
                values = [point.get("value", 0) for point in data]
                
                # Calculate statistical parameters
                mean = statistics.mean(values)
                std_dev = statistics.stdev(values) if len(values) > 1 else 0
                
                if std_dev == 0:
                    continue
                
                # Detect anomalies (values beyond threshold * standard deviations)
                threshold = self.anomaly_threshold_multiplier * std_dev
                
                for i, point in enumerate(data):
                    value = point.get("value", 0)
                    deviation = abs(value - mean)
                    
                    if deviation > threshold:
                        anomaly = {
                            "metric_type": metric_type.value,
                            "timestamp": point.get("timestamp", time.time()),
                            "value": value,
                            "expected_value": mean,
                            "deviation": deviation,
                            "severity": self._calculate_anomaly_severity(deviation, threshold),
                            "z_score": deviation / std_dev if std_dev > 0 else 0
                        }
                        anomalies.append(anomaly)
                
            except Exception as e:
                logfire.error("Failed to detect anomalies", 
                            metric=metric_type.value, 
                            error=str(e))
        
        # Sort anomalies by severity and timestamp
        anomalies.sort(key=lambda x: (x["severity"], -x["timestamp"]))
        
        return anomalies
    
    @logfire.instrument("create_performance_dashboard")
    async def create_performance_dashboard(self) -> str:
        """Create comprehensive performance dashboard."""
        
        dashboard_config = {
            "dashboard_id": "performance_analysis",
            "title": "Performance Analysis & Monitoring",
            "description": "Comprehensive performance metrics, trends, and anomaly detection",
            "charts": []
        }
        
        # Response Time Trend
        dashboard_config["charts"].append({
            "chart_id": "response_time_trend",
            "title": "Response Time Trend",
            "chart_type": ChartType.LINE.value,
            "data_source": "performance",
            "metric_type": PerformanceMetricType.RESPONSE_TIME.value,
            "position": (0, 0),
            "width": 6,
            "height": 4
        })
        
        # Throughput Analysis
        dashboard_config["charts"].append({
            "chart_id": "throughput_analysis",
            "title": "Throughput (Queries/sec)",
            "chart_type": ChartType.LINE.value,
            "data_source": "performance", 
            "metric_type": PerformanceMetricType.THROUGHPUT.value,
            "position": (0, 6),
            "width": 6,
            "height": 4
        })
        
        # Error Rate Gauge
        dashboard_config["charts"].append({
            "chart_id": "error_rate_gauge",
            "title": "Error Rate",
            "chart_type": ChartType.GAUGE.value,
            "data_source": "performance",
            "metric_type": PerformanceMetricType.ERROR_RATE.value,
            "warning_threshold": 2.0,
            "critical_threshold": 5.0,
            "position": (1, 0),
            "width": 3,
            "height": 3
        })
        
        # Resource Usage Gauge  
        dashboard_config["charts"].append({
            "chart_id": "resource_usage_gauge",
            "title": "Resource Usage",
            "chart_type": ChartType.GAUGE.value,
            "data_source": "performance",
            "metric_type": PerformanceMetricType.RESOURCE_USAGE.value,
            "warning_threshold": 70.0,
            "critical_threshold": 90.0,
            "position": (1, 3),
            "width": 3,
            "height": 3
        })
        
        # Latency Distribution
        dashboard_config["charts"].append({
            "chart_id": "latency_distribution",
            "title": "Response Time Distribution",
            "chart_type": ChartType.HISTOGRAM.value,
            "data_source": "performance",
            "metric_type": PerformanceMetricType.RESPONSE_TIME.value,
            "position": (1, 6),
            "width": 6,
            "height": 4
        })
        
        # Performance Heatmap
        dashboard_config["charts"].append({
            "chart_id": "performance_heatmap",
            "title": "Performance Heatmap (24h)",
            "chart_type": ChartType.HEATMAP.value,
            "data_source": "performance",
            "metric_type": PerformanceMetricType.RESPONSE_TIME.value,
            "position": (2, 0),
            "width": 12,
            "height": 4
        })
        
        # Create dashboard
        from metrics_dashboard import DashboardConfig
        config = DashboardConfig(**dashboard_config)
        success = self.dashboard.create_dashboard(config)
        
        if success:
            logfire.info("Performance dashboard created successfully")
            return dashboard_config["dashboard_id"]
        else:
            raise Exception("Failed to create performance dashboard")
    
    async def _get_performance_data(self, metric_type: PerformanceMetricType, 
                                  time_range: TimeRange) -> List[Dict[str, Any]]:
        """Get performance data for specified metric and time range."""
        
        # Calculate time boundaries
        end_time = time.time()
        if time_range == TimeRange.LAST_HOUR:
            start_time = end_time - 3600
        elif time_range == TimeRange.LAST_6_HOURS:
            start_time = end_time - (6 * 3600)
        elif time_range == TimeRange.LAST_24_HOURS:
            start_time = end_time - (24 * 3600)
        elif time_range == TimeRange.LAST_7_DAYS:
            start_time = end_time - (7 * 24 * 3600)
        elif time_range == TimeRange.LAST_30_DAYS:
            start_time = end_time - (30 * 24 * 3600)
        else:
            start_time = end_time - (24 * 3600)
        
        # Get events from analytics collector
        all_events = list(self.analytics_collector.events_queue)
        
        # Filter events by time range
        filtered_events = [
            e for e in all_events 
            if start_time <= e.timestamp <= end_time
        ]
        
        # Process events based on metric type
        return self._process_events_for_metric(filtered_events, metric_type)
    
    def _process_events_for_metric(self, events: List[Any], 
                                 metric_type: PerformanceMetricType) -> List[Dict[str, Any]]:
        """Process events to extract specific performance metric data."""
        
        data_points = []
        
        for event in events:
            point = {"timestamp": event.timestamp}
            
            if metric_type == PerformanceMetricType.RESPONSE_TIME:
                if hasattr(event, 'duration_ms') and event.duration_ms is not None:
                    point["value"] = event.duration_ms
                    point["metric"] = "response_time_ms"
                    data_points.append(point)
                    
            elif metric_type == PerformanceMetricType.ERROR_RATE:
                if hasattr(event, 'success'):
                    point["value"] = 0 if event.success else 1
                    point["metric"] = "error_rate"
                    data_points.append(point)
                    
            elif metric_type == PerformanceMetricType.THROUGHPUT:
                # For throughput, we count events per time unit
                point["value"] = 1
                point["metric"] = "throughput"
                data_points.append(point)
                
            elif metric_type == PerformanceMetricType.RESOURCE_USAGE:
                if hasattr(event, 'cpu_usage_percent'):
                    point["value"] = event.cpu_usage_percent
                    point["metric"] = "cpu_usage"
                    data_points.append(point)
                elif hasattr(event, 'memory_usage_mb'):
                    point["value"] = event.memory_usage_mb
                    point["metric"] = "memory_usage"
                    data_points.append(point)
                    
            elif metric_type == PerformanceMetricType.CACHE_HIT_RATE:
                if hasattr(event, 'data') and isinstance(event.data, dict):
                    if 'cache_hit' in event.data:
                        point["value"] = 1 if event.data['cache_hit'] else 0
                        point["metric"] = "cache_hit_rate"
                        data_points.append(point)
        
        return data_points
    
    def _create_line_chart(self, data: List[Dict[str, Any]], 
                          metric_type: PerformanceMetricType, **kwargs) -> Dict[str, Any]:
        """Create line chart for time series performance data."""
        
        if not data:
            return {"labels": [], "datasets": []}
        
        # Group data by time intervals
        interval_seconds = self._get_time_interval(len(data))
        time_buckets = defaultdict(list)
        
        for point in data:
            bucket_time = math.floor(point["timestamp"] / interval_seconds) * interval_seconds
            time_buckets[bucket_time].append(point["value"])
        
        # Sort by time and calculate averages
        sorted_times = sorted(time_buckets.keys())
        labels = [datetime.fromtimestamp(t, timezone.utc).strftime("%H:%M") for t in sorted_times]
        
        # Calculate aggregated values (average for most metrics)
        if metric_type == PerformanceMetricType.THROUGHPUT:
            # For throughput, sum the events in each bucket and convert to rate
            data_points = [len(time_buckets[t]) / (interval_seconds / 60) for t in sorted_times]
            y_label = "Queries/minute"
        elif metric_type == PerformanceMetricType.ERROR_RATE:
            # For error rate, calculate percentage
            data_points = []
            for t in sorted_times:
                bucket_values = time_buckets[t]
                error_rate = (sum(bucket_values) / len(bucket_values)) * 100 if bucket_values else 0
                data_points.append(error_rate)
            y_label = "Error Rate (%)"
        else:
            # For other metrics, use average
            data_points = [statistics.mean(time_buckets[t]) for t in sorted_times]
            y_label = metric_type.value.replace("_", " ").title()
        
        # Determine color based on metric type
        colors = {
            PerformanceMetricType.RESPONSE_TIME: ("rgb(255, 99, 132)", "rgba(255, 99, 132, 0.2)"),
            PerformanceMetricType.THROUGHPUT: ("rgb(54, 162, 235)", "rgba(54, 162, 235, 0.2)"),
            PerformanceMetricType.ERROR_RATE: ("rgb(255, 205, 86)", "rgba(255, 205, 86, 0.2)"),
            PerformanceMetricType.RESOURCE_USAGE: ("rgb(75, 192, 192)", "rgba(75, 192, 192, 0.2)")
        }
        
        border_color, bg_color = colors.get(metric_type, ("rgb(153, 102, 255)", "rgba(153, 102, 255, 0.2)"))
        
        return {
            "labels": labels,
            "datasets": [{
                "label": y_label,
                "data": data_points,
                "borderColor": border_color,
                "backgroundColor": bg_color,
                "tension": 0.4,
                "pointRadius": 3,
                "pointHoverRadius": 5
            }],
            "options": {
                "scales": {
                    "y": {
                        "beginAtZero": True,
                        "title": {"display": True, "text": y_label}
                    }
                }
            }
        }
    
    def _create_histogram_chart(self, data: List[Dict[str, Any]], 
                              metric_type: PerformanceMetricType, **kwargs) -> Dict[str, Any]:
        """Create histogram chart for performance distribution analysis."""
        
        if not data:
            return {"labels": [], "datasets": []}
        
        values = [point["value"] for point in data]
        
        # Calculate histogram bins
        min_val = min(values)
        max_val = max(values)
        bin_count = min(50, max(10, len(values) // 20))
        
        bin_width = (max_val - min_val) / bin_count if max_val > min_val else 1
        bins = [0] * bin_count
        labels = []
        
        for i in range(bin_count):
            bin_start = min_val + i * bin_width
            bin_end = bin_start + bin_width
            labels.append(f"{bin_start:.1f}-{bin_end:.1f}")
            
            # Count values in this bin
            for value in values:
                if bin_start <= value < bin_end or (i == bin_count - 1 and value == bin_end):
                    bins[i] += 1
        
        return {
            "labels": labels,
            "datasets": [{
                "label": "Frequency",
                "data": bins,
                "backgroundColor": "rgba(54, 162, 235, 0.7)",
                "borderColor": "rgba(54, 162, 235, 1)",
                "borderWidth": 1
            }],
            "statistics": {
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
                "min": min_val,
                "max": max_val,
                "count": len(values)
            }
        }
    
    def _create_heatmap_chart(self, data: List[Dict[str, Any]], 
                            metric_type: PerformanceMetricType, **kwargs) -> Dict[str, Any]:
        """Create heatmap for performance patterns over time."""
        
        if not data:
            return {"data": [], "hours": [], "days": []}
        
        # Group data by hour and day
        hourly_data = defaultdict(lambda: defaultdict(list))
        
        for point in data:
            dt = datetime.fromtimestamp(point["timestamp"], timezone.utc)
            day_key = dt.strftime("%Y-%m-%d")
            hour_key = dt.hour
            hourly_data[day_key][hour_key].append(point["value"])
        
        # Create heatmap matrix
        days = sorted(hourly_data.keys())[-7:]  # Last 7 days
        hours = list(range(24))
        heatmap_data = []
        
        for day in days:
            day_data = []
            for hour in hours:
                if hour in hourly_data[day] and hourly_data[day][hour]:
                    avg_value = statistics.mean(hourly_data[day][hour])
                else:
                    avg_value = 0
                day_data.append(avg_value)
            heatmap_data.append(day_data)
        
        return {
            "data": heatmap_data,
            "days": days,
            "hours": hours,
            "metric_type": metric_type.value
        }
    
    def _create_gauge_chart(self, data: List[Dict[str, Any]], 
                          metric_type: PerformanceMetricType, **kwargs) -> Dict[str, Any]:
        """Create gauge chart for current performance status."""
        
        if not data:
            return {"value": 0, "max": 100}
        
        # Get recent values (last 5 minutes)
        current_time = time.time()
        recent_data = [p for p in data if current_time - p["timestamp"] <= 300]
        
        if not recent_data:
            recent_data = data[-10:]  # Use last 10 points if no recent data
        
        # Calculate current value
        values = [point["value"] for point in recent_data]
        current_value = statistics.mean(values)
        
        # Determine max value and thresholds based on metric type
        if metric_type == PerformanceMetricType.ERROR_RATE:
            max_value = 100
            warning_threshold = kwargs.get("warning_threshold", 2.0)
            critical_threshold = kwargs.get("critical_threshold", 5.0)
        elif metric_type == PerformanceMetricType.RESOURCE_USAGE:
            max_value = 100
            warning_threshold = kwargs.get("warning_threshold", 70.0)
            critical_threshold = kwargs.get("critical_threshold", 90.0)
        elif metric_type == PerformanceMetricType.RESPONSE_TIME:
            max_value = max(1000, current_value * 1.5)
            warning_threshold = kwargs.get("warning_threshold", 500.0)
            critical_threshold = kwargs.get("critical_threshold", 1000.0)
        else:
            max_value = max(100, current_value * 1.2)
            warning_threshold = kwargs.get("warning_threshold", max_value * 0.7)
            critical_threshold = kwargs.get("critical_threshold", max_value * 0.9)
        
        return {
            "value": round(current_value, 2),
            "max": max_value,
            "warning_threshold": warning_threshold,
            "critical_threshold": critical_threshold,
            "unit": self._get_metric_unit(metric_type),
            "status": self._get_metric_status(current_value, warning_threshold, critical_threshold)
        }
    
    def _add_performance_annotations(self, chart_data: Dict[str, Any], 
                                   metric_type: PerformanceMetricType,
                                   time_range: TimeRange) -> Dict[str, Any]:
        """Add performance annotations and insights to chart data."""
        
        annotations = []
        
        # Add threshold lines for applicable metrics
        if metric_type in [PerformanceMetricType.ERROR_RATE, PerformanceMetricType.RESPONSE_TIME]:
            if metric_type.value in self.thresholds:
                threshold = self.thresholds[metric_type.value]
                annotations.append({
                    "type": "line",
                    "mode": "horizontal",
                    "scaleID": "y",
                    "value": threshold.warning_value,
                    "borderColor": "orange",
                    "borderWidth": 2,
                    "label": {
                        "content": f"Warning: {threshold.warning_value}",
                        "enabled": True
                    }
                })
                annotations.append({
                    "type": "line", 
                    "mode": "horizontal",
                    "scaleID": "y",
                    "value": threshold.critical_value,
                    "borderColor": "red",
                    "borderWidth": 2,
                    "label": {
                        "content": f"Critical: {threshold.critical_value}",
                        "enabled": True
                    }
                })
        
        # Add baseline if available
        if metric_type.value in self.baselines:
            baseline = self.baselines[metric_type.value]
            annotations.append({
                "type": "line",
                "mode": "horizontal",
                "scaleID": "y",
                "value": baseline,
                "borderColor": "green",
                "borderWidth": 1,
                "borderDash": [5, 5],
                "label": {
                    "content": f"Baseline: {baseline:.1f}",
                    "enabled": True
                }
            })
        
        chart_data["annotations"] = annotations
        return chart_data
    
    def _calculate_trend(self, data: List[Dict[str, Any]], 
                        metric_name: str, time_period: str) -> PerformanceTrend:
        """Calculate performance trend using linear regression."""
        
        if len(data) < 2:
            return PerformanceTrend(
                metric_name=metric_name,
                time_period=time_period,
                direction=TrendDirection.STABLE,
                change_percentage=0.0,
                confidence_score=0.0,
                data_points=len(data),
                start_value=0.0,
                end_value=0.0,
                slope=0.0,
                r_squared=0.0
            )
        
        # Extract x (time) and y (values) for regression
        x_values = [point["timestamp"] for point in data]
        y_values = [point["value"] for point in data]
        
        # Normalize time values
        min_time = min(x_values)
        x_normalized = [x - min_time for x in x_values]
        
        # Calculate linear regression
        n = len(data)
        sum_x = sum(x_normalized)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_normalized, y_values))
        sum_x2 = sum(x * x for x in x_normalized)
        sum_y2 = sum(y * y for y in y_values)
        
        # Calculate slope and intercept
        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            slope = 0
            intercept = statistics.mean(y_values)
        else:
            slope = (n * sum_xy - sum_x * sum_y) / denominator
            intercept = (sum_y - slope * sum_x) / n
        
        # Calculate R-squared
        if len(set(y_values)) == 1:  # All values are the same
            r_squared = 1.0
        else:
            y_mean = statistics.mean(y_values)
            ss_tot = sum((y - y_mean) ** 2 for y in y_values)
            ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(x_normalized, y_values))
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        # Determine trend direction
        start_value = y_values[0]
        end_value = y_values[-1]
        change_percentage = ((end_value - start_value) / start_value * 100) if start_value != 0 else 0
        
        if abs(change_percentage) < 5:  # Less than 5% change
            direction = TrendDirection.STABLE
        elif abs(slope) > statistics.stdev(y_values) if len(y_values) > 1 else 0:
            direction = TrendDirection.VOLATILE
        elif change_percentage > 0:
            direction = TrendDirection.IMPROVING if metric_name in ["throughput", "cache_hit_rate"] else TrendDirection.DEGRADING
        else:
            direction = TrendDirection.DEGRADING if metric_name in ["throughput", "cache_hit_rate"] else TrendDirection.IMPROVING
        
        return PerformanceTrend(
            metric_name=metric_name,
            time_period=time_period,
            direction=direction,
            change_percentage=change_percentage,
            confidence_score=r_squared,
            data_points=n,
            start_value=start_value,
            end_value=end_value,
            slope=slope,
            r_squared=r_squared
        )
    
    def _calculate_anomaly_severity(self, deviation: float, threshold: float) -> str:
        """Calculate anomaly severity based on deviation."""
        
        if deviation >= threshold * 3:
            return "critical"
        elif deviation >= threshold * 2:
            return "warning"
        else:
            return "info"
    
    def _period_to_time_range(self, period: str) -> TimeRange:
        """Convert period string to TimeRange enum."""
        
        period_map = {
            "1h": TimeRange.LAST_HOUR,
            "6h": TimeRange.LAST_6_HOURS,
            "24h": TimeRange.LAST_24_HOURS,
            "7d": TimeRange.LAST_7_DAYS,
            "30d": TimeRange.LAST_30_DAYS
        }
        
        return period_map.get(period, TimeRange.LAST_24_HOURS)
    
    def _get_time_interval(self, data_count: int) -> int:
        """Get appropriate time interval for data aggregation."""
        
        if data_count <= 50:
            return 300   # 5 minutes
        elif data_count <= 200:
            return 900   # 15 minutes
        elif data_count <= 500:
            return 1800  # 30 minutes
        else:
            return 3600  # 1 hour
    
    def _get_metric_unit(self, metric_type: PerformanceMetricType) -> str:
        """Get unit string for metric type."""
        
        unit_map = {
            PerformanceMetricType.RESPONSE_TIME: "ms",
            PerformanceMetricType.THROUGHPUT: "qps",
            PerformanceMetricType.ERROR_RATE: "%",
            PerformanceMetricType.RESOURCE_USAGE: "%",
            PerformanceMetricType.CACHE_HIT_RATE: "%"
        }
        
        return unit_map.get(metric_type, "")
    
    def _get_metric_status(self, value: float, warning: float, critical: float) -> str:
        """Get status string based on thresholds."""
        
        if value >= critical:
            return "critical"
        elif value >= warning:
            return "warning"
        else:
            return "good"
    
    def _setup_default_thresholds(self):
        """Setup default performance thresholds."""
        
        self.thresholds.update({
            "response_time": PerformanceThreshold(
                metric_name="response_time",
                warning_value=500.0,
                critical_value=1000.0,
                emergency_value=2000.0
            ),
            "error_rate": PerformanceThreshold(
                metric_name="error_rate",
                warning_value=2.0,
                critical_value=5.0,
                emergency_value=10.0
            ),
            "resource_usage": PerformanceThreshold(
                metric_name="resource_usage",
                warning_value=70.0,
                critical_value=90.0,
                emergency_value=95.0
            )
        })

# Utility functions
def create_performance_visualizer(analytics_collector: AnalyticsCollector,
                                dashboard: MetricsDashboard) -> PerformanceVisualizer:
    """Create and initialize performance visualizer."""
    visualizer = PerformanceVisualizer(analytics_collector, dashboard)
    logfire.info("Performance visualizer created and initialized")
    return visualizer

if __name__ == "__main__":
    # Example usage and testing
    async def main():
        print("📈 Testing Performance Visualizer")
        
        # Mock dependencies for testing
        from unittest.mock import Mock
        
        mock_collector = Mock()
        mock_collector.events_queue = []
        
        # Add mock performance events
        for i in range(100):
            mock_event = Mock()
            mock_event.timestamp = time.time() - (i * 60)  # Events over last 100 minutes
            mock_event.duration_ms = 100 + (i % 10) * 50 + (i // 20) * 100  # Varying response times
            mock_event.success = i % 10 != 0  # 90% success rate
            mock_event.cpu_usage_percent = 50 + (i % 30)  # CPU usage 50-80%
            mock_event.memory_usage_mb = 512 + (i % 100)  # Memory usage varies
            mock_event.data = {"cache_hit": i % 3 == 0}  # 33% cache hit rate
            mock_collector.events_queue.append(mock_event)
        
        mock_dashboard = Mock()
        mock_dashboard.create_dashboard = Mock(return_value=True)
        
        # Create visualizer
        visualizer = create_performance_visualizer(mock_collector, mock_dashboard)
        
        # Test chart creation
        response_time_chart = await visualizer.create_performance_chart(
            PerformanceMetricType.RESPONSE_TIME,
            TimeRange.LAST_24_HOURS,
            ChartType.LINE
        )
        
        print(f"Response time chart created with {len(response_time_chart['datasets'])} datasets")
        
        # Test trend analysis
        trends = await visualizer.analyze_performance_trends(["1h", "24h"])
        print(f"Analyzed {len(trends)} performance trends")
        
        for trend_key, trend in trends.items():
            if hasattr(trend, 'direction'):
                print(f"- {trend_key}: {trend.direction.value} ({trend.change_percentage:.1f}%)")
        
        # Test anomaly detection
        anomalies = await visualizer.detect_performance_anomalies()
        print(f"Detected {len(anomalies)} performance anomalies")
        
        for anomaly in anomalies[:3]:  # Show first 3
            print(f"- {anomaly['metric_type']}: {anomaly['severity']} (z-score: {anomaly['z_score']:.2f})")
        
        # Test dashboard creation
        dashboard_id = await visualizer.create_performance_dashboard()
        print(f"Created performance dashboard: {dashboard_id}")
        
        print("\n✅ Performance visualizer test completed")
    
    asyncio.run(main())