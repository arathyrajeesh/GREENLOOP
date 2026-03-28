import pytest
from django.urls import reverse
from rest_framework import status
from unittest.mock import patch
from tests.factories import ResidentFactory, AdminFactory, PickupFactory

@pytest.mark.django_db
class TestNotificationViewSet:
    def test_list_notifications(self, authenticated_client, resident_user):
        from apps.notifications.models import Notification
        Notification.objects.create(user=resident_user, title="Test", message="Msg")
        url = reverse('notification-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        
        # Handle both paginated and non-paginated responses
        if isinstance(response.data, dict) and 'results' in response.data:
            assert len(response.data['results']) >= 1
        else:
            assert len(response.data) >= 1

@pytest.mark.django_db
class TestNotificationTasks:
    @pytest.mark.celery(CELERY_TASK_ALWAYS_EAGER=True)
    @patch('apps.notifications.tasks.send_fcm_push')
    def test_notify_resident_pickup_assigned(self, mock_push, resident_user, ward):
        from apps.notifications.tasks import notify_resident_pickup_assigned
        pickup = PickupFactory(resident=resident_user, ward=ward, status='accepted')
        
        notify_resident_pickup_assigned(pickup.id)
        mock_push.assert_called_once()
        from apps.notifications.models import Notification
        assert Notification.objects.filter(user=resident_user).exists()
