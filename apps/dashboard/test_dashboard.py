import pytest
from django.urls import reverse
from rest_framework import status
from tests.factories import SyncQueueFactory

@pytest.mark.django_db
class TestSyncQueueViewSet:
    def test_prefetch_worker(self, worker_client, worker_user):
        url = reverse('sync-prefetch')
        response = worker_client.get(url)
        # 403 if worker hasn't been assigned a route today, but the code says 200 with empty data
        assert response.status_code == status.HTTP_200_OK

    def test_upload_sync_items(self, worker_client, worker_user, pickup):
        url = reverse('sync-upload')
        data = [
            {
                "client_id": "c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1",
                "model_name": "Pickup",
                "object_id": str(pickup.id),
                "action": "UPDATE",
                "payload": {"status": "completed"},
                "client_timestamp": "2026-03-28T10:00:00Z"
            }
        ]
        response = worker_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['items'][0]['status'] == 'SYNCED'
        
        pickup.refresh_from_db()
        assert pickup.status == 'completed'
