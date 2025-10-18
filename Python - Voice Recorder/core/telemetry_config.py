#!/usr/bin/env python3
"""
Telemetry configuration for Voice Recorder Pro
Manages Sentry SDK initialization with privacy-first approach.
"""
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

from core.pii_filter import filter_event

logger = logging.getLogger(__name__)


class TelemetryConfig:
    """
    Manages Sentry telemetry configuration with opt-in privacy controls
    """
    
    def __init__(
        self,
        dsn: Optional[str] = None,
        environment: Optional[str] = None,
        release: Optional[str] = None,
        enabled: bool = False
    ):
        """
        Initialize telemetry configuration
        
        Args:
            dsn: Sentry DSN (Data Source Name)
            environment: Environment name (dev/staging/production)
            release: Release version string
            enabled: Whether telemetry is enabled (opt-in, default False)
        """
        self.dsn = dsn or os.getenv('SENTRY_DSN', '')
        self.environment = environment or self._detect_environment()
        self.release = release or self._get_release_version()
        self.enabled = enabled
        self._initialized = False
    
    def _detect_environment(self) -> str:
        """
        Detect current environment
        
        Returns:
            Environment string (development/staging/production)
        """
        # Check environment variable first
        env = os.getenv('ENVIRONMENT', '').lower()
        if env in ('development', 'staging', 'production'):
            return env
        
        # Check if running from frozen executable (PyInstaller)
        if getattr(sys, 'frozen', False):
            return 'production'
        
        # Check for common dev indicators
        if any(indicator in sys.argv[0].lower() for indicator in ('test', 'pytest', 'dev')):
            return 'development'
        
        # Default to development
        return 'development'
    
    def _get_release_version(self) -> str:
        """
        Get release version from build_info.json or VERSION file
        
        Returns:
            Version string
        """
        try:
            import json
            build_info_path = Path(__file__).parent.parent / 'build_info.json'
            if build_info_path.exists():
                with open(build_info_path, 'r', encoding='utf-8') as f:
                    build_info = json.load(f)
                    return build_info.get('version', 'unknown')
        except Exception as e:
            logger.debug(f"Could not read build_info.json: {e}")
        
        # Fallback to VERSION file
        try:
            version_path = Path(__file__).parent.parent / 'VERSION'
            if version_path.exists():
                return version_path.read_text().strip()
        except Exception as e:
            logger.debug(f"Could not read VERSION file: {e}")
        
        return 'unknown'
    
    def initialize(self) -> bool:
        """
        Initialize Sentry SDK with current configuration
        
        Returns:
            True if initialization succeeded, False otherwise
        """
        if self._initialized:
            logger.debug("Sentry already initialized")
            return True
        
        if not self.enabled:
            logger.info("Telemetry is disabled (opt-in required)")
            return False
        
        if not self.dsn:
            logger.warning("Cannot initialize telemetry: DSN not configured")
            return False
        
        try:
            # Configure logging integration
            logging_integration = LoggingIntegration(
                level=logging.INFO,        # Capture info and above as breadcrumbs
                event_level=logging.ERROR  # Send errors as events
            )
            
            # Initialize Sentry
            sentry_sdk.init(
                dsn=self.dsn,
                environment=self.environment,
                release=self.release,
                integrations=[logging_integration],
                before_send=filter_event,  # Apply PII filtering
                traces_sample_rate=self._get_traces_sample_rate(),
                profiles_sample_rate=self._get_profiles_sample_rate(),
                send_default_pii=False,  # Never send PII by default
                attach_stacktrace=True,  # Include stack traces in messages
                max_breadcrumbs=50,      # Limit breadcrumb history
                debug=self.environment == 'development'  # Debug mode in dev
            )
            
            self._initialized = True
            logger.info(f"Sentry initialized: environment={self.environment}, release={self.release}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Sentry: {e}", exc_info=True)
            return False
    
    def _get_traces_sample_rate(self) -> float:
        """
        Get traces sample rate based on environment
        
        Returns:
            Sample rate (0.0 to 1.0)
        """
        if self.environment == 'production':
            return 0.1  # 10% sampling in production
        elif self.environment == 'staging':
            return 0.5  # 50% sampling in staging
        else:
            return 1.0  # 100% sampling in development
    
    def _get_profiles_sample_rate(self) -> float:
        """
        Get profiles sample rate based on environment
        
        Returns:
            Sample rate (0.0 to 1.0)
        """
        # Profile sampling only in staging/production
        if self.environment == 'production':
            return 0.01  # 1% profiling in production
        elif self.environment == 'staging':
            return 0.1   # 10% profiling in staging
        else:
            return 0.0   # No profiling in development
    
    def shutdown(self, timeout: int = 2) -> None:
        """
        Shutdown Sentry SDK gracefully
        
        Args:
            timeout: Timeout in seconds
        """
        if self._initialized:
            try:
                client = sentry_sdk.Hub.current.client
                if client:
                    client.close(timeout=timeout)
                logger.info("Sentry shut down gracefully")
            except Exception as e:
                logger.error(f"Error shutting down Sentry: {e}")
            finally:
                self._initialized = False
    
    def set_user_context(self, user_id: str = "anonymous") -> None:
        """
        Set user context (anonymous by default)
        
        Args:
            user_id: User identifier (should be anonymous session ID)
        """
        if self._initialized:
            sentry_sdk.set_user({"id": user_id})
    
    def set_tag(self, key: str, value: str) -> None:
        """
        Set a tag for the current scope
        
        Args:
            key: Tag key
            value: Tag value
        """
        if self._initialized:
            sentry_sdk.set_tag(key, value)
    
    def set_context(self, name: str, context: Dict[str, Any]) -> None:
        """
        Set custom context
        
        Args:
            name: Context name
            context: Context data (will be PII filtered)
        """
        if self._initialized:
            from core.pii_filter import get_pii_filter
            filtered_context = get_pii_filter().filter_dict(context)
            sentry_sdk.set_context(name, filtered_context)
    
    def capture_exception(self, exception: Exception) -> Optional[str]:
        """
        Capture an exception
        
        Args:
            exception: Exception to capture
        
        Returns:
            Event ID if captured, None otherwise
        """
        if self._initialized:
            return sentry_sdk.capture_exception(exception)
        return None
    
    def capture_message(self, message: str, level: str = 'info') -> Optional[str]:
        """
        Capture a message
        
        Args:
            message: Message to capture
            level: Log level (debug/info/warning/error/fatal)
        
        Returns:
            Event ID if captured, None otherwise
        """
        if self._initialized:
            from core.pii_filter import get_pii_filter
            filtered_message = get_pii_filter().filter_string(message)
            return sentry_sdk.capture_message(filtered_message, level=level)
        return None


# Global telemetry config instance
_telemetry_config: Optional[TelemetryConfig] = None


def get_telemetry_config() -> TelemetryConfig:
    """
    Get or create global telemetry config instance
    
    Returns:
        TelemetryConfig instance
    """
    global _telemetry_config
    if _telemetry_config is None:
        _telemetry_config = TelemetryConfig()
    return _telemetry_config


def initialize_telemetry(
    dsn: Optional[str] = None,
    environment: Optional[str] = None,
    release: Optional[str] = None,
    enabled: bool = False
) -> bool:
    """
    Initialize global telemetry configuration
    
    Args:
        dsn: Sentry DSN
        environment: Environment name
        release: Release version
        enabled: Whether telemetry is enabled
    
    Returns:
        True if initialization succeeded
    """
    config = get_telemetry_config()
    
    # Update configuration
    if dsn is not None:
        config.dsn = dsn
    if environment is not None:
        config.environment = environment
    if release is not None:
        config.release = release
    config.enabled = enabled
    
    return config.initialize()


def shutdown_telemetry(timeout: int = 2) -> None:
    """
    Shutdown global telemetry configuration
    
    Args:
        timeout: Timeout in seconds
    """
    config = get_telemetry_config()
    config.shutdown(timeout=timeout)
