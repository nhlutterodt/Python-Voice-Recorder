"""
Dashboard Engine

Loads and manages dashboard configurations, instantiates widgets,
and renders complete dashboards using various renderers.

Dashboards are defined via JSON configuration files in config/dashboards/.
This enables users to create custom dashboards without code changes.

Example Dashboard Config (config/dashboards/overview.json):
    {
        "title": "System Overview",
        "description": "General system metrics",
        "widgets": [
            {
                "widget_type": "metric",
                "metric_name": "recording.count",
                "label": "Total Recordings"
            },
            {
                "widget_type": "chart",
                "metric_name": "cpu.usage",
                "label": "CPU Usage (24h)",
                "chart_type": "sparkline",
                "window_hours": 24
            }
        ]
    }

Example Usage:
    from core.dashboard import Dashboard
    
    # Load dashboard from config
    dashboard = Dashboard.from_config("overview")
    
    # Render as text
    print(dashboard.render_text())
    
    # Export as JSON
    json_data = dashboard.render_json()
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from core.dashboard.widget_base import Widget, WidgetConfig
from core.dashboard.widgets import create_widget
from core.dashboard.renderers import (
    Renderer,
    TextRenderer,
    JSONRenderer,
    MarkdownRenderer,
    create_renderer,
)
from core.logging_config import get_logger

logger = get_logger(__name__)


class Dashboard:
    """
    Dashboard Engine
    
    Loads dashboard configurations and renders complete dashboards.
    Dashboards are composed of multiple widgets defined in JSON configs.
    """
    
    def __init__(
        self,
        title: str,
        widgets: List[Widget],
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize dashboard
        
        Args:
            title: Dashboard title
            widgets: List of widget instances
            description: Dashboard description
            metadata: Additional metadata
        """
        self.title = title
        self.widgets = widgets
        self.description = description
        self.metadata = metadata or {}
        
        logger.debug(
            f"Dashboard created: {title}",
            extra={"widget_count": len(widgets)}
        )
    
    @classmethod
    def from_config(
        cls,
        config_name: str,
        config_dir: Optional[Path] = None,
    ) -> "Dashboard":
        """
        Load dashboard from configuration file
        
        Args:
            config_name: Name of config file (without .json extension)
            config_dir: Directory containing config files (default: config/dashboards/)
            
        Returns:
            Dashboard instance
            
        Raises:
            FileNotFoundError: If config file not found
            ValueError: If config is invalid
        """
        # Determine config directory
        if config_dir is None:
            # Default to config/dashboards/ relative to this file's location
            config_dir = Path(__file__).parent.parent.parent / "config" / "dashboards"
        
        config_path = config_dir / f"{config_name}.json"
        
        if not config_path.exists():
            raise FileNotFoundError(
                f"Dashboard config not found: {config_path}\n"
                f"Available configs should be in: {config_dir}"
            )
        
        # Load config
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in dashboard config: {e}")
        
        # Parse config
        title = config.get("title", config_name)
        description = config.get("description", "")
        
        # Create widgets
        widgets = []
        for widget_config_dict in config.get("widgets", []):
            try:
                widget_config = WidgetConfig.from_dict(widget_config_dict)
                widget = create_widget(widget_config)
                widgets.append(widget)
            except Exception as e:
                logger.warning(
                    f"Failed to create widget: {e}",
                    extra={"widget_config": widget_config_dict}
                )
                # Continue with other widgets
        
        # Extract metadata
        metadata = {
            "config_name": config_name,
            "config_path": str(config_path),
            "description": description,
        }
        
        # Add any custom metadata from config
        for key, value in config.items():
            if key not in ["title", "description", "widgets"]:
                metadata[key] = value
        
        return cls(
            title=title,
            widgets=widgets,
            description=description,
            metadata=metadata,
        )
    
    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> "Dashboard":
        """
        Create dashboard from dictionary
        
        Args:
            config: Dashboard configuration dictionary
            
        Returns:
            Dashboard instance
        """
        title = config.get("title", "Dashboard")
        description = config.get("description", "")
        
        # Create widgets
        widgets = []
        for widget_config_dict in config.get("widgets", []):
            widget_config = WidgetConfig.from_dict(widget_config_dict)
            widget = create_widget(widget_config)
            widgets.append(widget)
        
        return cls(
            title=title,
            widgets=widgets,
            description=description,
            metadata=config.get("metadata", {}),
        )
    
    def render(self, renderer: Renderer) -> str:
        """
        Render dashboard using specified renderer
        
        Args:
            renderer: Renderer instance
            
        Returns:
            Rendered output (format depends on renderer)
        """
        return renderer.render_dashboard(
            title=self.title,
            widgets=self.widgets,
            metadata={
                "description": self.description,
                **self.metadata,
            },
        )
    
    def render_text(self, width: int = 80) -> str:
        """
        Render dashboard as text (CLI output)
        
        Args:
            width: Maximum line width
            
        Returns:
            Text representation of dashboard
        """
        renderer = TextRenderer(width=width)
        return self.render(renderer)
    
    def render_json(self, pretty: bool = True) -> str:
        """
        Render dashboard as JSON
        
        Args:
            pretty: Whether to pretty-print JSON
            
        Returns:
            JSON representation of dashboard
        """
        renderer = JSONRenderer(pretty=pretty)
        return self.render(renderer)
    
    def render_markdown(self) -> str:
        """
        Render dashboard as Markdown
        
        Returns:
            Markdown representation of dashboard
        """
        renderer = MarkdownRenderer()
        return self.render(renderer)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Export dashboard configuration
        
        Returns:
            Dashboard configuration as dictionary
        """
        return {
            "title": self.title,
            "description": self.description,
            "widgets": [w.config.to_dict() for w in self.widgets],
            "metadata": self.metadata,
        }
    
    @staticmethod
    def list_available_configs(config_dir: Optional[Path] = None) -> List[str]:
        """
        List available dashboard configurations
        
        Args:
            config_dir: Directory containing config files
            
        Returns:
            List of available config names (without .json extension)
        """
        if config_dir is None:
            config_dir = Path(__file__).parent.parent.parent / "config" / "dashboards"
        
        if not config_dir.exists():
            return []
        
        # Find all .json files
        configs = []
        for config_file in config_dir.glob("*.json"):
            configs.append(config_file.stem)
        
        return sorted(configs)
    
    def __repr__(self) -> str:
        """String representation for debugging"""
        return f"Dashboard(title={self.title}, widgets={len(self.widgets)})"


# Convenience function for quick dashboard rendering
def render_dashboard(
    config_name: str,
    renderer_type: str = "text",
    **renderer_kwargs,
) -> str:
    """
    Quick render dashboard from config name
    
    Args:
        config_name: Name of dashboard config
        renderer_type: Type of renderer ("text", "json", "markdown")
        **renderer_kwargs: Additional renderer arguments
        
    Returns:
        Rendered dashboard output
    """
    dashboard = Dashboard.from_config(config_name)
    renderer = create_renderer(renderer_type, **renderer_kwargs)
    return dashboard.render(renderer)
