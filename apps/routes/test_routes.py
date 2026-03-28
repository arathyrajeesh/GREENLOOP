import pytest
from django.urls import reverse
from rest_framework import status
from tests.factories import RouteFactory

@pytest.mark.django_db
class TestRouteViewSet:
    def test_list_routes_authenticated(self, worker_client):
        url = reverse('route-list')
        response = worker_client.get(url)
        assert response.status_code == status.HTTP_200_OK

@pytest.mark.django_db
class TestTodayRouteView:
    def test_get_today_route_worker(self, worker_client, worker_user, ward):
        RouteFactory(hks_worker=worker_user, ward=ward)
        url = reverse('hks-route-today')
        response = worker_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert 'route' in response.data
        assert 'pickups' in response.data

    def test_get_today_route_resident_forbidden(self, authenticated_client):
        url = reverse('hks-route-today')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
