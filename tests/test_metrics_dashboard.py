#!/usr/bin/env python3
"""
Test suite for Metrics Dashboard
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

from metrics_dashboard import (
    MetricsDashboard,
    DashboardConfig,
    ChartConfig,
    ChartData,
    ChartType,
    TimeRange,
    RefreshInterval,
    create_metrics_dashboard
)

class TestChartConfig:
    """Test chart configuration."""
    
    def test_chart_config_creation(self):
        """Test chart configuration creation."""
        config = ChartConfig(
            chart_id="test_chart",
            title="Test Chart",
            chart_type=ChartType.LINE,
            data_source="test_data",
            time_range=TimeRange.LAST_24_HOURS,
            refresh_interval=RefreshInterval.NORMAL
        )
        
        assert config.chart_id == "test_chart"
        assert config.title == "Test Chart"
        assert config.chart_type == ChartType.LINE
        assert config.data_source == "test_data"
        assert config.time_range == TimeRange.LAST_24_HOURS
        assert config.refresh_interval == RefreshInterval.NORMAL
        assert config.width == 6  # Default
        assert config.height == 4  # Default
        assert config.position == (0, 0)  # Default
    
    def test_chart_config_with_thresholds(self):
        """Test chart configuration with alert thresholds."""
        config = ChartConfig(
            chart_id="gauge_chart",
            title="Performance Gauge",
            chart_type=ChartType.GAUGE,
            data_source="response_time",
            warning_threshold=500.0,
            critical_threshold=1000.0
        )
        
        assert config.warning_threshold == 500.0
        assert config.critical_threshold == 1000.0
    
    def test_chart_config_with_filters(self):
        """Test chart configuration with filters."""
        config = ChartConfig(
            chart_id="filtered_chart",
            title="Filtered Chart",
            chart_type=ChartType.BAR,
            data_source="events",
            filters={"event_type": "query_completed", "success": True},
            group_by="intent"
        )
        
        assert config.filters["event_type"] == "query_completed"
        assert config.filters["success"] is True
        assert config.group_by == "intent"

class TestDashboardConfig:
    """Test dashboard configuration."""
    
    def test_dashboard_config_creation(self):
        """Test dashboard configuration creation."""
        chart1 = ChartConfig(
            chart_id="chart1",
            title="Chart 1",
            chart_type=ChartType.LINE,
            data_source="data1"
        )
        
        chart2 = ChartConfig(
            chart_id="chart2",
            title="Chart 2",
            chart_type=ChartType.PIE,
            data_source="data2"
        )
        
        config = DashboardConfig(
            dashboard_id="test_dashboard",
            title="Test Dashboard",
            description="A test dashboard",
            charts=[chart1, chart2]
        )
        
        assert config.dashboard_id == "test_dashboard"
        assert config.title == "Test Dashboard"
        assert config.description == "A test dashboard"
        assert len(config.charts) == 2
        assert config.grid_columns == 12  # Default
        assert config.auto_refresh is True  # Default
        assert config.public is False  # Default
    
    def test_dashboard_config_with_access_control(self):
        """Test dashboard configuration with access control."""
        config = DashboardConfig(
            dashboard_id="private_dashboard",
            title="Private Dashboard",
            public=False,
            allowed_users=["user1", "user2", "admin"]
        )
        
        assert config.public is False
        assert "user1" in config.allowed_users
        assert "admin" in config.allowed_users
        assert len(config.allowed_users) == 3

class TestChartData:
    """Test chart data structure."""
    
    def test_chart_data_creation(self):
        """Test chart data creation."""
        data = ChartData(
            chart_id="test_chart",
            title="Test Chart",
            chart_type=ChartType.LINE,
            data={"labels": ["A", "B"], "datasets": [{"data": [1, 2]}]},
            total_points=2,
            time_range="24h"
        )
        
        assert data.chart_id == "test_chart"
        assert data.title == "Test Chart"
        assert data.chart_type == ChartType.LINE
        assert data.data["labels"] == ["A", "B"]
        assert data.total_points == 2
        assert data.time_range == "24h"
        assert data.status == "success"  # Default
        assert data.error_message is None
        assert isinstance(data.timestamp, float)

class TestMetricsDashboard:
    """Test metrics dashboard functionality."""
    
    @pytest.fixture
    def mock_analytics_collector(self):
        """Create mock analytics collector."""
        collector = Mock()
        collector.events_queue = []
        
        # Add some mock events
        current_time = time.time()
        
        for i in range(20):
            event = Mock()
            event.timestamp = current_time - (i * 300)  # Events every 5 minutes
            event.event_type = Mock()
            
            if i % 4 == 0:
                event.event_type.value = "query_failed"
                event.success = False
            else:
                event.event_type.value = "query_completed"
                event.success = True
            
            event.intent = ["search", "explain", "compare", "tutorial"][i % 4]
            event.duration_ms = 100 + (i * 10)
            event.session_id = f"session_{i // 5}"
            event.user_id = f"user_{i % 3}"
            event.source_component = "query_processor"
            event.data = {"test_field": f"value_{i}"}
            
            # Mock to_dict method
            def make_to_dict(evt):
                return lambda: {
                    "event_type": evt.event_type.value,
                    "timestamp": evt.timestamp,
                    "intent": evt.intent,
                    "duration_ms": evt.duration_ms,
                    "success": evt.success,
                    "session_id": evt.session_id,
                    "user_id": evt.user_id,
                    "source_component": evt.source_component,
                    "data": evt.data
                }
            
            event.to_dict = make_to_dict(event)
            collector.events_queue.append(event)
        
        return collector
    
    @pytest.fixture
    def dashboard(self, mock_analytics_collector):
        """Create test dashboard."""
        return MetricsDashboard(mock_analytics_collector)
    
    def test_dashboard_initialization(self, mock_analytics_collector):
        """Test dashboard initialization."""
        dashboard = MetricsDashboard(mock_analytics_collector)
        
        assert dashboard.analytics_collector == mock_analytics_collector
        assert isinstance(dashboard.dashboards, dict)
        assert isinstance(dashboard.chart_cache, dict)
        
        # Should have default dashboards
        assert "system_overview" in dashboard.dashboards
        assert "performance" in dashboard.dashboards
    
    def test_create_dashboard(self, dashboard):
        """Test dashboard creation."""
        chart_config = ChartConfig(
            chart_id="test_chart",
            title="Test Chart",
            chart_type=ChartType.LINE,
            data_source="test_data"
        )
        
        dashboard_config = DashboardConfig(
            dashboard_id="test_dashboard",
            title="Test Dashboard",
            charts=[chart_config]
        )
        
        success = dashboard.create_dashboard(dashboard_config)
        
        assert success is True
        assert "test_dashboard" in dashboard.dashboards
        assert dashboard.dashboards["test_dashboard"].title == "Test Dashboard"
    
    def test_create_invalid_dashboard(self, dashboard):
        """Test creating invalid dashboard."""
        # Missing dashboard_id
        invalid_config = DashboardConfig(
            dashboard_id="",
            title="Invalid Dashboard"
        )
        
        success = dashboard.create_dashboard(invalid_config)
        assert success is False
    
    @pytest.mark.asyncio
    async def test_get_dashboard_data(self, dashboard):
        """Test getting dashboard data."""
        # Use the default system_overview dashboard
        data = await dashboard.get_dashboard_data("system_overview")
        
        assert data["dashboard_id"] == "system_overview"
        assert data["title"] == "System Overview"
        assert "charts" in data
        assert isinstance(data["charts"], list)
        assert len(data["charts"]) > 0
        assert "last_updated" in data
        assert data["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_dashboard(self, dashboard):
        """Test getting data for nonexistent dashboard."""
        data = await dashboard.get_dashboard_data("nonexistent")
        
        assert "error" in data
        assert data["error"] == "Dashboard not found"
    
    @pytest.mark.asyncio
    async def test_line_chart_processing(self, dashboard):
        """Test line chart data processing."""
        chart_config = ChartConfig(
            chart_id="line_test",
            title="Line Chart Test",
            chart_type=ChartType.LINE,
            data_source="queries",
            filters={"event_type": "query_completed"}
        )
        
        raw_data = await dashboard._fetch_raw_data(chart_config, TimeRange.LAST_24_HOURS)
        processed_data = dashboard._process_line_chart_data(raw_data, chart_config)
        
        assert "labels" in processed_data
        assert "datasets" in processed_data
        assert isinstance(processed_data["labels"], list)
        assert isinstance(processed_data["datasets"], list)
        
        if processed_data["datasets"]:
            assert "data" in processed_data["datasets"][0]
            assert "label" in processed_data["datasets"][0]
    
    @pytest.mark.asyncio
    async def test_bar_chart_processing(self, dashboard):
        """Test bar chart data processing."""
        chart_config = ChartConfig(
            chart_id="bar_test",
            title="Bar Chart Test",
            chart_type=ChartType.BAR,
            data_source="events",
            group_by="intent"
        )
        
        raw_data = await dashboard._fetch_raw_data(chart_config, TimeRange.LAST_24_HOURS)
        processed_data = dashboard._process_bar_chart_data(raw_data, chart_config)
        
        assert "labels" in processed_data
        assert "datasets" in processed_data
        
        if processed_data["datasets"]:
            dataset = processed_data["datasets"][0]
            assert "data" in dataset
            assert "backgroundColor" in dataset
            assert len(dataset["data"]) == len(processed_data["labels"])
    
    @pytest.mark.asyncio
    async def test_pie_chart_processing(self, dashboard):
        """Test pie chart data processing."""
        chart_config = ChartConfig(
            chart_id="pie_test",
            title="Pie Chart Test",
            chart_type=ChartType.PIE,
            data_source="intents",
            group_by="intent"
        )
        
        raw_data = await dashboard._fetch_raw_data(chart_config, TimeRange.LAST_24_HOURS)
        processed_data = dashboard._process_pie_chart_data(raw_data, chart_config)
        
        assert "labels" in processed_data
        assert "datasets" in processed_data
        
        if processed_data["datasets"]:
            dataset = processed_data["datasets"][0]
            assert "data" in dataset
            assert "backgroundColor" in dataset
            assert len(dataset["data"]) == len(processed_data["labels"])
    
    @pytest.mark.asyncio
    async def test_gauge_chart_processing(self, dashboard):
        """Test gauge chart data processing."""
        chart_config = ChartConfig(
            chart_id="gauge_test",
            title="Gauge Chart Test",
            chart_type=ChartType.GAUGE,
            data_source="response_time",
            aggregation="avg",
            warning_threshold=500.0,
            critical_threshold=1000.0
        )
        
        raw_data = await dashboard._fetch_raw_data(chart_config, TimeRange.LAST_24_HOURS)
        processed_data = dashboard._process_gauge_chart_data(raw_data, chart_config)
        
        assert "value" in processed_data
        assert "max" in processed_data
        assert isinstance(processed_data["value"], (int, float))
        assert isinstance(processed_data["max"], (int, float))
        assert processed_data["warning_threshold"] == 500.0
        assert processed_data["critical_threshold"] == 1000.0
    
    @pytest.mark.asyncio
    async def test_histogram_chart_processing(self, dashboard):
        """Test histogram chart data processing."""
        chart_config = ChartConfig(
            chart_id="histogram_test",
            title="Histogram Test",
            chart_type=ChartType.HISTOGRAM,
            data_source="duration_ms"
        )
        
        raw_data = await dashboard._fetch_raw_data(chart_config, TimeRange.LAST_24_HOURS)
        processed_data = dashboard._process_histogram_chart_data(raw_data, chart_config)
        
        assert "labels" in processed_data
        assert "datasets" in processed_data
        
        if processed_data["datasets"]:
            dataset = processed_data["datasets"][0]
            assert "data" in dataset
            assert len(dataset["data"]) == len(processed_data["labels"])
    
    @pytest.mark.asyncio
    async def test_table_chart_processing(self, dashboard):
        """Test table chart data processing."""
        chart_config = ChartConfig(
            chart_id="table_test",
            title="Table Test",
            chart_type=ChartType.TABLE,
            data_source="events"
        )
        
        raw_data = await dashboard._fetch_raw_data(chart_config, TimeRange.LAST_24_HOURS)
        processed_data = dashboard._process_table_chart_data(raw_data, chart_config)
        
        assert "columns" in processed_data
        assert "rows" in processed_data
        assert "total_rows" in processed_data
        assert isinstance(processed_data["columns"], list)
        assert isinstance(processed_data["rows"], list)
        
        if processed_data["columns"]:
            col = processed_data["columns"][0]
            assert "key" in col
            assert "label" in col
            assert "type" in col
    
    @pytest.mark.asyncio
    async def test_data_filtering(self, dashboard):
        """Test data filtering functionality."""
        chart_config = ChartConfig(
            chart_id="filtered_test",
            title="Filtered Test",
            chart_type=ChartType.BAR,
            data_source="events",
            filters={"event_type": "query_completed", "success": True}
        )
        
        raw_data = await dashboard._fetch_raw_data(chart_config, TimeRange.LAST_24_HOURS)
        
        # All filtered events should match the criteria
        for event in raw_data:
            assert event["event_type"] == "query_completed"
            assert event["success"] is True
    
    @pytest.mark.asyncio
    async def test_time_range_filtering(self, dashboard):
        """Test time range filtering."""
        chart_config = ChartConfig(
            chart_id="time_test",
            title="Time Range Test",
            chart_type=ChartType.LINE,
            data_source="events"
        )
        
        # Test different time ranges
        current_time = time.time()
        
        # 1 hour data
        data_1h = await dashboard._fetch_raw_data(chart_config, TimeRange.LAST_HOUR)
        for event in data_1h:
            assert event["timestamp"] >= current_time - 3600
        
        # 24 hour data should have more events
        data_24h = await dashboard._fetch_raw_data(chart_config, TimeRange.LAST_24_HOURS)
        assert len(data_24h) >= len(data_1h)
    
    def test_list_dashboards(self, dashboard):
        """Test listing dashboards."""
        dashboards = dashboard.list_dashboards()
        
        assert isinstance(dashboards, list)
        assert len(dashboards) >= 2  # At least the default dashboards
        
        # Check structure
        for db in dashboards:
            assert "dashboard_id" in db
            assert "title" in db
            assert "description" in db
            assert "charts_count" in db
            assert "created_at" in db
            assert "public" in db
    
    def test_get_dashboard_config(self, dashboard):
        """Test getting dashboard configuration."""
        config = dashboard.get_dashboard_config("system_overview")
        
        assert config is not None
        assert config.dashboard_id == "system_overview"
        assert config.title == "System Overview"
        assert len(config.charts) > 0
        
        # Test nonexistent dashboard
        missing_config = dashboard.get_dashboard_config("nonexistent")
        assert missing_config is None
    
    def test_update_dashboard_config(self, dashboard):
        """Test updating dashboard configuration."""
        # Get existing config
        config = dashboard.get_dashboard_config("system_overview")
        
        # Modify it
        original_title = config.title
        config.title = "Modified System Overview"
        
        # Update
        success = dashboard.update_dashboard_config(config)
        assert success is True
        
        # Verify update
        updated_config = dashboard.get_dashboard_config("system_overview")
        assert updated_config.title == "Modified System Overview"
        
        # Restore original
        config.title = original_title
        dashboard.update_dashboard_config(config)
    
    def test_update_nonexistent_dashboard(self, dashboard):
        """Test updating nonexistent dashboard."""
        fake_config = DashboardConfig(
            dashboard_id="nonexistent",
            title="Fake Dashboard"
        )
        
        success = dashboard.update_dashboard_config(fake_config)
        assert success is False
    
    def test_delete_dashboard(self, dashboard):
        """Test deleting dashboard."""
        # Create a test dashboard first
        test_config = DashboardConfig(
            dashboard_id="test_delete",
            title="Delete Test Dashboard"
        )
        
        dashboard.create_dashboard(test_config)
        assert "test_delete" in dashboard.dashboards
        
        # Delete it
        success = dashboard.delete_dashboard("test_delete")
        assert success is True
        assert "test_delete" not in dashboard.dashboards
        
        # Try deleting nonexistent dashboard
        success = dashboard.delete_dashboard("nonexistent")
        assert success is False
    
    def test_cache_functionality(self, dashboard):
        """Test dashboard caching."""
        # Clear cache first
        dashboard.clear_cache()
        assert len(dashboard.chart_cache) == 0
        
        # Add some test data to cache
        test_chart_data = ChartData(
            chart_id="test_chart",
            title="Test Chart",
            chart_type=ChartType.LINE,
            data={"test": "data"}
        )
        
        cache_key = "test_chart_24h"
        dashboard.chart_cache[cache_key] = test_chart_data
        
        assert len(dashboard.chart_cache) == 1
        
        # Clear cache again
        dashboard.clear_cache()
        assert len(dashboard.chart_cache) == 0
    
    def test_dashboard_validation(self, dashboard):
        """Test dashboard configuration validation."""
        # Valid config
        valid_config = DashboardConfig(
            dashboard_id="valid_test",
            title="Valid Dashboard",
            charts=[
                ChartConfig(
                    chart_id="valid_chart",
                    title="Valid Chart",
                    chart_type=ChartType.LINE,
                    data_source="test"
                )
            ]
        )
        
        assert dashboard._validate_dashboard_config(valid_config) is True
        
        # Invalid config - missing dashboard_id
        invalid_config1 = DashboardConfig(
            dashboard_id="",
            title="Invalid Dashboard"
        )
        
        assert dashboard._validate_dashboard_config(invalid_config1) is False
        
        # Invalid config - missing title
        invalid_config2 = DashboardConfig(
            dashboard_id="invalid_test",
            title=""
        )
        
        assert dashboard._validate_dashboard_config(invalid_config2) is False
        
        # Invalid config - chart missing chart_id
        invalid_config3 = DashboardConfig(
            dashboard_id="invalid_test",
            title="Invalid Dashboard",
            charts=[
                ChartConfig(
                    chart_id="",
                    title="Invalid Chart",
                    chart_type=ChartType.LINE,
                    data_source="test"
                )
            ]
        )
        
        assert dashboard._validate_dashboard_config(invalid_config3) is False

class TestTimeIntervals:
    """Test time interval calculations."""
    
    def test_get_time_interval(self):
        """Test time interval calculation based on event count."""
        dashboard = MetricsDashboard(Mock())
        
        # Small event count - 5 minute intervals
        assert dashboard._get_time_interval(30) == 300
        
        # Medium event count - 15 minute intervals
        assert dashboard._get_time_interval(100) == 900
        
        # Larger event count - 30 minute intervals
        assert dashboard._get_time_interval(300) == 1800
        
        # Large event count - 1 hour intervals
        assert dashboard._get_time_interval(1000) == 3600

class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_create_metrics_dashboard(self):
        """Test dashboard creation utility."""
        mock_collector = Mock()
        dashboard = create_metrics_dashboard(mock_collector)
        
        assert isinstance(dashboard, MetricsDashboard)
        assert dashboard.analytics_collector == mock_collector

if __name__ == "__main__":
    pytest.main([__file__, "-v"])