"""
Unit tests for cloud._query_builder module

Tests QueryBuilder class for building Google Drive API queries
"""

import pytest
from cloud._query_builder import QueryBuilder


class TestQueryBuilderBasics:
    """Tests for basic QueryBuilder functionality"""
    
    def test_empty_builder(self):
        """Test that empty builder produces empty string"""
        builder = QueryBuilder()
        assert builder.build() == ""
    
    def test_single_condition(self):
        """Test building single condition"""
        builder = QueryBuilder()
        result = builder.is_folder().build()
        assert result == "mimeType='application/vnd.google-apps.folder'"
    
    def test_chaining(self):
        """Test method chaining returns QueryBuilder"""
        builder = QueryBuilder()
        result = builder.is_folder()
        assert isinstance(result, QueryBuilder)
    
    def test_str_representation(self):
        """Test __str__ returns the query"""
        builder = QueryBuilder().is_folder()
        assert str(builder) == builder.build()


class TestInFolder:
    """Tests for in_folder method"""
    
    def test_in_folder_basic(self):
        """Test in_folder adds correct condition"""
        builder = QueryBuilder().in_folder("abc123")
        assert "'abc123' in parents" in builder.build()
    
    def test_in_folder_with_special_chars(self):
        """Test in_folder with folder ID containing special chars"""
        builder = QueryBuilder().in_folder("abc-123_xyz")
        assert "'abc-123_xyz' in parents" in builder.build()
    
    def test_in_folder_empty_string(self):
        """Test that empty folder ID is ignored"""
        builder = QueryBuilder().in_folder("")
        assert builder.build() == ""


class TestIsFolder:
    """Tests for is_folder method"""
    
    def test_is_folder_condition(self):
        """Test is_folder adds correct MIME type"""
        builder = QueryBuilder().is_folder()
        assert "mimeType='application/vnd.google-apps.folder'" in builder.build()


class TestIsFile:
    """Tests for is_file method"""
    
    def test_is_file_condition(self):
        """Test is_file adds correct condition"""
        builder = QueryBuilder().is_file()
        assert "mimeType!='application/vnd.google-apps.folder'" in builder.build()


class TestNotTrashed:
    """Tests for not_trashed method"""
    
    def test_not_trashed_condition(self):
        """Test not_trashed adds correct condition"""
        builder = QueryBuilder().not_trashed()
        assert "trashed=false" in builder.build()


class TestNameEquals:
    """Tests for name_equals method"""
    
    def test_name_equals_basic(self):
        """Test name_equals with simple name"""
        builder = QueryBuilder().name_equals("My Folder")
        assert "name='My Folder'" in builder.build()
    
    def test_name_equals_with_quotes(self):
        """Test name_equals escapes single quotes"""
        builder = QueryBuilder().name_equals("John's Folder")
        assert "name='John\\'s Folder'" in builder.build()
    
    def test_name_equals_empty(self):
        """Test name_equals with empty string"""
        builder = QueryBuilder().name_equals("")
        assert builder.build() == ""
    
    def test_name_equals_special_chars(self):
        """Test name_equals with various special characters"""
        builder = QueryBuilder().name_equals("Audio (Draft) - v2.wav")
        query = builder.build()
        assert "name='Audio (Draft) - v2.wav'" in query


class TestNameContains:
    """Tests for name_contains method"""
    
    def test_name_contains_basic(self):
        """Test name_contains with simple substring"""
        builder = QueryBuilder().name_contains("voice")
        assert "name contains 'voice'" in builder.build()
    
    def test_name_contains_escapes_quotes(self):
        """Test name_contains escapes single quotes"""
        builder = QueryBuilder().name_contains("it's")
        assert "name contains 'it\\'s'" in builder.build()
    
    def test_name_contains_empty(self):
        """Test name_contains with empty string"""
        builder = QueryBuilder().name_contains("")
        assert builder.build() == ""


class TestMimeType:
    """Tests for mime_type method"""
    
    def test_mime_type_folder(self):
        """Test mime_type with folder MIME type"""
        builder = QueryBuilder().mime_type("application/vnd.google-apps.folder")
        assert "mimeType='application/vnd.google-apps.folder'" in builder.build()
    
    def test_mime_type_audio(self):
        """Test mime_type with audio MIME types"""
        builder = QueryBuilder().mime_type("audio/wav")
        assert "mimeType='audio/wav'" in builder.build()
    
    def test_mime_type_empty(self):
        """Test mime_type with empty string"""
        builder = QueryBuilder().mime_type("")
        assert builder.build() == ""


class TestAtRoot:
    """Tests for at_root method"""
    
    def test_at_root_condition(self):
        """Test at_root adds correct condition"""
        builder = QueryBuilder().at_root()
        assert "'root' in parents" in builder.build()


class TestOwnedByMe:
    """Tests for owned_by_me method"""
    
    def test_owned_by_me_condition(self):
        """Test owned_by_me adds correct condition"""
        builder = QueryBuilder().owned_by_me()
        assert "'me' in owners" in builder.build()


class TestSharedWithMe:
    """Tests for shared_with_me method"""
    
    def test_shared_with_me_condition(self):
        """Test shared_with_me adds correct condition"""
        builder = QueryBuilder().shared_with_me()
        assert "sharedWithMe=true" in builder.build()


class TestCustom:
    """Tests for custom method"""
    
    def test_custom_condition(self):
        """Test custom adds raw condition"""
        builder = QueryBuilder().custom("size > 1000")
        assert "size > 1000" in builder.build()
    
    def test_custom_empty_ignored(self):
        """Test custom with empty string is ignored"""
        builder = QueryBuilder().custom("")
        assert builder.build() == ""


class TestComplexQueries:
    """Tests for complex multi-condition queries"""
    
    def test_multiple_conditions_joined_with_and(self):
        """Test that multiple conditions are joined with ' and '"""
        builder = (QueryBuilder()
                  .in_folder("folder123")
                  .is_folder()
                  .not_trashed())
        query = builder.build()
        assert " and " in query
        assert "'folder123' in parents" in query
        assert "mimeType='application/vnd.google-apps.folder'" in query
        assert "trashed=false" in query
    
    def test_realistic_folder_query(self):
        """Test realistic folder listing query"""
        builder = (QueryBuilder()
                  .in_folder("abc123")
                  .is_folder()
                  .not_trashed())
        query = builder.build()
        # Should have exactly 2 'and' separators for 3 conditions
        assert query.count(" and ") == 2
    
    def test_realistic_file_query(self):
        """Test realistic file search query"""
        builder = (QueryBuilder()
                  .name_contains("voice")
                  .mime_type("audio/wav")
                  .not_trashed())
        query = builder.build()
        assert "name contains 'voice'" in query
        assert "mimeType='audio/wav'" in query
        assert "trashed=false" in query
    
    def test_recordings_folder_query(self):
        """Test query for Voice Recorder Pro recordings folder"""
        builder = (QueryBuilder()
                  .name_equals("Voice Recorder Pro")
                  .is_folder()
                  .not_trashed())
        query = builder.build()
        assert "name='Voice Recorder Pro'" in query
        assert "mimeType='application/vnd.google-apps.folder'" in query
        assert "trashed=false" in query


class TestClear:
    """Tests for clear method"""
    
    def test_clear_resets_conditions(self):
        """Test clear removes all conditions"""
        builder = QueryBuilder().is_folder().not_trashed()
        assert builder.build() != ""
        builder.clear()
        assert builder.build() == ""
    
    def test_clear_returns_builder(self):
        """Test clear returns self for chaining"""
        builder = QueryBuilder()
        result = builder.clear()
        assert result is builder
    
    def test_clear_and_rebuild(self):
        """Test that builder can be reused after clear"""
        builder = QueryBuilder().is_folder()
        first_query = builder.build()
        
        builder.clear().is_file()
        second_query = builder.build()
        
        assert first_query != second_query
        assert first_query == "mimeType='application/vnd.google-apps.folder'"
        assert second_query == "mimeType!='application/vnd.google-apps.folder'"


class TestRepr:
    """Tests for __repr__ method"""
    
    def test_repr_shows_query(self):
        """Test __repr__ includes query info"""
        builder = QueryBuilder().is_folder()
        repr_str = repr(builder)
        assert "QueryBuilder" in repr_str
        assert "mimeType='application/vnd.google-apps.folder'" in repr_str
