#!/usr/bin/env python3
"""
PII (Personally Identifiable Information) filter for Voice Recorder Pro
Scrubs sensitive data before sending to telemetry services.
"""
import re
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse


class PIIFilter:
    """
    Filter that removes or redacts PII from data before sending to telemetry
    """
    
    # Patterns for PII detection
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    IP_PATTERN = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
    PATH_PATTERN = re.compile(r'[A-Za-z]:\\(?:[^\\/:*?"<>|\r\n]+\\)*[^\\/:*?"<>|\r\n]*|/(?:[^/\0]+/)*[^/\0]*')
    
    # Fields that are safe to send
    ALLOWLIST_FIELDS = {
        'event_type', 'category', 'level', 'message',
        'duration_seconds', 'duration_ms',
        'current_mb', 'peak_mb', 'current_bytes', 'peak_bytes',
        'operation', 'function',
        'timestamp', 'session_id', 'request_id',
        'version', 'environment', 'platform'
    }
    
    # Fields that should be completely removed
    BLOCKLIST_FIELDS = {
        'password', 'token', 'api_key', 'secret',
        'auth', 'credential', 'private_key'
    }
    
    def __init__(self, scrub_paths: bool = True, allowlist_only: bool = True):
        """
        Initialize PII filter
        
        Args:
            scrub_paths: Whether to scrub file paths (keep only filename)
            allowlist_only: Only allow explicitly whitelisted fields
        """
        self.scrub_paths = scrub_paths
        self.allowlist_only = allowlist_only
    
    def filter_string(self, text: str) -> str:
        """
        Filter PII from a string
        
        Args:
            text: Input string
        
        Returns:
            Filtered string with PII redacted
        """
        if not isinstance(text, str):
            return text
        
        # Filter emails
        text = self.EMAIL_PATTERN.sub('[EMAIL]', text)
        
        # Filter IP addresses
        text = self.IP_PATTERN.sub('[IP]', text)
        
        # Filter file paths
        if self.scrub_paths:
            text = self._scrub_path(text)
        
        return text
    
    def _scrub_path(self, text: str) -> str:
        """
        Scrub file paths from text, keeping only filename
        
        Args:
            text: Input text
        
        Returns:
            Text with paths replaced by filenames only
        """
        def replace_path(match: re.Match) -> str:
            path_str = match.group(0)
            try:
                path = Path(path_str)
                # Return just the filename, or '[PATH]' if no name
                return path.name if path.name else '[PATH]'
            except (ValueError, OSError):
                return '[PATH]'
        
        return self.PATH_PATTERN.sub(replace_path, text)
    
    def filter_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter PII from a dictionary
        
        Args:
            data: Input dictionary
        
        Returns:
            Filtered dictionary with PII removed/redacted
        """
        if not isinstance(data, dict):
            return data
        
        filtered = {}
        
        for key, value in data.items():
            # Skip blocklisted fields entirely
            if key.lower() in self.BLOCKLIST_FIELDS:
                continue
            
            # If allowlist mode, skip non-allowlisted fields
            if self.allowlist_only and key not in self.ALLOWLIST_FIELDS:
                continue
            
            # Recursively filter values
            if isinstance(value, dict):
                filtered[key] = self.filter_dict(value)
            elif isinstance(value, list):
                filtered[key] = [self.filter_value(item) for item in value]
            elif isinstance(value, str):
                filtered[key] = self.filter_string(value)
            else:
                filtered[key] = value
        
        return filtered
    
    def filter_value(self, value: Any) -> Any:
        """
        Filter PII from any value type
        
        Args:
            value: Input value
        
        Returns:
            Filtered value
        """
        if isinstance(value, dict):
            return self.filter_dict(value)
        elif isinstance(value, str):
            return self.filter_string(value)
        elif isinstance(value, list):
            return [self.filter_value(item) for item in value]
        else:
            return value
    
    def filter_exception(self, exc_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter PII from exception information
        
        Args:
            exc_info: Exception info dict
        
        Returns:
            Filtered exception info
        """
        if not isinstance(exc_info, dict):
            return exc_info
        
        filtered = exc_info.copy()
        
        # Filter exception message
        if 'message' in filtered:
            filtered['message'] = self.filter_string(str(filtered['message']))
        
        # Filter exception value (similar to message)
        if 'value' in filtered:
            filtered['value'] = self.filter_string(str(filtered['value']))
        
        # Filter exception type (keep it, it's not PII)
        # filtered['type'] is safe
        
        # Filter stack trace
        if 'stacktrace' in filtered and isinstance(filtered['stacktrace'], dict):
            filtered['stacktrace'] = self._filter_stacktrace(filtered['stacktrace'])
        
        # Filter values in exception
        if 'values' in filtered and isinstance(filtered['values'], list):
            filtered['values'] = [self.filter_exception(v) for v in filtered['values']]
        
        return filtered
    
    def _filter_stacktrace(self, stacktrace: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter PII from stack trace
        
        Args:
            stacktrace: Stack trace dict
        
        Returns:
            Filtered stack trace
        """
        if not isinstance(stacktrace, dict):
            return stacktrace
        
        filtered = stacktrace.copy()
        
        # Filter frames
        if 'frames' in filtered and isinstance(filtered['frames'], list):
            filtered['frames'] = [self._filter_frame(frame) for frame in filtered['frames']]
        
        return filtered
    
    def _filter_frame(self, frame: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter PII from a stack frame
        
        Args:
            frame: Stack frame dict
        
        Returns:
            Filtered stack frame
        """
        if not isinstance(frame, dict):
            return frame
        
        filtered = frame.copy()
        
        # Filter filename (keep only basename)
        if 'filename' in filtered and self.scrub_paths:
            filtered['filename'] = Path(filtered['filename']).name
        
        # Filter abs_path (keep only basename)
        if 'abs_path' in filtered and self.scrub_paths:
            filtered['abs_path'] = Path(filtered['abs_path']).name
        
        # Filter local variables (remove them entirely for privacy)
        if 'vars' in filtered:
            del filtered['vars']
        
        return filtered
    
    def filter_breadcrumbs(self, breadcrumbs: list) -> list:
        """
        Filter PII from breadcrumbs
        
        Args:
            breadcrumbs: List of breadcrumb dicts
        
        Returns:
            Filtered breadcrumbs
        """
        if not isinstance(breadcrumbs, list):
            return breadcrumbs
        
        return [self._filter_breadcrumb(bc) for bc in breadcrumbs]
    
    def _filter_breadcrumb(self, breadcrumb: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter PII from a single breadcrumb
        
        Args:
            breadcrumb: Breadcrumb dict
        
        Returns:
            Filtered breadcrumb
        """
        if not isinstance(breadcrumb, dict):
            return breadcrumb
        
        filtered = breadcrumb.copy()
        
        # Filter message
        if 'message' in filtered:
            filtered['message'] = self.filter_string(str(filtered['message']))
        
        # Filter data
        if 'data' in filtered and isinstance(filtered['data'], dict):
            filtered['data'] = self.filter_dict(filtered['data'])
        
        return filtered
    
    def filter_user_context(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter user context (remove most fields for privacy)
        
        Args:
            user: User context dict
        
        Returns:
            Filtered user context (minimal info)
        """
        if not isinstance(user, dict):
            return user
        
        # Only keep anonymous session ID
        filtered = {}
        if 'id' in user and isinstance(user['id'], str) and user['id'].startswith('session_'):
            filtered['id'] = user['id']
        
        return filtered


# Global filter instance
_pii_filter: Optional[PIIFilter] = None


def get_pii_filter(scrub_paths: bool = True, allowlist_only: bool = True) -> PIIFilter:
    """
    Get or create global PII filter instance
    
    Args:
        scrub_paths: Whether to scrub file paths
        allowlist_only: Only allow whitelisted fields
    
    Returns:
        PIIFilter instance
    """
    global _pii_filter
    if _pii_filter is None:
        _pii_filter = PIIFilter(scrub_paths=scrub_paths, allowlist_only=allowlist_only)
    return _pii_filter


def filter_event(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Sentry event filter function
    This is the main entry point for Sentry's before_send hook
    
    Args:
        event: Sentry event dict
        hint: Additional context (unused, required by Sentry API)
    
    Returns:
        Filtered event or None to drop
    """
    _ = hint  # Unused but required by Sentry API
    
    pii_filter = get_pii_filter()
    
    # Filter exception info
    if 'exception' in event:
        event['exception'] = pii_filter.filter_exception(event['exception'])
    
    # Filter breadcrumbs
    if 'breadcrumbs' in event:
        event['breadcrumbs'] = pii_filter.filter_breadcrumbs(event['breadcrumbs'])
    
    # Filter user context
    if 'user' in event:
        event['user'] = pii_filter.filter_user_context(event['user'])
    
    # Filter tags and extras
    event = _filter_event_metadata(event, pii_filter)
    
    # Filter request info
    event = _filter_request_info(event)
    
    return event


def _filter_event_metadata(event: Dict[str, Any], pii_filter: PIIFilter) -> Dict[str, Any]:
    """Helper to filter event metadata (tags and extra)"""
    if 'tags' in event and isinstance(event['tags'], dict):
        event['tags'] = pii_filter.filter_dict(event['tags'])
    
    if 'extra' in event and isinstance(event['extra'], dict):
        event['extra'] = pii_filter.filter_dict(event['extra'])
    
    return event


def _filter_request_info(event: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to filter request information"""
    if 'request' in event and isinstance(event['request'], dict):
        if 'url' in event['request']:
            # Parse and filter URL
            try:
                parsed = urlparse(event['request']['url'])
                # Keep only scheme and sanitized path
                event['request']['url'] = f"{parsed.scheme}://[FILTERED]{parsed.path}"
            except Exception:
                event['request']['url'] = '[FILTERED]'
        
        # Remove headers (may contain auth tokens)
        if 'headers' in event['request']:
            del event['request']['headers']
    
    return event
