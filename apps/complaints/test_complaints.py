import pytest
from django.urls import reverse
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch
from tests.factories import ComplaintFactory, AdminFactory, WorkerFactory

@pytest.mark.django_db
class TestComplaintViewSet:
    def test_list_complaints_resident(self, authenticated_client, resident_user):
        ComplaintFactory(reporter=resident_user)
        url = reverse('complaint-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert 'features' in response.data
        assert len(response.data['features']) >= 1

    def test_assign_complaint_admin(self, admin_client, worker_user):
        complaint = ComplaintFactory(status='submitted')
        # Use custom 'assign' action
        url = reverse('complaint-assign', kwargs={'pk': complaint.pk})
        data = {"worker_id": str(worker_user.id)}
        response = admin_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
        complaint.refresh_from_db()
        assert complaint.assigned_to == worker_user
        assert complaint.status == 'assigned'

    def test_resolve_complaint_worker(self, worker_client, worker_user):
        complaint = ComplaintFactory(status='assigned', assigned_to=worker_user)
        url = reverse('complaint-advance-status', kwargs={'pk': complaint.pk})
        
        # Advance from assigned to in-progress
        response = worker_client.post(url)
        assert response.status_code == status.HTTP_200_OK
        
        # Advance from in-progress to resolved
        response = worker_client.post(url)
        assert response.status_code == status.HTTP_200_OK
        
        complaint.refresh_from_db()
        assert complaint.status == 'resolved'
        assert complaint.resolved_at is not None

@pytest.mark.django_db
class TestComplaintTasks:
    @pytest.mark.celery(CELERY_TASK_ALWAYS_EAGER=True)
    def test_check_pending_complaints_escalation(self, db):
        from apps.complaints.tasks import check_pending_complaints
        from apps.complaints.models import Complaint
        
        # Create an old complaint
        old_time = timezone.now() - timedelta(hours=50)
        c = ComplaintFactory(status='submitted', is_escalated=False)
        Complaint.objects.filter(id=c.id).update(created_at=old_time)
        
        # Admin for notification
        AdminFactory()
        
        result = check_pending_complaints()
        assert "Escalated 1 complaints" in result
        
        c.refresh_from_db()
        assert c.is_escalated is True
        assert c.priority == 4 # Urgent
