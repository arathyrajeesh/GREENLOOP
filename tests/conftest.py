import pytest
from rest_framework.test import APIClient
from tests.factories import AdminFactory, ResidentFactory, WorkerFactory, WardFactory

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def admin_user(db):
    return AdminFactory()

@pytest.fixture
def resident_user(db):
    return ResidentFactory()

@pytest.fixture
def worker_user(db):
    return WorkerFactory()

@pytest.fixture
def ward(db):
    return WardFactory()

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

@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    pass

@pytest.fixture(autouse=True)
def celery_eager_mode(settings):
    """
    Ensure Celery tasks run synchronously during tests.
    """
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
