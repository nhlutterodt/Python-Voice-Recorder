"""
Access Control for Dashboard Features

Provides simple, config-based access control to protect dashboard features
from casual users while allowing authorized access without password friction.

Security Model:
- Default: DENY (dashboards hidden)
- Enable via: Environment variable OR config file
- Protection: Obscurity-based (suitable for single-user desktop app)
- Future: Can add password/OAuth when multi-user deployment emerges

Privacy Note: This protects system internals from accidental exposure/changes,
not a security boundary against malicious actors. For true security, see
multi-user authentication options in TASK20_DAY4_DASHBOARD_SECURITY_ANALYSIS.md

Example Usage:
    # Check if dashboard features should be available
    access = DashboardAccessControl()
    if access.is_enabled():
        # Show dashboard menu/features
        pass
    
    # Get detailed access check with reason
    allowed, reason = access.check_access()
    if not allowed:
        logger.info(f"Dashboard access denied: {reason}")
"""

import os
import json
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass

from core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class DashboardConfig:
    """Dashboard configuration from settings file"""
    enabled: bool = False
    require_confirmation: bool = True
    description: str = "System metrics and diagnostics"


class DashboardAccessControl:
    """
    Simple access control for dashboard features.
    
    Checks access in priority order:
    1. Environment variable VRP_ADMIN_MODE (developer override)
    2. Configuration file setting (persistent enable)
    3. Default: DENY (hidden/disabled)
    
    This provides protection against casual users on shared computers
    while allowing authorized users to enable features via config file.
    """
    
    ENV_VAR = "VRP_ADMIN_MODE"
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize access control
        
        Args:
            config_path: Path to settings.json (default: config/settings.json)
        """
        if config_path is None:
            config_path = Path("config/settings.json")
        
        self.config_path = config_path
        self._config: Optional[DashboardConfig] = None
        self._load_config()
    
    def _load_config(self) -> None:
        """Load dashboard configuration from file"""
        try:
            if not self.config_path.exists():
                logger.debug(f"Config file not found: {self.config_path}")
                self._config = DashboardConfig()
                return
            
            with open(self.config_path) as f:
                data = json.load(f)
            
            dashboard_data = data.get("dashboard", {})
            self._config = DashboardConfig(
                enabled=dashboard_data.get("enabled", False),
                require_confirmation=dashboard_data.get("require_confirmation", True),
                description=dashboard_data.get("description", "System metrics and diagnostics"),
            )
            
            logger.debug(
                f"Dashboard config loaded: enabled={self._config.enabled}",
                extra={"config_path": str(self.config_path)}
            )
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse config file: {e}")
            self._config = DashboardConfig()
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")
            self._config = DashboardConfig()
    
    def is_enabled(self) -> bool:
        """
        Check if dashboard features are enabled
        
        Returns:
            True if dashboards should be available, False otherwise
        """
        # Priority 1: Environment variable (developer/power-user override)
        env_value = os.getenv(self.ENV_VAR, "").lower()
        if env_value in ("true", "1", "yes", "on"):
            logger.debug(f"Dashboard enabled via {self.ENV_VAR} environment variable")
            return True
        
        # Priority 2: Config file setting
        if self._config and self._config.enabled:
            logger.debug("Dashboard enabled via config file")
            return True
        
        # Default: DENY
        logger.debug("Dashboard disabled (default)")
        return False
    
    def requires_confirmation(self) -> bool:
        """
        Check if user confirmation is required before showing dashboard
        
        Returns:
            True if confirmation dialog should be shown
        """
        # Environment variable bypasses confirmation (developer mode)
        env_value = os.getenv(self.ENV_VAR, "").lower()
        if env_value in ("true", "1", "yes", "on"):
            return False
        
        # Otherwise check config
        return self._config.require_confirmation if self._config else True
    
    def get_description(self) -> str:
        """
        Get dashboard description for display
        
        Returns:
            Human-readable description of dashboard features
        """
        return self._config.description if self._config else "System metrics and diagnostics"
    
    def check_access(self) -> Tuple[bool, Optional[str]]:
        """
        Check dashboard access with detailed reason
        
        Returns:
            Tuple of (allowed: bool, reason: Optional[str])
            - allowed: True if access granted
            - reason: Explanation if access denied, None if allowed
        """
        if not self.is_enabled():
            return (
                False,
                f"Dashboard is not enabled. Set {self.ENV_VAR}=true environment variable "
                f"or enable in {self.config_path} to access dashboard features."
            )
        
        return (True, None)
    
    def get_enable_instructions(self) -> str:
        """
        Get instructions for enabling dashboard access
        
        Returns:
            Multi-line string with enable instructions
        """
        return f"""
Dashboard Access Instructions:

Option 1: Enable for current session (developer mode)
  Windows: set {self.ENV_VAR}=true
  Linux/Mac: export {self.ENV_VAR}=true
  
Option 2: Enable permanently (edit config file)
  1. Open: {self.config_path}
  2. Set: "dashboard": {{"enabled": true}}
  3. Restart application

Note: Dashboards show system metrics and diagnostics.
Protected by default to prevent accidental changes.
"""


def is_dashboard_enabled() -> bool:
    """
    Convenience function to check if dashboards are enabled
    
    Returns:
        True if dashboard access is allowed
    """
    access = DashboardAccessControl()
    return access.is_enabled()


def check_dashboard_access() -> Tuple[bool, Optional[str]]:
    """
    Convenience function to check dashboard access with reason
    
    Returns:
        Tuple of (allowed: bool, reason: Optional[str])
    """
    access = DashboardAccessControl()
    return access.check_access()
