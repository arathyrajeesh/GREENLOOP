import pytest
from django.urls import reverse
from rest_framework import status
from django.utils import timezone
from django.contrib.gis.geos import Point
from tests.factories import WorkerFactory, WardFactory, AttendanceLogFactory

@pytest.mark.django_db
class TestWorkerAttendanceView:
    def test_check_in_success(self, worker_client, worker_user):
        ward = worker_user.ward
        check_in_loc = {"type": "Point", "coordinates": [76.95, 8.55]}
        
        url = reverse('hks-attendance')
        data = {
            "has_gloves": True,
            "has_mask": True,
            "has_vest": True,
            "has_boots": True,
            "ppe_photo_url": "http://example.com/ppe.jpg",
            "check_in_location": check_in_loc
        }
        response = worker_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        # If AttendanceLogSerializer is GeoFeature, it has 'id', 'type', 'properties'
        if 'properties' in response.data:
            assert 'check_in' in response.data['properties']
        else:
            assert 'check_in' in response.data

    def test_check_out_success(self, worker_client, worker_user):
        # Create a check-in for today
        AttendanceLogFactory(worker=worker_user, date=timezone.now().date(), check_out=None)
        
        url = reverse('hks-attendance')
        response = worker_client.patch(url)
        assert response.status_code == status.HTTP_200_OK
        if 'properties' in response.data:
            assert response.data['properties']['check_out'] is not None
        else:
            assert response.data['check_out'] is not None

    def test_attendance_history(self, worker_client, worker_user):
        AttendanceLogFactory(worker=worker_user, date=timezone.now().date())
        url = reverse('hks-attendance')
        response = worker_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

@pytest.mark.django_db
class TestAttendanceLogViewSet:
    def test_list_attendance_admin(self, admin_client):
        AttendanceLogFactory()
        url = reverse('attendance-list')
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        # GeoFeature list is a FeatureCollection
        assert 'features' in response.data
