"""
Dashboard Framework for Voice Recorder Pro

Privacy-first metrics visualization with config-driven widgets and
access control for protecting system internals from accidental changes.

Key Features:
- Config-driven dashboard definitions (JSON)
- Reusable widget components
- Multiple renderers (CLI, JSON, future: HTML/GUI)
- Access control via config/environment variables
- No PII - aggregated metrics only

Example Usage:
    from core.dashboard import Dashboard, DashboardAccessControl
    
    # Check access
    access = DashboardAccessControl()
    if access.is_enabled():
        # Load and display dashboard
        dashboard = Dashboard.from_config("overview")
        print(dashboard.render_text())
"""

from .access_control import DashboardAccessControl
from .widget_base import Widget, WidgetConfig
from .widgets import (
    MetricWidget,
    ChartWidget,
    AlertWidget,
    SummaryWidget,
    BaselineWidget,
    create_widget,
)
from .dashboard import Dashboard, render_dashboard
from .renderers import (
    Renderer,
    TextRenderer,
    JSONRenderer,
    MarkdownRenderer,
    create_renderer,
)

__all__ = [
    "DashboardAccessControl",
    "Widget",
    "WidgetConfig",
    "MetricWidget",
    "ChartWidget",
    "AlertWidget",
    "SummaryWidget",
    "BaselineWidget",
    "create_widget",
    "Dashboard",
    "render_dashboard",
    "Renderer",
    "TextRenderer",
    "JSONRenderer",
    "MarkdownRenderer",
    "create_renderer",
]
