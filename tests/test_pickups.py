import pytest
from django.urls import reverse
from rest_framework import status
from tests.factories import PickupFactory, ResidentFactory, WorkerFactory

@pytest.mark.django_db
class TestPickupOperations:
    def test_list_pickups_resident(self, authenticated_client, resident_user):
        PickupFactory(resident=resident_user)
        # Another resident's pickup
        PickupFactory()
        
        url = reverse('pickup-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        
        # In PickupViewSet logic, residents only see their own pickups
        # Let's check view logic.
        assert len(response.data['results'] if 'results' in response.data else response.data['features']) >= 1

    def test_create_pickup_resident(self, authenticated_client, resident_user):
        url = reverse('pickup-list')
        data = {
            "waste_type": "dry",
            "scheduled_date": "2026-04-01",
            "time_slot": "10:00-12:00",
            "location": {"type": "Point", "coordinates": [76.9, 8.5]}
        }
        response = authenticated_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data.get('properties', {}).get('status') == 'pending'

    def test_worker_can_list_pickups_in_their_ward(self, worker_client, worker_user, ward):
        # Create pickup in worker's ward
        res = ResidentFactory(ward=ward)
        PickupFactory(resident=res)
        
        url = reverse('pickup-list')
        response = worker_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        # Workers should see all in their ward
        assert len(response.data['features']) >= 1
