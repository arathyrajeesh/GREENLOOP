import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from tests.factories import ResidentFactory, AdminFactory, WardFactory, WorkerFactory
from apps.reports.models import NPSSurvey


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_resident_eligible(resident):
    """Backdate registration so the 30-day trigger fires."""
    from apps.users.models import User
    User.objects.filter(pk=resident.pk).update(
        created_at=timezone.now() - timezone.timedelta(days=31)
    )
    resident.refresh_from_db()


# ── Status endpoint ───────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_nps_status_not_eligible_yet(api_client):
    """New resident (<30 days) should NOT see the survey."""
    resident = ResidentFactory()
    api_client.force_authenticate(user=resident)
    response = api_client.get(reverse("nps-status"))
    assert response.status_code == status.HTTP_200_OK
    assert response.data["show_survey"] is False


@pytest.mark.django_db
def test_nps_status_eligible(api_client):
    """Resident registered >30 days ago with no submission → show survey."""
    resident = ResidentFactory()
    make_resident_eligible(resident)
    api_client.force_authenticate(user=resident)
    response = api_client.get(reverse("nps-status"))
    assert response.status_code == status.HTTP_200_OK
    assert response.data["show_survey"] is True


@pytest.mark.django_db
def test_nps_status_cooldown_active(api_client):
    """Resident who submitted recently (within 60 days) → don't show again."""
    resident = ResidentFactory()
    make_resident_eligible(resident)
    NPSSurvey.objects.create(
        resident=resident,
        score=8,
        next_prompt_at=timezone.now() + timezone.timedelta(days=50),
    )
    api_client.force_authenticate(user=resident)
    response = api_client.get(reverse("nps-status"))
    assert response.data["show_survey"] is False


# ── Submit endpoint ───────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_nps_submit_creates_survey(api_client):
    """Valid submission creates an NPSSurvey record."""
    resident = ResidentFactory()
    api_client.force_authenticate(user=resident)
    payload = {"score": 9, "comment": "Great service!"}
    response = api_client.post(reverse("nps-submit"), payload)
    assert response.status_code == status.HTTP_201_CREATED
    assert NPSSurvey.objects.filter(resident=resident).exists()
    survey = NPSSurvey.objects.get(resident=resident)
    assert survey.score == 9
    assert survey.comment == "Great service!"
    assert survey.category == "promoter"


@pytest.mark.django_db
def test_nps_submit_rejects_invalid_score(api_client):
    """Score outside 0-10 is rejected."""
    resident = ResidentFactory()
    api_client.force_authenticate(user=resident)
    response = api_client.post(reverse("nps-submit"), {"score": 11})
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_nps_submit_updates_existing(api_client):
    """Resubmitting updates the existing record and resets cooldown."""
    resident = ResidentFactory()
    NPSSurvey.objects.create(
        resident=resident,
        score=5,
        next_prompt_at=timezone.now() - timezone.timedelta(days=1),  # expired
    )
    api_client.force_authenticate(user=resident)
    response = api_client.post(reverse("nps-submit"), {"score": 10, "comment": "Even better!"})
    assert response.status_code == status.HTTP_200_OK
    survey = NPSSurvey.objects.get(resident=resident)
    assert survey.score == 10
    assert survey.category == "promoter"


@pytest.mark.django_db
def test_nps_submit_forbidden_for_worker(api_client):
    """HKS Workers cannot submit NPS surveys."""
    worker = WorkerFactory()
    api_client.force_authenticate(user=worker)
    response = api_client.post(reverse("nps-submit"), {"score": 7})
    assert response.status_code == status.HTTP_403_FORBIDDEN


# ── Summary endpoint ──────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_nps_summary_requires_admin(api_client):
    """Residents cannot access the NPS summary."""
    resident = ResidentFactory()
    api_client.force_authenticate(user=resident)
    response = api_client.get(reverse("nps-summary"))
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_nps_summary_calculates_score(api_client):
    """Admin gets correct NPS score: (promoters - detractors) / total × 100."""
    admin = AdminFactory()
    ward = WardFactory()
    # 3 promoters (9-10), 1 passive (7-8), 1 detractor (0-6)
    scores = [10, 9, 10, 7, 3]
    for i, score in enumerate(scores):
        r = ResidentFactory(ward=ward)
        NPSSurvey.objects.create(
            resident=r,
            score=score,
            next_prompt_at=timezone.now() + timezone.timedelta(days=60)
        )
    api_client.force_authenticate(user=admin)
    response = api_client.get(reverse("nps-summary"))
    assert response.status_code == status.HTTP_200_OK
    data = response.data
    assert data["total_responses"] == 5
    assert data["promoters"] == 3
    assert data["passives"] == 1
    assert data["detractors"] == 1
    # NPS = (3-1)/5 * 100 = 40.0
    assert data["nps_score"] == 40.0
