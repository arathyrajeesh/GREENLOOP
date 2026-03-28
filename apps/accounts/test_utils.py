import pytest
from unittest.mock import patch, MagicMock
from apps.accounts.utils import send_resend_email
from django.conf import settings

@patch('requests.post')
def test_send_resend_email_success(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_post.return_value = mock_response
    
    with patch('apps.accounts.utils.getattr', side_effect=lambda obj, attr, default=None: "test-key" if attr == 'RES_API_KEY' else default):
        # We need to ensure settings.RESEND_API_KEY is mocked or env var is set
        with patch.dict('os.environ', {'RESEND_API_KEY': 'test-key'}):
            result = send_resend_email("test@example.com", "Subject", "<p>Content</p>")
            assert result is True

@patch('requests.post')
def test_send_resend_email_failure(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_post.return_value = mock_response
    
    with patch.dict('os.environ', {'RESEND_API_KEY': 'test-key'}):
        result = send_resend_email("test@example.com", "Subject", "<p>Content</p>")
        assert result is False
