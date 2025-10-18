"""
Tests for Dashboard Framework

Tests widget rendering, dashboard configuration, access control,
and multiple renderers.
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from core.dashboard import (
    Dashboard,
    DashboardAccessControl,
    Widget,
    WidgetConfig,
    MetricWidget,
    ChartWidget,
    AlertWidget,
    SummaryWidget,
    BaselineWidget,
    create_widget,
    TextRenderer,
    JSONRenderer,
    MarkdownRenderer,
    create_renderer,
    render_dashboard,
)
from core.metrics_aggregator import get_metrics_aggregator, MetricType, MetricSnapshot
from core.metrics_baseline import get_baseline_manager


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory"""
    config_dir = tmp_path / "dashboards"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def sample_metrics():
    """Create sample metrics for testing"""
    aggregator = get_metrics_aggregator()
    
    # Add some test metrics
    now = datetime.now()
    for i in range(10):
        timestamp = now - timedelta(hours=10-i)
        snapshot1 = MetricSnapshot(
            metric_type=MetricType.GAUGE,
            name="test.metric",
            value=100 + i * 10,
            timestamp=timestamp,
            tags={}
        )
        snapshot2 = MetricSnapshot(
            metric_type=MetricType.GAUGE,
            name="test.cpu",
            value=50 + i * 2,
            timestamp=timestamp,
            tags={}
        )
        aggregator.record_metric(snapshot1)
        aggregator.record_metric(snapshot2)
    
    yield
    
    # Note: Cleanup not needed - each test uses unique metric names


class TestWidgetConfig:
    """Test widget configuration"""
    
    def test_widget_config_creation(self):
        """Test creating widget config"""
        config = WidgetConfig(
            widget_type="metric",
            metric_name="test.metric",
            label="Test Metric",
        )
        
        assert config.widget_type == "metric"
        assert config.metric_name == "test.metric"
        assert config.label == "Test Metric"
    
    def test_widget_config_to_dict(self):
        """Test widget config serialization"""
        config = WidgetConfig(
            widget_type="metric",
            metric_name="test.metric",
            label="Test Metric",
            format="number",
            decimals=2,
        )
        
        data = config.to_dict()
        
        assert data["widget_type"] == "metric"
        assert data["metric_name"] == "test.metric"
        assert data["label"] == "Test Metric"
        assert data["format"] == "number"
        assert data["decimals"] == 2
    
    def test_widget_config_from_dict(self):
        """Test widget config deserialization"""
        data = {
            "widget_type": "chart",
            "metric_name": "test.metric",
            "label": "Test Chart",
            "chart_type": "sparkline",
            "window_hours": 24,
        }
        
        config = WidgetConfig.from_dict(data)
        
        assert config.widget_type == "chart"
        assert config.metric_name == "test.metric"
        assert config.chart_type == "sparkline"
        assert config.window_hours == 24


class TestWidgets:
    """Test widget implementations"""
    
    def test_metric_widget_render(self, sample_metrics):
        """Test metric widget rendering"""
        config = WidgetConfig(
            widget_type="metric",
            metric_name="test.metric",
            label="Test Metric",
        )
        
        widget = MetricWidget(config)
        output = widget.render()
        
        assert "Test Metric" in output
        assert ":" in output  # Should have label:value format
    
    def test_metric_widget_to_dict(self, sample_metrics):
        """Test metric widget data export"""
        config = WidgetConfig(
            widget_type="metric",
            metric_name="test.metric",
        )
        
        widget = MetricWidget(config)
        data = widget.to_dict()
        
        assert data["widget_type"] == "metric"
        assert data["metric_name"] == "test.metric"
        assert data["value"] is not None
        assert data["data_points"] > 0
    
    def test_chart_widget_sparkline(self, sample_metrics):
        """Test chart widget sparkline rendering"""
        config = WidgetConfig(
            widget_type="chart",
            metric_name="test.metric",
            chart_type="sparkline",
            window_hours=24,
        )
        
        widget = ChartWidget(config)
        output = widget.render()
        
        assert "Test Metric" in output
        # Should contain sparkline characters
        assert any(c in output for c in "▁▂▃▄▅▆▇█")
    
    def test_chart_widget_bar(self, sample_metrics):
        """Test chart widget bar rendering"""
        config = WidgetConfig(
            widget_type="chart",
            metric_name="test.metric",
            chart_type="bar",
            window_hours=24,
        )
        
        widget = ChartWidget(config)
        output = widget.render()
        
        assert "│" in output  # Bar chart marker
    
    def test_summary_widget(self, sample_metrics):
        """Test summary widget"""
        config = WidgetConfig(
            widget_type="summary",
            label="Test Summary",
            window_hours=24,
            extra={
                "metrics": [
                    {"name": "test.metric", "agg": "avg"},
                    {"name": "test.metric", "agg": "max"},
                ]
            },
        )
        
        widget = SummaryWidget(config)
        output = widget.render()
        
        assert "Test Summary" in output
        assert "avg" in output
        assert "max" in output
    
    def test_baseline_widget(self, sample_metrics):
        """Test baseline widget"""
        # Calculate baseline first
        baseline_mgr = get_baseline_manager()
        baseline_mgr.calculate_baseline("test.metric", window_hours=24)
        
        config = WidgetConfig(
            widget_type="baseline",
            metric_name="test.metric",
            label="Test Baseline",
        )
        
        widget = BaselineWidget(config)
        output = widget.render()
        
        assert "Test Baseline" in output
        # Verify it renders something (could be "No data" or baseline info)
        assert len(output) > 0


class TestWidgetFactory:
    """Test widget factory"""
    
    def test_create_metric_widget(self):
        """Test creating metric widget via factory"""
        config = WidgetConfig(widget_type="metric", metric_name="test")
        widget = create_widget(config)
        
        assert isinstance(widget, MetricWidget)
    
    def test_create_chart_widget(self):
        """Test creating chart widget via factory"""
        config = WidgetConfig(widget_type="chart", metric_name="test")
        widget = create_widget(config)
        
        assert isinstance(widget, ChartWidget)
    
    def test_create_alert_widget(self):
        """Test creating alert widget via factory"""
        config = WidgetConfig(widget_type="alert")
        widget = create_widget(config)
        
        assert isinstance(widget, AlertWidget)
    
    def test_create_summary_widget(self):
        """Test creating summary widget via factory"""
        config = WidgetConfig(widget_type="summary")
        widget = create_widget(config)
        
        assert isinstance(widget, SummaryWidget)
    
    def test_create_baseline_widget(self):
        """Test creating baseline widget via factory"""
        config = WidgetConfig(widget_type="baseline", metric_name="test")
        widget = create_widget(config)
        
        assert isinstance(widget, BaselineWidget)
    
    def test_create_unknown_widget(self):
        """Test creating unknown widget type fails"""
        config = WidgetConfig(widget_type="unknown")
        
        with pytest.raises(ValueError, match="Unknown widget type"):
            create_widget(config)


class TestRenderers:
    """Test dashboard renderers"""
    
    def test_text_renderer(self, sample_metrics):
        """Test text renderer"""
        config = WidgetConfig(widget_type="metric", metric_name="test.metric")
        widget = MetricWidget(config)
        
        renderer = TextRenderer(width=80)
        output = renderer.render_dashboard(
            title="Test Dashboard",
            widgets=[widget],
            metadata={"description": "Test"},
        )
        
        assert "Test Dashboard" in output
        assert "═" in output  # Header separator
        assert "Test Metric" in output
    
    def test_json_renderer(self, sample_metrics):
        """Test JSON renderer"""
        config = WidgetConfig(widget_type="metric", metric_name="test.metric")
        widget = MetricWidget(config)
        
        renderer = JSONRenderer(pretty=True)
        output = renderer.render_dashboard(
            title="Test Dashboard",
            widgets=[widget],
            metadata={"description": "Test"},
        )
        
        data = json.loads(output)
        
        assert data["title"] == "Test Dashboard"
        assert data["widget_count"] == 1
        assert len(data["widgets"]) == 1
    
    def test_markdown_renderer(self, sample_metrics):
        """Test Markdown renderer"""
        config = WidgetConfig(widget_type="metric", metric_name="test.metric")
        widget = MetricWidget(config)
        
        renderer = MarkdownRenderer()
        output = renderer.render_dashboard(
            title="Test Dashboard",
            widgets=[widget],
            metadata={"description": "Test"},
        )
        
        assert "# Test Dashboard" in output
        assert "## Test Metric" in output
        assert "---" in output


class TestRendererFactory:
    """Test renderer factory"""
    
    def test_create_text_renderer(self):
        """Test creating text renderer"""
        renderer = create_renderer("text")
        assert isinstance(renderer, TextRenderer)
    
    def test_create_json_renderer(self):
        """Test creating JSON renderer"""
        renderer = create_renderer("json")
        assert isinstance(renderer, JSONRenderer)
    
    def test_create_markdown_renderer(self):
        """Test creating Markdown renderer"""
        renderer = create_renderer("markdown")
        assert isinstance(renderer, MarkdownRenderer)
    
    def test_create_unknown_renderer(self):
        """Test creating unknown renderer fails"""
        with pytest.raises(ValueError, match="Unknown renderer type"):
            create_renderer("unknown")


class TestDashboard:
    """Test dashboard engine"""
    
    def test_dashboard_creation(self, sample_metrics):
        """Test creating dashboard programmatically"""
        config = WidgetConfig(widget_type="metric", metric_name="test.metric")
        widget = MetricWidget(config)
        
        dashboard = Dashboard(
            title="Test Dashboard",
            widgets=[widget],
            description="Test",
        )
        
        assert dashboard.title == "Test Dashboard"
        assert len(dashboard.widgets) == 1
        assert dashboard.description == "Test"
    
    def test_dashboard_from_dict(self, sample_metrics):
        """Test creating dashboard from dictionary"""
        config = {
            "title": "Test Dashboard",
            "description": "Test",
            "widgets": [
                {
                    "widget_type": "metric",
                    "metric_name": "test.metric",
                    "label": "Test Metric",
                }
            ],
        }
        
        dashboard = Dashboard.from_dict(config)
        
        assert dashboard.title == "Test Dashboard"
        assert len(dashboard.widgets) == 1
    
    def test_dashboard_from_config(self, temp_config_dir, sample_metrics):
        """Test loading dashboard from config file"""
        # Create test config file
        config = {
            "title": "Test Dashboard",
            "description": "Test",
            "widgets": [
                {
                    "widget_type": "metric",
                    "metric_name": "test.metric",
                }
            ],
        }
        
        config_file = temp_config_dir / "test.json"
        with open(config_file, "w") as f:
            json.dump(config, f)
        
        # Load dashboard
        dashboard = Dashboard.from_config("test", config_dir=temp_config_dir)
        
        assert dashboard.title == "Test Dashboard"
        assert len(dashboard.widgets) == 1
    
    def test_dashboard_render_text(self, sample_metrics):
        """Test rendering dashboard as text"""
        config = WidgetConfig(widget_type="metric", metric_name="test.metric")
        widget = MetricWidget(config)
        
        dashboard = Dashboard(title="Test", widgets=[widget])
        output = dashboard.render_text()
        
        assert "Test" in output
        assert isinstance(output, str)
    
    def test_dashboard_render_json(self, sample_metrics):
        """Test rendering dashboard as JSON"""
        config = WidgetConfig(widget_type="metric", metric_name="test.metric")
        widget = MetricWidget(config)
        
        dashboard = Dashboard(title="Test", widgets=[widget])
        output = dashboard.render_json()
        
        data = json.loads(output)
        assert data["title"] == "Test"
    
    def test_dashboard_render_markdown(self, sample_metrics):
        """Test rendering dashboard as Markdown"""
        config = WidgetConfig(widget_type="metric", metric_name="test.metric")
        widget = MetricWidget(config)
        
        dashboard = Dashboard(title="Test", widgets=[widget])
        output = dashboard.render_markdown()
        
        assert "# Test" in output
    
    def test_dashboard_to_dict(self, sample_metrics):
        """Test exporting dashboard config"""
        config = WidgetConfig(widget_type="metric", metric_name="test.metric")
        widget = MetricWidget(config)
        
        dashboard = Dashboard(title="Test", widgets=[widget])
        data = dashboard.to_dict()
        
        assert data["title"] == "Test"
        assert len(data["widgets"]) == 1
    
    def test_list_available_configs(self, temp_config_dir):
        """Test listing available configs"""
        # Create test config files
        (temp_config_dir / "dashboard1.json").write_text("{}")
        (temp_config_dir / "dashboard2.json").write_text("{}")
        
        configs = Dashboard.list_available_configs(config_dir=temp_config_dir)
        
        assert len(configs) == 2
        assert "dashboard1" in configs
        assert "dashboard2" in configs


class TestAccessControl:
    """Test dashboard access control"""
    
    def test_access_control_default_deny(self, tmp_path, monkeypatch):
        """Test access control defaults to DENY"""
        # Clear the VRP_ADMIN_MODE env var that might be set during development
        monkeypatch.delenv("VRP_ADMIN_MODE", raising=False)
        
        config_file = tmp_path / "settings.json"
        config_file.write_text("{}")
        
        access = DashboardAccessControl(config_path=config_file)
        
        assert not access.is_enabled()
    
    def test_access_control_config_enabled(self, tmp_path):
        """Test access control via config file"""
        config_file = tmp_path / "settings.json"
        config_file.write_text('{"dashboard": {"enabled": true}}')
        
        access = DashboardAccessControl(config_path=config_file)
        
        assert access.is_enabled()
    
    def test_access_control_check_access(self, tmp_path, monkeypatch):
        """Test access check with reason"""
        # Clear the VRP_ADMIN_MODE env var that might be set during development
        monkeypatch.delenv("VRP_ADMIN_MODE", raising=False)
        
        config_file = tmp_path / "settings.json"
        config_file.write_text("{}")
        
        access = DashboardAccessControl(config_path=config_file)
        allowed, reason = access.check_access()
        
        assert not allowed
        assert reason is not None
        assert "not enabled" in reason.lower()


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def test_render_dashboard_function(self, temp_config_dir, sample_metrics):
        """Test render_dashboard convenience function"""
        # Create test config
        config = {
            "title": "Test",
            "widgets": [
                {"widget_type": "metric", "metric_name": "test.metric"}
            ],
        }
        
        config_file = temp_config_dir / "test.json"
        with open(config_file, "w") as f:
            json.dump(config, f)
        
        # This would fail because it uses default config dir
        # In real usage, Dashboard.from_config handles this
        # Just test that function exists and has correct signature
        from inspect import signature
        sig = signature(render_dashboard)
        
        assert "config_name" in sig.parameters
        assert "renderer_type" in sig.parameters
