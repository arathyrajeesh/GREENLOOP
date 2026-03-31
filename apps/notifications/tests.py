import pytest
from unittest.mock import patch
from apps.notifications.tasks import notify_admin_new_complaint, notify_resident_pickup_complete, send_fcm_push_task
from tests.factories import ComplaintFactory, PickupFactory, UserFactory, AdminFactory, WorkerFactory

@pytest.mark.django_db
class TestNotificationTasks:
    @patch('apps.notifications.tasks.send_push_notification')
    def test_notify_admin_new_complaint(self, mock_push):
        complaint = ComplaintFactory()
        # Admin user for notification
        AdminFactory(fcm_token='admin-token')
        
        notify_admin_new_complaint(complaint.id)
        assert mock_push.called

    @patch('apps.notifications.tasks.send_push_notification')
    def test_notify_resident_pickup_complete(self, mock_push):
        # We need a reward created first for this task's retry logic
        from apps.rewards.models import Reward
        pickup = PickupFactory(status='completed')
        Reward.objects.create(pickup=pickup, resident=pickup.resident, points=10, transaction_type='EARNED')
        
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
        # Mock the AI service or verification fields since some validation might happen
        flag_pickup_for_review(pickup.id)
        pickup.refresh_from_db()
        # Ensure it works or at least doesn't crash during test
