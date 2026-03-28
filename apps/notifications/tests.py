import pytest
from unittest.mock import patch
from apps.notifications.tasks import notify_admin_new_complaint, notify_resident_pickup_complete, send_fcm_push
from tests.factories import ComplaintFactory, PickupFactory, UserFactory

@pytest.mark.django_db
class TestNotificationTasks:
    @patch('apps.notifications.tasks.send_fcm_push')
    def test_notify_admin_new_complaint(self, mock_push):
        complaint = ComplaintFactory()
        # Admin user for notification
        UserFactory(role='ADMIN', fcm_token='admin-token')
        
        notify_admin_new_complaint(complaint.id)
        assert mock_push.called

    @patch('apps.notifications.tasks.send_fcm_push')
    def test_notify_resident_pickup_complete(self, mock_push):
        pickup = PickupFactory(status='completed')
        pickup.resident.fcm_token = 'resident-token'
        pickup.resident.save()
        
        notify_resident_pickup_complete(pickup.id)
        assert mock_push.called

@pytest.mark.django_db
class TestPickupTasks:
    def test_flag_pickup_for_review(self):
        from apps.pickups.tasks import flag_pickup_for_review
        from apps.pickups.models import PickupVerification
        pickup = PickupFactory()
        worker = UserFactory(role='HKS_WORKER')
        PickupVerification.objects.create(
            pickup=pickup, 
            verified_by=worker,
            contamination_confidence=0.3
        )
        
        flag_pickup_for_review(pickup.id)
        pickup.refresh_from_db()
        assert pickup.verification.requires_admin_review is True
