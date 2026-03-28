import pytest
from rest_framework.test import APIClient
from tests.factories import UserFactory, AdminFactory, WorkerFactory, ResidentFactory, WardFactory, PickupFactory

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def admin_user(db):
    return AdminFactory()

@pytest.fixture
def worker_user(db):
    return WorkerFactory()

@pytest.fixture
def resident_user(db):
    return ResidentFactory()

@pytest.fixture
def ward(db):
    return WardFactory()

@pytest.fixture
def pickup(db, resident_user):
    return PickupFactory(resident=resident_user)

@pytest.fixture
def authenticated_client(api_client, resident_user):
    api_client.force_authenticate(user=resident_user)
    return api_client

@pytest.fixture
def admin_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client

@pytest.fixture
def worker_client(api_client, worker_user):
    api_client.force_authenticate(user=worker_user)
    return api_client
