"""
Dashboard Widget Implementations

Concrete widget types for displaying metrics, charts, alerts, and summaries.
All widgets are config-driven - behavior defined by JSON configuration.

Available Widgets:
- MetricWidget: Display single metric value
- ChartWidget: Render metric as text chart (sparkline/bar)
- AlertWidget: Show recent alerts filtered by severity
- SummaryWidget: Aggregate metrics (sum/avg/count/min/max)
- BaselineWidget: Compare metric to baseline with deviation

Example Usage:
    from core.dashboard.widgets import MetricWidget
    from core.dashboard.widget_base import WidgetConfig
    
    config = WidgetConfig(
        widget_type="metric",
        metric_name="recording.count",
        label="Total Recordings"
    )
    
    widget = MetricWidget(config)
    print(widget.render())
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from core.dashboard.widget_base import Widget, WidgetConfig
from core.metrics_aggregator import (
    get_metrics_aggregator,
    MetricQuery,
    MetricType,
)
from core.metrics_baseline import (
    get_baseline_manager,
    AlertSeverity,
)
from core.logging_config import get_logger

logger = get_logger(__name__)


class MetricWidget(Widget):
    """
    Display single metric value
    
    Shows latest value or aggregated value over time window.
    Optionally shows trend indicator (↑ ↓ →).
    
    Example Config:
        {
            "widget_type": "metric",
            "metric_name": "recording.count",
            "label": "Total Recordings",
            "format": "number",
            "show_trend": true,
            "window_hours": 24
        }
    """
    
    def render(self) -> str:
        """Render metric as text"""
        aggregator = get_metrics_aggregator()
        
        # Build query
        end_time = datetime.now()
        start_time = None
        if self.config.window_hours:
            start_time = end_time - timedelta(hours=self.config.window_hours)
        
        query = MetricQuery(
            metric_name=self.config.metric_name,
            start_time=start_time,
            end_time=end_time,
            tags=self.config.tags,
        )
        
        # Get snapshots
        snapshots = aggregator.query_metrics(query)
        
        if not snapshots:
            return f"{self.get_label()}: No data"
        
        # Get latest value
        latest = snapshots[-1]
        value_str = self.format_value(latest.value)
        
        # Build output
        output = f"{self.get_label()}: {value_str}"
        
        # Add trend if requested
        if self.config.show_trend and len(snapshots) > 1:
            prev = snapshots[-2]
            if latest.value > prev.value:
                output += " ↑"
            elif latest.value < prev.value:
                output += " ↓"
            else:
                output += " →"
        
        return output
    
    def to_dict(self) -> Dict[str, Any]:
        """Export metric data"""
        aggregator = get_metrics_aggregator()
        
        # Build query
        end_time = datetime.now()
        start_time = None
        if self.config.window_hours:
            start_time = end_time - timedelta(hours=self.config.window_hours)
        
        query = MetricQuery(
            metric_name=self.config.metric_name,
            start_time=start_time,
            end_time=end_time,
            tags=self.config.tags,
        )
        
        # Get snapshots
        snapshots = aggregator.query_metrics(query)
        
        return {
            "widget_type": "metric",
            "label": self.get_label(),
            "metric_name": self.config.metric_name,
            "value": snapshots[-1].value if snapshots else None,
            "timestamp": snapshots[-1].timestamp.isoformat() if snapshots else None,
            "data_points": len(snapshots),
        }


class ChartWidget(Widget):
    """
    Render metric as text chart
    
    Supports sparkline (mini line chart) and bar chart styles.
    Useful for showing trends over time in CLI.
    
    Example Config:
        {
            "widget_type": "chart",
            "metric_name": "cpu.usage",
            "label": "CPU Usage (24h)",
            "chart_type": "sparkline",
            "window_hours": 24
        }
    """
    
    def render(self) -> str:
        """Render chart as text"""
        aggregator = get_metrics_aggregator()
        
        # Build query
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=self.config.window_hours or 24)
        
        query = MetricQuery(
            metric_name=self.config.metric_name,
            start_time=start_time,
            end_time=end_time,
            tags=self.config.tags,
        )
        
        # Get snapshots
        snapshots = aggregator.query_metrics(query)
        
        if not snapshots:
            return f"{self.get_label()}: No data"
        
        values = [s.value for s in snapshots]
        
        # Render chart
        if self.config.chart_type == "sparkline":
            chart = self._render_sparkline(values)
        else:  # bar chart
            chart = self._render_bar_chart(values)
        
        return f"{self.get_label()}\n{chart}"
    
    def _render_sparkline(self, values: List[float]) -> str:
        """Render sparkline (mini line chart)"""
        if not values:
            return "(no data)"
        
        # Sparkline characters (low to high)
        chars = "▁▂▃▄▅▆▇█"
        
        min_val = min(values)
        max_val = max(values)
        
        if min_val == max_val:
            return chars[0] * len(values)
        
        # Normalize to 0-7 range
        normalized = [
            int((v - min_val) / (max_val - min_val) * 7)
            for v in values
        ]
        
        return "".join(chars[n] for n in normalized)
    
    def _render_bar_chart(self, values: List[float]) -> str:
        """Render horizontal bar chart"""
        if not values:
            return "(no data)"
        
        # Take last N values to fit width
        max_bars = self.config.chart_width
        if len(values) > max_bars:
            values = values[-max_bars:]
        
        max_val = max(values)
        if max_val == 0:
            return "\n".join("│" for _ in values)
        
        # Render bars
        lines = []
        for v in values:
            bar_len = int((v / max_val) * self.config.chart_width)
            bar = "█" * bar_len
            lines.append(f"│{bar}")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """Export chart data"""
        aggregator = get_metrics_aggregator()
        
        # Build query
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=self.config.window_hours or 24)
        
        query = MetricQuery(
            metric_name=self.config.metric_name,
            start_time=start_time,
            end_time=end_time,
            tags=self.config.tags,
        )
        
        # Get snapshots
        snapshots = aggregator.query_metrics(query)
        
        return {
            "widget_type": "chart",
            "label": self.get_label(),
            "metric_name": self.config.metric_name,
            "chart_type": self.config.chart_type,
            "values": [s.value for s in snapshots],
            "timestamps": [s.timestamp.isoformat() for s in snapshots],
            "data_points": len(snapshots),
        }


class AlertWidget(Widget):
    """
    Show recent alerts filtered by severity
    
    Displays alerts from baseline deviation detection.
    Can filter by severity (INFO/WARNING/CRITICAL) and limit count.
    
    Example Config:
        {
            "widget_type": "alert",
            "label": "Critical Alerts",
            "severity_filter": ["CRITICAL"],
            "limit": 5
        }
    """
    
    def render(self) -> str:
        """Render alerts as text"""
        baseline_mgr = get_baseline_manager()
        
        # For now, we'll check baselines for all metrics
        # In a real implementation, we'd store alerts in a separate table
        baselines = baseline_mgr.get_all_baselines()
        
        if not baselines:
            return f"{self.get_label()}: No alerts"
        
        # Build alert list
        alerts = []
        severity_filter = self.config.severity_filter or ["INFO", "WARNING", "CRITICAL"]
        
        for metric_name, baseline_stats in baselines.items():
            # Check for deviations (simplified - in real impl, use stored alerts)
            aggregator = get_metrics_aggregator()
            query = MetricQuery(
                metric_name=metric_name,
                start_time=datetime.now() - timedelta(hours=1),
            )
            snapshots = aggregator.query_metrics(query)
            
            if snapshots:
                latest = snapshots[-1]
                if baseline_stats.is_above_threshold(latest.value):
                    severity = AlertSeverity.WARNING
                    if severity.name in severity_filter:
                        alerts.append(
                            f"[{severity.name}] {metric_name}: "
                            f"{self.format_value(latest.value)} "
                            f"(baseline: {self.format_value(baseline_stats.median)})"
                        )
        
        # Apply limit
        if self.config.limit:
            alerts = alerts[:self.config.limit]
        
        if not alerts:
            return f"{self.get_label()}: No alerts"
        
        return f"{self.get_label()}\n" + "\n".join(alerts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Export alert data"""
        # Similar to render() but return structured data
        return {
            "widget_type": "alert",
            "label": self.get_label(),
            "severity_filter": self.config.severity_filter,
            "limit": self.config.limit,
            "alerts": [],  # Would contain actual alert objects
        }


class SummaryWidget(Widget):
    """
    Aggregate metrics (sum/avg/count/min/max)
    
    Computes aggregate statistics over multiple metrics or time windows.
    Useful for showing totals, averages, etc.
    
    Example Config:
        {
            "widget_type": "summary",
            "label": "Recording Stats (24h)",
            "metrics": [
                {"name": "recording.count", "agg": "sum"},
                {"name": "recording.duration", "agg": "avg"}
            ],
            "window_hours": 24
        }
    """
    
    def render(self) -> str:
        """Render summary as text"""
        aggregator = get_metrics_aggregator()
        
        # Build query
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=self.config.window_hours or 24)
        
        # Get metrics from config
        metrics = self.config.extra.get("metrics", [])
        if not metrics:
            return f"{self.get_label()}: No metrics configured"
        
        # Build output
        lines = [self.get_label()]
        
        for metric_config in metrics:
            metric_name = metric_config["name"]
            agg_type = metric_config.get("agg", "avg")
            
            query = MetricQuery(
                metric_name=metric_name,
                start_time=start_time,
                end_time=end_time,
                tags=self.config.tags,
            )
            
            snapshots = aggregator.query_metrics(query)
            
            if not snapshots:
                lines.append(f"  {metric_name}: No data")
                continue
            
            values = [s.value for s in snapshots]
            
            # Compute aggregate
            if agg_type == "sum":
                result = sum(values)
            elif agg_type == "avg":
                result = sum(values) / len(values)
            elif agg_type == "count":
                result = len(values)
            elif agg_type == "min":
                result = min(values)
            elif agg_type == "max":
                result = max(values)
            else:
                result = values[-1]  # latest
            
            lines.append(f"  {metric_name} ({agg_type}): {self.format_value(result)}")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """Export summary data"""
        return {
            "widget_type": "summary",
            "label": self.get_label(),
            "window_hours": self.config.window_hours,
            "metrics": self.config.extra.get("metrics", []),
        }


class BaselineWidget(Widget):
    """
    Compare metric to baseline with deviation
    
    Shows current value vs baseline and deviation percentage.
    Highlights values that exceed thresholds.
    
    Example Config:
        {
            "widget_type": "baseline",
            "metric_name": "cpu.usage",
            "label": "CPU Usage vs Baseline",
            "window_hours": 168
        }
    """
    
    def render(self) -> str:
        """Render baseline comparison as text"""
        aggregator = get_metrics_aggregator()
        baseline_mgr = get_baseline_manager()
        
        # Get current value
        query = MetricQuery(
            metric_name=self.config.metric_name,
            start_time=datetime.now() - timedelta(hours=1),
        )
        
        snapshots = aggregator.query_metrics(query)
        
        if not snapshots:
            return f"{self.get_label()}: No data"
        
        current_value = snapshots[-1].value
        
        # Get baseline
        baseline_stats = baseline_mgr.get_baseline(self.config.metric_name)
        
        if not baseline_stats:
            # Calculate baseline if needed
            baseline_stats = baseline_mgr.calculate_baseline(
                self.config.metric_name,
                window_hours=self.config.window_hours or 168,
            )
        
        if not baseline_stats:
            return f"{self.get_label()}: Insufficient baseline data"
        
        # Calculate deviation
        deviation_pct = (
            (current_value - baseline_stats.median) / baseline_stats.median * 100
        ) if baseline_stats.median != 0 else 0
        
        # Build output
        output = f"{self.get_label()}\n"
        output += f"  Current: {self.format_value(current_value)}\n"
        output += f"  Baseline: {self.format_value(baseline_stats.median)}\n"
        output += f"  Deviation: {deviation_pct:+.1f}%"
        
        # Add indicator if threshold exceeded
        if baseline_stats.is_above_threshold(current_value):
            output += " ⚠ ABOVE THRESHOLD"
        elif baseline_stats.is_below_threshold(current_value):
            output += " ⚠ BELOW THRESHOLD"
        
        return output
    
    def to_dict(self) -> Dict[str, Any]:
        """Export baseline comparison data"""
        aggregator = get_metrics_aggregator()
        baseline_mgr = get_baseline_manager()
        
        # Get current value
        query = MetricQuery(
            metric_name=self.config.metric_name,
            start_time=datetime.now() - timedelta(hours=1),
        )
        
        snapshots = aggregator.query_metrics(query)
        current_value = snapshots[-1].value if snapshots else None
        
        # Get baseline
        baseline_stats = baseline_mgr.get_baseline(self.config.metric_name)
        
        return {
            "widget_type": "baseline",
            "label": self.get_label(),
            "metric_name": self.config.metric_name,
            "current_value": current_value,
            "baseline_median": baseline_stats.median if baseline_stats else None,
            "baseline_mad": baseline_stats.mad if baseline_stats else None,
            "deviation_percent": (
                (current_value - baseline_stats.median) / baseline_stats.median * 100
                if baseline_stats and baseline_stats.median != 0 and current_value
                else None
            ),
        }


# Widget factory for dynamic instantiation from config
WIDGET_TYPES = {
    "metric": MetricWidget,
    "chart": ChartWidget,
    "alert": AlertWidget,
    "summary": SummaryWidget,
    "baseline": BaselineWidget,
}


def create_widget(config: WidgetConfig) -> Widget:
    """
    Factory function to create widget from config
    
    Args:
        config: Widget configuration
        
    Returns:
        Widget instance
        
    Raises:
        ValueError: If widget type is unknown
    """
    widget_class = WIDGET_TYPES.get(config.widget_type)
    
    if not widget_class:
        raise ValueError(
            f"Unknown widget type: {config.widget_type}. "
            f"Available types: {', '.join(WIDGET_TYPES.keys())}"
        )
    
    return widget_class(config)
