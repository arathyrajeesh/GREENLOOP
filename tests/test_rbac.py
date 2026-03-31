import pytest
from django.urls import reverse
from rest_framework import status

@pytest.mark.django_db
class TestGlobalRBAC:
    """
    Ensures that security boundaries between ADMIN and RESIDENT/WORKER are enforced.
    """
    
    admin_only_endpoints = [
        ('user-list', 'get', {}),
        ('create-worker', 'post', {}),
        ('dashboard-stats-list', 'get', {}),
        ('ward-list', 'post', {}), # Create ward
        ('reward-settings-list', 'get', {}),
        ('reward-item-list', 'post', {}),
        ('materialtype-list', 'post', {}),
    ]

    @pytest.mark.parametrize("url_name, method, data", admin_only_endpoints)
    def test_resident_cannot_access_admin_endpoints(self, authenticated_client, url_name, method, data):
        url = reverse(url_name)
        if method == 'get':
            response = authenticated_client.get(url)
        elif method == 'post':
            response = authenticated_client.post(url, data)
        
        # Should be 403 Forbidden
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_worker_cannot_access_dashboard_stats(self, worker_client):
        url = reverse('dashboard-stats-list')
        response = worker_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
