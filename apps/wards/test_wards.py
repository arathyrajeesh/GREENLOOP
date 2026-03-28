import pytest
from django.urls import reverse
from rest_framework import status
from tests.factories import WardFactory, WorkerFactory

@pytest.mark.django_db
class TestWardViewSet:
    def test_list_wards(self, authenticated_client, ward):
        url = reverse('ward-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert 'features' in response.data
        assert len(response.data['features']) >= 1

    def test_retrieve_ward(self, authenticated_client, ward):
        url = reverse('ward-detail', kwargs={'pk': ward.pk})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert 'id' in response.data or response.data.get('properties', {}).get('id')

    def test_ward_permissions(self, api_client, ward):
        url = reverse('ward-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_ward_admin_only(self, admin_client):
        url = reverse('ward-list')
        data = {
            "name": "New Ward",
            "number": 99,
            "location": {"type": "Point", "coordinates": [76.9, 8.5]},
            "boundary": {
                "type": "Polygon",
                "coordinates": [[[76.8, 8.4], [77.0, 8.4], [77.0, 8.6], [76.8, 8.6], [76.8, 8.4]]]
            }
        }
        response = admin_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_ward_workers_list(self, authenticated_client, ward):
        WorkerFactory(ward=ward)
        url = reverse('ward-workers', kwargs={'pk': ward.pk})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_assign_workers_admin(self, admin_client, ward):
        worker = WorkerFactory(ward=None)
        url = reverse('ward-assign-workers', kwargs={'pk': ward.pk})
        data = {"worker_ids": [str(worker.id)]}
        response = admin_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        worker.refresh_from_db()
        assert worker.ward == ward
