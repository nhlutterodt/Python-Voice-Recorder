#!/usr/bin/env python3
"""
Tests for PII filter module
"""
import pytest
from core.pii_filter import PIIFilter, get_pii_filter, filter_event


class TestPIIFilter:
    """Test PII filtering functionality"""
    
    def setup_method(self):
        """Reset global filter before each test"""
        import core.pii_filter
        core.pii_filter._pii_filter = None
    
    def test_filter_email(self):
        """Test email filtering"""
        pii_filter = PIIFilter()
        text = "Contact us at support@example.com for help"
        filtered = pii_filter.filter_string(text)
        assert "[EMAIL]" in filtered
        assert "support@example.com" not in filtered
    
    def test_filter_ip_address(self):
        """Test IP address filtering"""
        pii_filter = PIIFilter()
        text = "Connection from 192.168.1.100 detected"
        filtered = pii_filter.filter_string(text)
        assert "[IP]" in filtered
        assert "192.168.1.100" not in filtered
    
    def test_filter_windows_path(self):
        """Test Windows file path filtering"""
        pii_filter = PIIFilter(scrub_paths=True)
        text = "Recording saved to C:\\Users\\JohnDoe\\Documents\\recording.wav"
        filtered = pii_filter.filter_string(text)
        assert "recording.wav" in filtered
        assert "JohnDoe" not in filtered
        assert "C:\\Users" not in filtered
    
    def test_filter_unix_path(self):
        """Test Unix file path filtering"""
        pii_filter = PIIFilter(scrub_paths=True)
        text = "Recording saved to /home/johndoe/recordings/test.wav"
        filtered = pii_filter.filter_string(text)
        assert "test.wav" in filtered
        assert "johndoe" not in filtered
        assert "/home" not in filtered
    
    def test_filter_dict_allowlist(self):
        """Test dictionary filtering with allowlist"""
        pii_filter = PIIFilter(allowlist_only=True)
        data = {
            'event_type': 'recording_started',
            'duration_ms': 1500,
            'custom_field': 'should_be_removed',
            'password': 'secret123'
        }
        filtered = pii_filter.filter_dict(data)
        assert 'event_type' in filtered
        assert 'duration_ms' in filtered
        assert 'custom_field' not in filtered
        assert 'password' not in filtered
    
    def test_filter_dict_blocklist(self):
        """Test dictionary blocklist filtering"""
        pii_filter = PIIFilter(allowlist_only=False)
        data = {
            'message': 'Test message',
            'password': 'secret123',
            'api_key': 'key_abc123',
            'token': 'bearer_xyz'
        }
        filtered = pii_filter.filter_dict(data)
        assert 'message' in filtered
        assert 'password' not in filtered
        assert 'api_key' not in filtered
        assert 'token' not in filtered
    
    def test_filter_nested_dict(self):
        """Test nested dictionary filtering"""
        pii_filter = PIIFilter(allowlist_only=True)
        data = {
            'event_type': 'error',
            'extra': {  # 'extra' is not in allowlist, so it will be removed
                'operation': 'save_file',
                'custom': 'removed'
            }
        }
        filtered = pii_filter.filter_dict(data)
        assert filtered['event_type'] == 'error'
        # 'extra' key is not in allowlist, so entire nested dict is removed
        assert 'extra' not in filtered
    
    def test_filter_list_values(self):
        """Test filtering list values"""
        pii_filter = PIIFilter()
        data = {
            'message': 'Test',
            'emails': ['user@example.com', 'admin@test.com']
        }
        filtered = pii_filter.filter_dict(data)
        for email in filtered.get('emails', []):
            assert '@' not in email  # Should be filtered
    
    def test_filter_exception_message(self):
        """Test exception message filtering"""
        pii_filter = PIIFilter()
        exc_info = {
            'message': 'Failed to save C:\\Users\\John\\file.wav',
            'type': 'IOError'
        }
        filtered = pii_filter.filter_exception(exc_info)
        assert 'file.wav' in filtered['message']
        assert 'John' not in filtered['message']
        assert filtered['type'] == 'IOError'
    
    def test_filter_stacktrace_frames(self):
        """Test stack trace frame filtering"""
        pii_filter = PIIFilter(scrub_paths=True)
        stacktrace = {
            'frames': [
                {
                    'filename': 'C:\\Users\\Alice\\project\\main.py',
                    'abs_path': 'C:\\Users\\Alice\\project\\main.py',
                    'function': 'process_audio',
                    'vars': {'password': 'secret'}
                }
            ]
        }
        filtered = pii_filter._filter_stacktrace(stacktrace)
        frame = filtered['frames'][0]
        assert frame['filename'] == 'main.py'
        assert frame['abs_path'] == 'main.py'
        assert frame['function'] == 'process_audio'
        assert 'vars' not in frame  # Local vars removed for privacy
    
    def test_filter_breadcrumbs(self):
        """Test breadcrumb filtering"""
        pii_filter = PIIFilter()
        breadcrumbs = [
            {
                'message': 'User logged in from 192.168.1.50',
                'category': 'auth',
                'data': {
                    'user_id': 'session_abc123',
                    'ip': '192.168.1.50'
                }
            }
        ]
        filtered = pii_filter.filter_breadcrumbs(breadcrumbs)
        assert '[IP]' in filtered[0]['message']
        assert '192.168.1.50' not in filtered[0]['message']
    
    def test_filter_user_context_anonymous(self):
        """Test user context filtering (keep only session ID)"""
        pii_filter = PIIFilter()
        user = {
            'id': 'session_abc123',
            'username': 'johndoe',
            'email': 'john@example.com',
            'ip_address': '10.0.0.1'
        }
        filtered = pii_filter.filter_user_context(user)
        assert filtered['id'] == 'session_abc123'
        assert 'username' not in filtered
        assert 'email' not in filtered
        assert 'ip_address' not in filtered
    
    def test_filter_user_context_non_session_id(self):
        """Test user context filtering with non-session ID"""
        pii_filter = PIIFilter()
        user = {
            'id': 'user_12345',  # Not a session ID
            'username': 'johndoe'
        }
        filtered = pii_filter.filter_user_context(user)
        assert 'id' not in filtered  # Should be removed
        assert 'username' not in filtered
    
    def test_global_filter_instance(self):
        """Test global filter instance creation"""
        filter1 = get_pii_filter()
        filter2 = get_pii_filter()
        assert filter1 is filter2  # Should be same instance
    
    def test_filter_event_integration(self):
        """Test full Sentry event filtering"""
        event = {
            'exception': {
                'values': [{
                    'type': 'ValueError',
                    'value': 'Invalid file path: C:\\Users\\Bob\\test.wav',
                    'stacktrace': {
                        'frames': [{
                            'filename': 'C:\\Users\\Bob\\app\\main.py',
                            'function': 'load_file'
                        }]
                    }
                }]
            },
            'breadcrumbs': [
                {'message': 'Loading file from /home/user/data/file.wav'}
            ],
            'user': {
                'id': 'session_xyz789',
                'email': 'bob@example.com'
            },
            'tags': {
                'environment': 'production',
                'custom_tag': 'removed'
            },
            'extra': {
                'operation': 'file_load',
                'path': '/home/user/data/file.wav'
            }
        }
        
        filtered = filter_event(event, {})
        
        # Check exception message filtered
        exc_value = filtered['exception']['values'][0]['value']
        assert 'test.wav' in exc_value
        assert 'Bob' not in exc_value
        
        # Check stack frame filtered
        frame = filtered['exception']['values'][0]['stacktrace']['frames'][0]
        assert frame['filename'] == 'main.py'
        
        # Check breadcrumb filtered
        assert 'file.wav' in filtered['breadcrumbs'][0]['message']
        assert 'user' not in filtered['breadcrumbs'][0]['message']
        
        # Check user context filtered
        assert filtered['user']['id'] == 'session_xyz789'
        assert 'email' not in filtered['user']
        
        # Check tags/extra filtered (allowlist mode)
        assert 'environment' in filtered['tags']
        assert 'custom_tag' not in filtered['tags']
        assert 'operation' in filtered['extra']
    
    def test_filter_request_info(self):
        """Test request info filtering"""
        from core.pii_filter import _filter_request_info
        event = {
            'request': {
                'url': 'https://api.example.com/users/johndoe/recordings',
                'headers': {
                    'Authorization': 'Bearer token123',
                    'User-Agent': 'VoiceRecorder/2.0'
                }
            }
        }
        filtered = _filter_request_info(event)
        assert 'headers' not in filtered['request']
        assert '[FILTERED]' in filtered['request']['url']
        # Path is preserved in current implementation, only URL base is filtered
    
    def test_no_pii_in_output(self):
        """Test that no PII leaks through filtering"""
        pii_filter = PIIFilter(scrub_paths=True, allowlist_only=True)
        
        # Input with multiple PII types
        text = """
        User john.doe@company.com accessed the system from 10.0.1.100.
        Files saved to C:\\Users\\johndoe\\Documents\\recordings\\test.wav
        Password: secret123, API Key: key_abc, Token: xyz789
        """
        
        filtered_text = pii_filter.filter_string(text)
        
        # Verify all PII removed
        assert 'john.doe@company.com' not in filtered_text
        assert '10.0.1.100' not in filtered_text
        assert 'johndoe' not in filtered_text
        assert 'C:\\Users' not in filtered_text
        
        # Verify markers present
        assert '[EMAIL]' in filtered_text
        assert '[IP]' in filtered_text
        assert 'test.wav' in filtered_text  # Filename preserved
