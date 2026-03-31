import pytest
from unittest.mock import patch
from apps.notifications.tasks import send_fcm_push_task
from tests.factories import ResidentFactory

@pytest.mark.django_db
class TestNotificationTasks:
    
    @patch('apps.notifications.utils.messaging.send')
    def test_send_fcm_push_task_success(self, mock_send, resident_user):
        resident_user.fcm_token = "valid_token"
        resident_user.save()
        
        mock_send.return_value = "projects/greenloop/messages/123"
        
        # Test synchronously via US-TASK-03 fix
        result = send_fcm_push_task(resident_user.id, "Test Title", "Test Body")
        
        assert result is True
        assert mock_send.called
        
        # Verify DB record
        from apps.notifications.models import Notification
        assert Notification.objects.filter(user=resident_user).count() == 1

    @patch('apps.notifications.utils.messaging.send')
    def test_send_fcm_push_task_no_token(self, mock_send, resident_user):
        resident_user.fcm_token = None
        resident_user.save()
        
        result = send_fcm_push_task(resident_user.id, "Title", "Body")
        assert result is False
        assert not mock_send.called
