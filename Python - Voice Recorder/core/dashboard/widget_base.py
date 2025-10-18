"""
Widget Base Classes for Dashboard Framework

Provides abstract base class and configuration schema for dashboard widgets.
All widgets inherit from Widget and implement render() method.

Widgets are config-driven - behavior defined by JSON configuration rather
than hardcoded parameters. This enables users to create custom dashboards
without code changes.

Example Widget Config (JSON):
    {
        "type": "metric",
        "metric_name": "recording.count",
        "label": "Total Recordings",
        "format": "number"
    }

Example Usage:
    from core.dashboard.widgets import MetricWidget
    
    config = WidgetConfig(
        widget_type="metric",
        metric_name="recording.count",
        label="Total Recordings"
    )
    
    widget = MetricWidget(config)
    print(widget.render())  # "Total Recordings: 42"
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime

from core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class WidgetConfig:
    """
    Configuration for a dashboard widget
    
    All widgets accept a config object that defines their behavior.
    This allows dashboards to be defined via JSON without code changes.
    """
    widget_type: str  # Type of widget: "metric", "chart", "alert", "summary"
    
    # Common properties
    label: Optional[str] = None
    description: Optional[str] = None
    
    # Metric-specific
    metric_name: Optional[str] = None
    metric_type: Optional[str] = None
    
    # Time range
    window_hours: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Display options
    format: str = "auto"  # "number", "percent", "duration", "bytes", "auto"
    decimals: int = 2
    show_trend: bool = False
    
    # Chart options
    chart_type: Optional[str] = None  # "sparkline", "bar", "line"
    chart_height: int = 5
    chart_width: int = 40
    
    # Alert options
    severity_filter: Optional[List[str]] = None  # ["WARNING", "CRITICAL"]
    limit: Optional[int] = None
    
    # Tags for filtering
    tags: Optional[Dict[str, str]] = None
    
    # Additional custom properties
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        return {
            "widget_type": self.widget_type,
            "label": self.label,
            "description": self.description,
            "metric_name": self.metric_name,
            "metric_type": self.metric_type,
            "window_hours": self.window_hours,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "format": self.format,
            "decimals": self.decimals,
            "show_trend": self.show_trend,
            "chart_type": self.chart_type,
            "chart_height": self.chart_height,
            "chart_width": self.chart_width,
            "severity_filter": self.severity_filter,
            "limit": self.limit,
            "tags": self.tags,
            "extra": self.extra,
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "WidgetConfig":
        """Create from dictionary (JSON config)"""
        start_time = None
        if data.get("start_time"):
            start_time = datetime.fromisoformat(data["start_time"])
        
        end_time = None
        if data.get("end_time"):
            end_time = datetime.fromisoformat(data["end_time"])
        
        return WidgetConfig(
            widget_type=data["widget_type"],
            label=data.get("label"),
            description=data.get("description"),
            metric_name=data.get("metric_name"),
            metric_type=data.get("metric_type"),
            window_hours=data.get("window_hours"),
            start_time=start_time,
            end_time=end_time,
            format=data.get("format", "auto"),
            decimals=data.get("decimals", 2),
            show_trend=data.get("show_trend", False),
            chart_type=data.get("chart_type"),
            chart_height=data.get("chart_height", 5),
            chart_width=data.get("chart_width", 40),
            severity_filter=data.get("severity_filter"),
            limit=data.get("limit"),
            tags=data.get("tags"),
            extra=data.get("extra", {}),
        )


class Widget(ABC):
    """
    Abstract base class for all dashboard widgets
    
    Widgets are the building blocks of dashboards. Each widget:
    - Accepts a WidgetConfig defining its behavior
    - Implements render() to produce text output
    - Implements to_dict() to export data (JSON/API)
    
    Subclasses must implement:
    - render() -> str: Render widget as text
    - to_dict() -> Dict: Export widget data
    """
    
    def __init__(self, config: WidgetConfig):
        """
        Initialize widget with configuration
        
        Args:
            config: Widget configuration object
        """
        self.config = config
        logger.debug(
            f"Widget created: {config.widget_type}",
            extra={"label": config.label}
        )
    
    @abstractmethod
    def render(self) -> str:
        """
        Render widget as text (for CLI/terminal display)
        
        Returns:
            Formatted text representation of widget
        """
        pass
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """
        Export widget data as dictionary (for JSON/API)
        
        Returns:
            Dictionary with widget data and metadata
        """
        pass
    
    def get_label(self) -> str:
        """
        Get widget label for display
        
        Returns:
            Widget label or auto-generated label
        """
        if self.config.label:
            return self.config.label
        
        # Auto-generate label from metric name
        if self.config.metric_name:
            # Convert "recording.count" -> "Recording Count"
            parts = self.config.metric_name.split(".")
            return " ".join(p.capitalize() for p in parts)
        
        return f"{self.config.widget_type.capitalize()} Widget"
    
    def format_value(self, value: float) -> str:
        """
        Format numeric value according to widget config
        
        Args:
            value: Numeric value to format
            
        Returns:
            Formatted string
        """
        fmt = self.config.format
        decimals = self.config.decimals
        
        if fmt == "percent":
            return f"{value:.{decimals}f}%"
        elif fmt == "duration":
            # Format as HH:MM:SS
            hours = int(value // 3600)
            minutes = int((value % 3600) // 60)
            seconds = int(value % 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        elif fmt == "bytes":
            # Format as human-readable bytes
            for unit in ["B", "KB", "MB", "GB", "TB"]:
                if value < 1024.0:
                    return f"{value:.{decimals}f} {unit}"
                value /= 1024.0
            return f"{value:.{decimals}f} PB"
        elif fmt == "number":
            return f"{value:,.{decimals}f}"
        else:  # "auto"
            # Auto-detect format
            if value >= 1_000_000:
                return f"{value:,.{decimals}f}"
            elif value >= 1000:
                return f"{value:,.{decimals}f}"
            else:
                return f"{value:.{decimals}f}"
    
    def __repr__(self) -> str:
        """String representation for debugging"""
        return f"{self.__class__.__name__}(type={self.config.widget_type}, label={self.get_label()})"
