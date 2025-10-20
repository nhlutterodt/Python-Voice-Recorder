"""
Google Drive API Query Builder

Provides a fluent, type-safe interface for building Drive API queries.
Replaces manual query string concatenation with a builder pattern that
prevents errors and improves readability.

Pattern: Fluent Builder Pattern with method chaining support
"""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class QueryBuilder:
    """
    Builds Google Drive API query strings using a fluent interface.
    
    The Drive API accepts queries via the `q` parameter in list() requests.
    This builder provides type-safe methods for common query patterns instead
    of concatenating raw strings, reducing errors and improving maintainability.
    
    Example:
        >>> query = (QueryBuilder()
        ...     .in_folder(folder_id)
        ...     .is_folder()
        ...     .not_trashed()
        ...     .build())
        >>> results = service.files().list(q=query).execute()
    """

    def __init__(self) -> None:
        """Initialize an empty query builder."""
        self._conditions: List[str] = []

    def in_folder(self, folder_id: str) -> "QueryBuilder":
        """
        Add condition: file is in the given folder.
        
        Args:
            folder_id: Google Drive folder ID
        
        Returns:
            Self for method chaining
        """
        if not folder_id:
            logger.warning("in_folder() called with empty folder_id")
            return self
        
        self._conditions.append(f"'{folder_id}' in parents")
        return self

    def is_folder(self) -> "QueryBuilder":
        """
        Add condition: file is a folder.
        
        Returns:
            Self for method chaining
        """
        self._conditions.append("mimeType='application/vnd.google-apps.folder'")
        return self

    def is_file(self) -> "QueryBuilder":
        """
        Add condition: file is NOT a folder (i.e., is a regular file).
        
        Returns:
            Self for method chaining
        """
        self._conditions.append("mimeType!='application/vnd.google-apps.folder'")
        return self

    def not_trashed(self) -> "QueryBuilder":
        """
        Add condition: file is not in trash.
        
        Returns:
            Self for method chaining
        """
        self._conditions.append("trashed=false")
        return self

    def name_equals(self, name: str) -> "QueryBuilder":
        """
        Add condition: file name exactly matches (case-insensitive).
        
        Note: Single quotes in name will be escaped as per Drive API rules.
        
        Args:
            name: Exact file name to match
        
        Returns:
            Self for method chaining
        """
        if not name:
            logger.warning("name_equals() called with empty name")
            return self
        
        # Escape single quotes in the name per Drive API rules
        escaped_name = name.replace("'", "\\'")
        self._conditions.append(f"name='{escaped_name}'")
        return self

    def name_contains(self, substring: str) -> "QueryBuilder":
        """
        Add condition: file name contains substring (case-sensitive).
        
        Args:
            substring: Substring to search for in file name
        
        Returns:
            Self for method chaining
        """
        if not substring:
            logger.warning("name_contains() called with empty substring")
            return self
        
        # Escape single quotes in the substring
        escaped_substring = substring.replace("'", "\\'")
        self._conditions.append(f"name contains '{escaped_substring}'")
        return self

    def mime_type(self, mime_type: str) -> "QueryBuilder":
        """
        Add condition: file has specific MIME type.
        
        Common MIME types:
        - 'application/vnd.google-apps.folder' - Google Drive folder
        - 'audio/wav' - WAV audio file
        - 'audio/mpeg' - MP3 audio file
        
        Args:
            mime_type: MIME type string
        
        Returns:
            Self for method chaining
        """
        if not mime_type:
            logger.warning("mime_type() called with empty mime_type")
            return self
        
        self._conditions.append(f"mimeType='{mime_type}'")
        return self

    def at_root(self) -> "QueryBuilder":
        """
        Add condition: file is at root level (direct child of Drive root).
        
        Returns:
            Self for method chaining
        """
        self._conditions.append("'root' in parents")
        return self

    def owned_by_me(self) -> "QueryBuilder":
        """
        Add condition: file is owned by the authenticated user.
        
        Returns:
            Self for method chaining
        """
        self._conditions.append("'me' in owners")
        return self

    def shared_with_me(self) -> "QueryBuilder":
        """
        Add condition: file is shared with the authenticated user (not owned).
        
        Returns:
            Self for method chaining
        """
        self._conditions.append("sharedWithMe=true")
        return self

    def custom(self, condition: str) -> "QueryBuilder":
        """
        Add a custom raw condition string.
        
        Use this for Drive API query conditions not covered by other methods.
        See Drive API documentation for valid query syntax:
        https://developers.google.com/drive/api/guides/search-files
        
        Args:
            condition: Raw Drive API query condition
        
        Returns:
            Self for method chaining
        """
        if condition:
            self._conditions.append(condition)
        return self

    def build(self) -> str:
        """
        Build the final query string.
        
        Combines all conditions with ' and ' operator.
        
        Returns:
            Complete Drive API query string ready for use in service.files().list(q=...)
        
        Example:
            >>> query = QueryBuilder().is_folder().not_trashed().build()
            >>> "mimeType='application/vnd.google-apps.folder' and trashed=false"
        """
        if not self._conditions:
            return ""
        return " and ".join(self._conditions)

    def clear(self) -> "QueryBuilder":
        """
        Clear all conditions and start fresh.
        
        Returns:
            Self for method chaining
        """
        self._conditions.clear()
        return self

    def __str__(self) -> str:
        """Return the built query string."""
        return self.build()

    def __repr__(self) -> str:
        """Return a representation showing the query being built."""
        return f"QueryBuilder(conditions={len(self._conditions)}, query={self.build()!r})"
