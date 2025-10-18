"""
Dashboard Rendering

Renders dashboards to different output formats (text, JSON, etc.).

Renderers transform widget output into specific formats:
- TextRenderer: CLI/terminal text output
- JSONRenderer: JSON export for APIs/GUIs
- Future: HTMLRenderer, GUIRenderer

Example Usage:
    from core.dashboard.renderers import TextRenderer
    from core.dashboard.widgets import MetricWidget
    from core.dashboard.widget_base import WidgetConfig
    
    widget = MetricWidget(WidgetConfig(
        widget_type="metric",
        metric_name="recording.count"
    ))
    
    renderer = TextRenderer()
    output = renderer.render_widget(widget)
    print(output)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from datetime import datetime

from core.dashboard.widget_base import Widget
from core.logging_config import get_logger

logger = get_logger(__name__)


class Renderer(ABC):
    """
    Abstract base class for dashboard renderers
    
    Renderers transform widgets into specific output formats.
    """
    
    @abstractmethod
    def render_widget(self, widget: Widget) -> str:
        """Render single widget"""
        pass
    
    @abstractmethod
    def render_dashboard(
        self,
        title: str,
        widgets: List[Widget],
        metadata: Dict[str, Any],
    ) -> str:
        """Render complete dashboard"""
        pass


class TextRenderer(Renderer):
    """
    Render dashboard as plain text (for CLI/terminal)
    
    Produces human-readable text output suitable for terminal display.
    Uses box-drawing characters for visual separation.
    """
    
    def __init__(self, width: int = 80):
        """
        Initialize text renderer
        
        Args:
            width: Maximum line width for output
        """
        self.width = width
    
    def render_widget(self, widget: Widget) -> str:
        """Render single widget as text"""
        return widget.render()
    
    def render_dashboard(
        self,
        title: str,
        widgets: List[Widget],
        metadata: Dict[str, Any],
    ) -> str:
        """Render complete dashboard as text"""
        lines = []
        
        # Header
        lines.append("═" * self.width)
        lines.append(title.center(self.width))
        
        # Metadata
        if metadata.get("description"):
            lines.append(metadata["description"].center(self.width))
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"Generated: {timestamp}".center(self.width))
        lines.append("═" * self.width)
        lines.append("")
        
        # Widgets
        for i, widget in enumerate(widgets):
            # Render widget
            widget_output = self.render_widget(widget)
            lines.append(widget_output)
            
            # Separator between widgets
            if i < len(widgets) - 1:
                lines.append("")
                lines.append("─" * self.width)
                lines.append("")
        
        # Footer
        lines.append("")
        lines.append("═" * self.width)
        lines.append(f"Total Widgets: {len(widgets)}".center(self.width))
        lines.append("═" * self.width)
        
        return "\n".join(lines)


class JSONRenderer(Renderer):
    """
    Render dashboard as JSON (for APIs/GUIs)
    
    Produces structured JSON output suitable for:
    - API responses
    - GUI consumption
    - Data export
    - Integration with other tools
    """
    
    def __init__(self, pretty: bool = True):
        """
        Initialize JSON renderer
        
        Args:
            pretty: Whether to pretty-print JSON
        """
        self.pretty = pretty
    
    def render_widget(self, widget: Widget) -> str:
        """Render single widget as JSON string"""
        import json
        
        data = widget.to_dict()
        
        if self.pretty:
            return json.dumps(data, indent=2)
        else:
            return json.dumps(data)
    
    def render_dashboard(
        self,
        title: str,
        widgets: List[Widget],
        metadata: Dict[str, Any],
    ) -> str:
        """Render complete dashboard as JSON string"""
        import json
        
        # Build dashboard data
        dashboard_data = {
            "title": title,
            "description": metadata.get("description", ""),
            "generated_at": datetime.now().isoformat(),
            "widget_count": len(widgets),
            "widgets": [widget.to_dict() for widget in widgets],
            "metadata": metadata,
        }
        
        if self.pretty:
            return json.dumps(dashboard_data, indent=2)
        else:
            return json.dumps(dashboard_data)


class MarkdownRenderer(Renderer):
    """
    Render dashboard as Markdown (for documentation/reports)
    
    Produces Markdown output suitable for:
    - Documentation
    - Reports
    - GitHub/GitLab integration
    - Static site generation
    """
    
    def render_widget(self, widget: Widget) -> str:
        """Render single widget as Markdown"""
        output = widget.render()
        
        # Wrap in code block if it's a chart
        if widget.config.widget_type == "chart":
            return f"```\n{output}\n```"
        
        return output
    
    def render_dashboard(
        self,
        title: str,
        widgets: List[Widget],
        metadata: Dict[str, Any],
    ) -> str:
        """Render complete dashboard as Markdown"""
        lines = []
        
        # Header
        lines.append(f"# {title}")
        lines.append("")
        
        # Metadata
        if metadata.get("description"):
            lines.append(f"> {metadata['description']}")
            lines.append("")
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"**Generated:** {timestamp}")
        lines.append("")
        
        lines.append("---")
        lines.append("")
        
        # Widgets
        for widget in widgets:
            # Widget header
            lines.append(f"## {widget.get_label()}")
            lines.append("")
            
            # Widget content
            widget_output = self.render_widget(widget)
            lines.append(widget_output)
            lines.append("")
        
        # Footer
        lines.append("---")
        lines.append("")
        lines.append(f"*Total Widgets: {len(widgets)}*")
        
        return "\n".join(lines)


# Renderer factory
RENDERER_TYPES = {
    "text": TextRenderer,
    "json": JSONRenderer,
    "markdown": MarkdownRenderer,
}


def create_renderer(renderer_type: str, **kwargs) -> Renderer:
    """
    Factory function to create renderer
    
    Args:
        renderer_type: Type of renderer ("text", "json", "markdown")
        **kwargs: Additional arguments for renderer
        
    Returns:
        Renderer instance
        
    Raises:
        ValueError: If renderer type is unknown
    """
    renderer_class = RENDERER_TYPES.get(renderer_type)
    
    if not renderer_class:
        raise ValueError(
            f"Unknown renderer type: {renderer_type}. "
            f"Available types: {', '.join(RENDERER_TYPES.keys())}"
        )
    
    return renderer_class(**kwargs)
