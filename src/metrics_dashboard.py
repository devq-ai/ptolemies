#!/usr/bin/env python3
"""
Metrics Dashboard for Ptolemies
Comprehensive dashboard system for visualizing analytics data and KPIs.
"""

import asyncio
import time
import json
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime, timezone, timedelta
from collections import defaultdict, deque
import math
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

# Configure Logfire
logfire.configure(send_to_logfire=False)

class ChartType(Enum):
    """Types of charts supported by the dashboard."""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    GAUGE = "gauge"
    HEATMAP = "heatmap"
    SCATTER = "scatter"
    AREA = "area"
    HISTOGRAM = "histogram"
    TABLE = "table"

class TimeRange(Enum):
    """Time ranges for dashboard data."""
    LAST_HOUR = "1h"
    LAST_6_HOURS = "6h"
    LAST_24_HOURS = "24h"
    LAST_7_DAYS = "7d"
    LAST_30_DAYS = "30d"
    CUSTOM = "custom"

class RefreshInterval(Enum):
    """Dashboard refresh intervals."""
    REAL_TIME = 5  # 5 seconds
    FAST = 30      # 30 seconds
    NORMAL = 60    # 1 minute
    SLOW = 300     # 5 minutes
    MANUAL = 0     # Manual refresh only

@dataclass
class ChartConfig:
    """Configuration for a dashboard chart."""
    chart_id: str
    title: str
    chart_type: ChartType
    data_source: str
    time_range: TimeRange = TimeRange.LAST_24_HOURS
    refresh_interval: RefreshInterval = RefreshInterval.NORMAL
    
    # Chart-specific settings
    x_axis_label: str = ""
    y_axis_label: str = ""
    color_scheme: str = "default"
    show_legend: bool = True
    show_grid: bool = True
    
    # Filtering and aggregation
    filters: Dict[str, Any] = field(default_factory=dict)
    group_by: Optional[str] = None
    aggregation: str = "count"  # count, sum, avg, min, max
    
    # Thresholds and alerts
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None
    
    # Display options
    width: int = 6  # Grid width (1-12)
    height: int = 4  # Grid height
    position: Tuple[int, int] = (0, 0)  # (row, col)

@dataclass
class DashboardConfig:
    """Configuration for a complete dashboard."""
    dashboard_id: str
    title: str
    description: str = ""
    
    # Layout settings
    grid_columns: int = 12
    auto_refresh: bool = True
    default_time_range: TimeRange = TimeRange.LAST_24_HOURS
    
    # Charts configuration
    charts: List[ChartConfig] = field(default_factory=list)
    
    # Access control
    public: bool = False
    allowed_users: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)

@dataclass
class ChartData:
    """Data container for chart rendering."""
    chart_id: str
    title: str
    chart_type: ChartType
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    
    # Chart metadata
    total_points: int = 0
    time_range: str = ""
    last_updated: str = ""
    
    # Status information
    status: str = "success"  # success, error, loading, no_data
    error_message: Optional[str] = None

class MetricsDashboard:
    """Main dashboard system for metrics visualization."""
    
    def __init__(self, analytics_collector: AnalyticsCollector):
        self.analytics_collector = analytics_collector
        
        # Dashboard storage
        self.dashboards: Dict[str, DashboardConfig] = {}
        self.chart_cache: Dict[str, ChartData] = {}
        
        # Chart data processors
        self.data_processors = {
            ChartType.LINE: self._process_line_chart_data,
            ChartType.BAR: self._process_bar_chart_data,
            ChartType.PIE: self._process_pie_chart_data,
            ChartType.GAUGE: self._process_gauge_chart_data,
            ChartType.HEATMAP: self._process_heatmap_chart_data,
            ChartType.HISTOGRAM: self._process_histogram_chart_data,
            ChartType.TABLE: self._process_table_chart_data
        }
        
        # Predefined dashboard templates
        self._register_default_dashboards()
    
    @logfire.instrument("create_dashboard")
    def create_dashboard(self, dashboard_config: DashboardConfig) -> bool:
        """Create a new dashboard."""
        try:
            with logfire.span("Creating dashboard", dashboard_id=dashboard_config.dashboard_id):
                # Validate configuration
                if not self._validate_dashboard_config(dashboard_config):
                    logfire.error("Invalid dashboard configuration")
                    return False
                
                # Store dashboard
                self.dashboards[dashboard_config.dashboard_id] = dashboard_config
                
                logfire.info("Dashboard created successfully", 
                           dashboard_id=dashboard_config.dashboard_id,
                           charts_count=len(dashboard_config.charts))
                
                return True
                
        except Exception as e:
            logfire.error("Failed to create dashboard", error=str(e))
            return False
    
    @logfire.instrument("get_dashboard_data")
    async def get_dashboard_data(self, dashboard_id: str, 
                               time_range: TimeRange = None,
                               force_refresh: bool = False) -> Dict[str, Any]:
        """Get complete dashboard data for rendering."""
        
        if dashboard_id not in self.dashboards:
            return {"error": "Dashboard not found"}
        
        dashboard = self.dashboards[dashboard_id]
        time_range = time_range or dashboard.default_time_range
        
        with logfire.span("Getting dashboard data", dashboard_id=dashboard_id):
            try:
                dashboard_data = {
                    "dashboard_id": dashboard_id,
                    "title": dashboard.title,
                    "description": dashboard.description,
                    "time_range": time_range.value,
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "charts": [],
                    "status": "success"
                }
                
                # Get data for each chart
                chart_tasks = []
                for chart_config in dashboard.charts:
                    chart_tasks.append(
                        self._get_chart_data(chart_config, time_range, force_refresh)
                    )
                
                # Execute chart data retrieval in parallel
                chart_results = await asyncio.gather(*chart_tasks, return_exceptions=True)
                
                # Process results
                for i, result in enumerate(chart_results):
                    if isinstance(result, Exception):
                        logfire.error("Chart data retrieval failed", 
                                    chart_id=dashboard.charts[i].chart_id,
                                    error=str(result))
                        # Add error chart data
                        dashboard_data["charts"].append({
                            "chart_id": dashboard.charts[i].chart_id,
                            "status": "error",
                            "error_message": str(result)
                        })
                    else:
                        dashboard_data["charts"].append(result)
                
                logfire.info("Dashboard data retrieved successfully",
                           dashboard_id=dashboard_id,
                           charts_count=len(dashboard_data["charts"]))
                
                return dashboard_data
                
            except Exception as e:
                logfire.error("Failed to get dashboard data", error=str(e))
                return {
                    "dashboard_id": dashboard_id,
                    "status": "error",
                    "error_message": str(e)
                }
    
    async def _get_chart_data(self, chart_config: ChartConfig, 
                            time_range: TimeRange, 
                            force_refresh: bool = False) -> Dict[str, Any]:
        """Get data for a specific chart."""
        
        # Check cache first
        cache_key = f"{chart_config.chart_id}_{time_range.value}"
        if not force_refresh and cache_key in self.chart_cache:
            cached_data = self.chart_cache[cache_key]
            # Check if cache is still valid (based on refresh interval)
            cache_age = time.time() - cached_data.timestamp
            if cache_age < chart_config.refresh_interval.value:
                return asdict(cached_data)
        
        try:
            # Get raw data from analytics collector
            raw_data = await self._fetch_raw_data(chart_config, time_range)
            
            # Process data based on chart type
            processor = self.data_processors.get(chart_config.chart_type)
            if not processor:
                raise ValueError(f"Unsupported chart type: {chart_config.chart_type}")
            
            processed_data = processor(raw_data, chart_config)
            
            # Create chart data object
            chart_data = ChartData(
                chart_id=chart_config.chart_id,
                title=chart_config.title,
                chart_type=chart_config.chart_type,
                data=processed_data,
                total_points=len(raw_data) if isinstance(raw_data, list) else 0,
                time_range=time_range.value,
                last_updated=datetime.now(timezone.utc).isoformat()
            )
            
            # Cache the result
            self.chart_cache[cache_key] = chart_data
            
            return asdict(chart_data)
            
        except Exception as e:
            logfire.error("Failed to get chart data", 
                        chart_id=chart_config.chart_id, 
                        error=str(e))
            return {
                "chart_id": chart_config.chart_id,
                "title": chart_config.title,
                "status": "error",
                "error_message": str(e)
            }
    
    async def _fetch_raw_data(self, chart_config: ChartConfig, 
                            time_range: TimeRange) -> List[Dict[str, Any]]:
        """Fetch raw data from analytics collector."""
        
        # Calculate time range
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
            start_time = end_time - (24 * 3600)  # Default to 24 hours
        
        # Get events from analytics collector
        all_events = list(self.analytics_collector.events_queue)
        
        # Filter by time range
        filtered_events = [
            e for e in all_events 
            if start_time <= e.timestamp <= end_time
        ]
        
        # Apply additional filters from chart config
        if chart_config.filters:
            filtered_events = self._apply_filters(filtered_events, chart_config.filters)
        
        # Convert events to dictionary format for processing
        event_dicts = []
        for event in filtered_events:
            event_dict = event.to_dict() if hasattr(event, 'to_dict') else {
                'event_type': event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type),
                'timestamp': event.timestamp,
                'session_id': event.session_id,
                'user_id': event.user_id,
                'duration_ms': event.duration_ms,
                'success': event.success,
                'intent': getattr(event, 'intent', None),
                'query': getattr(event, 'query', None),
                'source_component': getattr(event, 'source_component', None),
                'data': getattr(event, 'data', {})
            }
            event_dicts.append(event_dict)
        
        return event_dicts
    
    def _apply_filters(self, events: List[Dict[str, Any]], 
                      filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply filters to event data."""
        filtered_events = events
        
        for filter_key, filter_value in filters.items():
            if filter_key == "event_type":
                filtered_events = [e for e in filtered_events if e.get("event_type") == filter_value]
            elif filter_key == "intent":
                filtered_events = [e for e in filtered_events if e.get("intent") == filter_value]
            elif filter_key == "success":
                filtered_events = [e for e in filtered_events if e.get("success") == filter_value]
            elif filter_key == "source_component":
                filtered_events = [e for e in filtered_events if e.get("source_component") == filter_value]
        
        return filtered_events
    
    # Chart data processors
    def _process_line_chart_data(self, events: List[Dict[str, Any]], 
                               chart_config: ChartConfig) -> Dict[str, Any]:
        """Process data for line charts (time series)."""
        
        if not events:
            return {"datasets": [], "labels": []}
        
        # Group events by time intervals
        interval_seconds = self._get_time_interval(len(events))
        time_buckets = defaultdict(int)
        
        for event in events:
            bucket_time = math.floor(event["timestamp"] / interval_seconds) * interval_seconds
            time_buckets[bucket_time] += 1
        
        # Sort by time
        sorted_times = sorted(time_buckets.keys())
        
        # Create labels and data
        labels = [datetime.fromtimestamp(t, timezone.utc).strftime("%H:%M") for t in sorted_times]
        data_points = [time_buckets[t] for t in sorted_times]
        
        return {
            "labels": labels,
            "datasets": [{
                "label": chart_config.title,
                "data": data_points,
                "borderColor": "rgb(75, 192, 192)",
                "backgroundColor": "rgba(75, 192, 192, 0.2)",
                "tension": 0.1
            }]
        }
    
    def _process_bar_chart_data(self, events: List[Dict[str, Any]], 
                              chart_config: ChartConfig) -> Dict[str, Any]:
        """Process data for bar charts."""
        
        if not events:
            return {"labels": [], "datasets": []}
        
        # Group by the specified field
        group_field = chart_config.group_by or "event_type"
        grouped_data = defaultdict(int)
        
        for event in events:
            group_value = event.get(group_field, "unknown")
            grouped_data[group_value] += 1
        
        # Sort by count (descending)
        sorted_groups = sorted(grouped_data.items(), key=lambda x: x[1], reverse=True)
        
        labels = [item[0] for item in sorted_groups[:10]]  # Top 10
        data_points = [item[1] for item in sorted_groups[:10]]
        
        return {
            "labels": labels,
            "datasets": [{
                "label": chart_config.title,
                "data": data_points,
                "backgroundColor": [
                    "rgba(255, 99, 132, 0.8)",
                    "rgba(54, 162, 235, 0.8)",
                    "rgba(255, 205, 86, 0.8)",
                    "rgba(75, 192, 192, 0.8)",
                    "rgba(153, 102, 255, 0.8)",
                    "rgba(255, 159, 64, 0.8)",
                    "rgba(199, 199, 199, 0.8)",
                    "rgba(83, 102, 255, 0.8)",
                    "rgba(255, 99, 255, 0.8)",
                    "rgba(99, 255, 132, 0.8)"
                ][:len(labels)]
            }]
        }
    
    def _process_pie_chart_data(self, events: List[Dict[str, Any]], 
                              chart_config: ChartConfig) -> Dict[str, Any]:
        """Process data for pie charts."""
        
        if not events:
            return {"labels": [], "datasets": []}
        
        # Group by the specified field
        group_field = chart_config.group_by or "intent"
        grouped_data = defaultdict(int)
        
        for event in events:
            group_value = event.get(group_field, "unknown")
            if group_value:  # Skip None/empty values
                grouped_data[group_value] += 1
        
        # Sort by count (descending)
        sorted_groups = sorted(grouped_data.items(), key=lambda x: x[1], reverse=True)
        
        labels = [item[0] for item in sorted_groups[:8]]  # Top 8 for readability
        data_points = [item[1] for item in sorted_groups[:8]]
        
        return {
            "labels": labels,
            "datasets": [{
                "data": data_points,
                "backgroundColor": [
                    "#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0",
                    "#9966FF", "#FF9F40", "#FF6384", "#C9CBCF"
                ][:len(labels)]
            }]
        }
    
    def _process_gauge_chart_data(self, events: List[Dict[str, Any]], 
                                chart_config: ChartConfig) -> Dict[str, Any]:
        """Process data for gauge charts."""
        
        if not events:
            return {"value": 0, "max": 100}
        
        # Calculate the metric based on aggregation type
        if chart_config.aggregation == "avg" and chart_config.data_source == "response_time":
            response_times = [e.get("duration_ms", 0) for e in events if e.get("duration_ms")]
            value = sum(response_times) / len(response_times) if response_times else 0
            max_value = chart_config.critical_threshold or 1000  # Default 1000ms
        elif chart_config.aggregation == "rate" and chart_config.data_source == "error_rate":
            failed_events = [e for e in events if e.get("success") is False]
            value = (len(failed_events) / len(events)) * 100 if events else 0
            max_value = 100  # Percentage
        else:
            # Default: count of events
            value = len(events)
            max_value = chart_config.critical_threshold or max(100, value * 1.2)
        
        return {
            "value": round(value, 2),
            "max": max_value,
            "warning_threshold": chart_config.warning_threshold,
            "critical_threshold": chart_config.critical_threshold
        }
    
    def _process_heatmap_chart_data(self, events: List[Dict[str, Any]], 
                                  chart_config: ChartConfig) -> Dict[str, Any]:
        """Process data for heatmap charts."""
        
        if not events:
            return {"data": []}
        
        # Create hourly heatmap for the last 7 days
        heatmap_data = []
        
        # Group events by hour and day
        hourly_counts = defaultdict(lambda: defaultdict(int))
        
        for event in events:
            dt = datetime.fromtimestamp(event["timestamp"], timezone.utc)
            day_key = dt.strftime("%Y-%m-%d")
            hour_key = dt.hour
            hourly_counts[day_key][hour_key] += 1
        
        # Create matrix data
        days = sorted(hourly_counts.keys())[-7:]  # Last 7 days
        
        for day in days:
            day_data = []
            for hour in range(24):
                count = hourly_counts[day][hour]
                day_data.append(count)
            heatmap_data.append(day_data)
        
        return {
            "data": heatmap_data,
            "days": days,
            "hours": list(range(24))
        }
    
    def _process_histogram_chart_data(self, events: List[Dict[str, Any]], 
                                    chart_config: ChartConfig) -> Dict[str, Any]:
        """Process data for histogram charts."""
        
        if not events:
            return {"labels": [], "datasets": []}
        
        # Extract values for histogram
        values = []
        value_field = chart_config.data_source or "duration_ms"
        
        for event in events:
            value = event.get(value_field)
            if value is not None and isinstance(value, (int, float)):
                values.append(value)
        
        if not values:
            return {"labels": [], "datasets": []}
        
        # Create histogram bins
        min_value = min(values)
        max_value = max(values)
        bin_count = min(20, len(values) // 5)  # Adaptive bin count
        
        if bin_count == 0:
            bin_count = 1
        
        bin_width = (max_value - min_value) / bin_count
        bins = [0] * bin_count
        labels = []
        
        for i in range(bin_count):
            bin_start = min_value + i * bin_width
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
                "backgroundColor": "rgba(54, 162, 235, 0.8)",
                "borderColor": "rgba(54, 162, 235, 1)",
                "borderWidth": 1
            }]
        }
    
    def _process_table_chart_data(self, events: List[Dict[str, Any]], 
                                chart_config: ChartConfig) -> Dict[str, Any]:
        """Process data for table displays."""
        
        if not events:
            return {"columns": [], "rows": []}
        
        # Define columns based on chart configuration or common fields
        columns = [
            {"key": "timestamp", "label": "Time", "type": "datetime"},
            {"key": "event_type", "label": "Event Type", "type": "string"},
            {"key": "intent", "label": "Intent", "type": "string"},
            {"key": "duration_ms", "label": "Duration (ms)", "type": "number"},
            {"key": "success", "label": "Success", "type": "boolean"}
        ]
        
        # Prepare table rows (latest events first)
        rows = []
        for event in sorted(events, key=lambda x: x["timestamp"], reverse=True)[:50]:
            row = {}
            for col in columns:
                value = event.get(col["key"])
                if col["type"] == "datetime" and value:
                    row[col["key"]] = datetime.fromtimestamp(value, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                elif col["type"] == "boolean" and value is not None:
                    row[col["key"]] = "Yes" if value else "No"
                else:
                    row[col["key"]] = value
            rows.append(row)
        
        return {
            "columns": columns,
            "rows": rows,
            "total_rows": len(events)
        }
    
    def _get_time_interval(self, event_count: int) -> int:
        """Get appropriate time interval for grouping based on event count."""
        if event_count <= 50:
            return 300   # 5 minutes
        elif event_count <= 200:
            return 900   # 15 minutes
        elif event_count <= 500:
            return 1800  # 30 minutes
        else:
            return 3600  # 1 hour
    
    def _validate_dashboard_config(self, config: DashboardConfig) -> bool:
        """Validate dashboard configuration."""
        if not config.dashboard_id or not config.title:
            return False
        
        # Validate chart configurations
        for chart in config.charts:
            if not chart.chart_id or not chart.title:
                return False
            if chart.chart_type not in ChartType:
                return False
        
        return True
    
    def _register_default_dashboards(self):
        """Register predefined dashboard templates."""
        
        # System Overview Dashboard
        system_overview = DashboardConfig(
            dashboard_id="system_overview",
            title="System Overview",
            description="High-level system metrics and performance indicators",
            charts=[
                ChartConfig(
                    chart_id="queries_over_time",
                    title="Queries Over Time",
                    chart_type=ChartType.LINE,
                    data_source="queries",
                    filters={"event_type": "query_completed"},
                    position=(0, 0),
                    width=6
                ),
                ChartConfig(
                    chart_id="error_rate_gauge",
                    title="Error Rate",
                    chart_type=ChartType.GAUGE,
                    data_source="error_rate",
                    aggregation="rate",
                    warning_threshold=5.0,
                    critical_threshold=10.0,
                    position=(0, 6),
                    width=3
                ),
                ChartConfig(
                    chart_id="avg_response_time",
                    title="Average Response Time",
                    chart_type=ChartType.GAUGE,
                    data_source="response_time",
                    aggregation="avg",
                    warning_threshold=500.0,
                    critical_threshold=1000.0,
                    position=(0, 9),
                    width=3
                ),
                ChartConfig(
                    chart_id="query_intents_pie",
                    title="Query Intents Distribution",
                    chart_type=ChartType.PIE,
                    data_source="intents",
                    group_by="intent",
                    position=(1, 0),
                    width=6
                ),
                ChartConfig(
                    chart_id="recent_events_table",
                    title="Recent Events",
                    chart_type=ChartType.TABLE,
                    data_source="events",
                    position=(1, 6),
                    width=6
                )
            ]
        )
        
        # Performance Dashboard
        performance_dashboard = DashboardConfig(
            dashboard_id="performance",
            title="Performance Metrics",
            description="Detailed performance and timing metrics",
            charts=[
                ChartConfig(
                    chart_id="response_time_histogram",
                    title="Response Time Distribution",
                    chart_type=ChartType.HISTOGRAM,
                    data_source="duration_ms",
                    filters={"event_type": "query_completed"},
                    position=(0, 0),
                    width=6
                ),
                ChartConfig(
                    chart_id="hourly_activity_heatmap",
                    title="Activity Heatmap (Hourly)",
                    chart_type=ChartType.HEATMAP,
                    data_source="activity",
                    position=(0, 6),
                    width=6
                ),
                ChartConfig(
                    chart_id="search_performance_bar",
                    title="Search Performance by Type",
                    chart_type=ChartType.BAR,
                    data_source="search_performance",
                    group_by="event_type",
                    filters={"event_type": "search_executed"},
                    position=(1, 0),
                    width=12
                )
            ]
        )
        
        self.dashboards["system_overview"] = system_overview
        self.dashboards["performance"] = performance_dashboard
    
    def list_dashboards(self) -> List[Dict[str, Any]]:
        """List all available dashboards."""
        dashboard_list = []
        
        for dashboard_id, config in self.dashboards.items():
            dashboard_list.append({
                "dashboard_id": dashboard_id,
                "title": config.title,
                "description": config.description,
                "charts_count": len(config.charts),
                "created_at": config.created_at,
                "updated_at": config.updated_at,
                "tags": config.tags,
                "public": config.public
            })
        
        return dashboard_list
    
    def get_dashboard_config(self, dashboard_id: str) -> Optional[DashboardConfig]:
        """Get dashboard configuration."""
        return self.dashboards.get(dashboard_id)
    
    def update_dashboard_config(self, dashboard_config: DashboardConfig) -> bool:
        """Update existing dashboard configuration."""
        if dashboard_config.dashboard_id not in self.dashboards:
            return False
        
        dashboard_config.updated_at = time.time()
        self.dashboards[dashboard_config.dashboard_id] = dashboard_config
        
        # Clear related cache
        cache_keys_to_remove = [k for k in self.chart_cache.keys() 
                               if any(chart.chart_id in k for chart in dashboard_config.charts)]
        for key in cache_keys_to_remove:
            del self.chart_cache[key]
        
        return True
    
    def delete_dashboard(self, dashboard_id: str) -> bool:
        """Delete a dashboard."""
        if dashboard_id not in self.dashboards:
            return False
        
        # Clear related cache
        dashboard = self.dashboards[dashboard_id]
        cache_keys_to_remove = [k for k in self.chart_cache.keys() 
                               if any(chart.chart_id in k for chart in dashboard.charts)]
        for key in cache_keys_to_remove:
            del self.chart_cache[key]
        
        del self.dashboards[dashboard_id]
        return True
    
    def clear_cache(self, dashboard_id: str = None):
        """Clear dashboard cache."""
        if dashboard_id:
            # Clear cache for specific dashboard
            if dashboard_id in self.dashboards:
                dashboard = self.dashboards[dashboard_id]
                cache_keys_to_remove = [k for k in self.chart_cache.keys() 
                                       if any(chart.chart_id in k for chart in dashboard.charts)]
                for key in cache_keys_to_remove:
                    del self.chart_cache[key]
        else:
            # Clear all cache
            self.chart_cache.clear()

# Utility functions
def create_metrics_dashboard(analytics_collector: AnalyticsCollector) -> MetricsDashboard:
    """Create and initialize metrics dashboard."""
    dashboard = MetricsDashboard(analytics_collector)
    logfire.info("Metrics dashboard created and initialized")
    return dashboard

if __name__ == "__main__":
    # Example usage and testing
    async def main():
        print("📊 Testing Metrics Dashboard")
        
        # Mock analytics collector for testing
        from unittest.mock import Mock
        
        mock_collector = Mock()
        mock_collector.events_queue = []
        
        # Add some mock events
        for i in range(50):
            mock_event = Mock()
            mock_event.timestamp = time.time() - (i * 60)  # Events over last hour
            mock_event.event_type = Mock()
            mock_event.event_type.value = "query_completed" if i % 4 != 0 else "query_failed"
            mock_event.intent = ["search", "explain", "compare", "tutorial"][i % 4]
            mock_event.duration_ms = 100 + (i * 10)
            mock_event.success = i % 4 != 0
            mock_event.session_id = f"session_{i // 10}"
            mock_event.user_id = f"user_{i % 5}"
            mock_event.source_component = "query_processor"
            mock_event.data = {}
            
            # Mock to_dict method
            mock_event.to_dict = lambda: {
                "event_type": mock_event.event_type.value,
                "timestamp": mock_event.timestamp,
                "intent": mock_event.intent,
                "duration_ms": mock_event.duration_ms,
                "success": mock_event.success,
                "session_id": mock_event.session_id,
                "user_id": mock_event.user_id,
                "source_component": mock_event.source_component,
                "data": mock_event.data
            }
            
            mock_collector.events_queue.append(mock_event)
        
        # Create dashboard
        dashboard = create_metrics_dashboard(mock_collector)
        
        # Test getting system overview dashboard
        system_data = await dashboard.get_dashboard_data("system_overview")
        
        print(f"Dashboard: {system_data['title']}")
        print(f"Charts: {len(system_data['charts'])}")
        
        for chart in system_data['charts']:
            if chart.get('status') == 'success':
                print(f"- {chart['title']}: {chart['chart_type']} ({chart.get('total_points', 0)} points)")
            else:
                print(f"- {chart['title']}: ERROR - {chart.get('error_message', 'Unknown error')}")
        
        # Test performance dashboard
        perf_data = await dashboard.get_dashboard_data("performance")
        print(f"\nPerformance Dashboard: {len(perf_data['charts'])} charts")
        
        # List all dashboards
        all_dashboards = dashboard.list_dashboards()
        print(f"\nAvailable dashboards: {len(all_dashboards)}")
        for db in all_dashboards:
            print(f"- {db['title']} ({db['charts_count']} charts)")
        
        print("\n✅ Metrics dashboard test completed")
    
    asyncio.run(main())