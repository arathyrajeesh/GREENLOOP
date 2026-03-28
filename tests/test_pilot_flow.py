import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from django.core.management import call_command
from apps.users.models import User
from apps.wards.models import Ward
from apps.pickups.models import Pickup
from apps.rewards.models import Reward
import os

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db(transaction=True)
def test_end_to_end_pilot_flow(api_client, settings):
    # Enable eager celery for signal testing
    settings.CELERY_TASK_ALWAYS_EAGER = True
    
    # 0. Seed data for the test
    call_command("seed_wards", "data/pilot_wards.json")
    call_command("onboard_pilot_users")
    
    # 1. GIVEN Resident and Worker from seeded data (Match Wards)
    # resident4 is in Ward 1, worker1 is in Ward 1
    resident = User.objects.get(email="resident4@example.com")
    worker = User.objects.get(email="worker1@greenloop.org")
    assert resident.ward == worker.ward
    
    # 2. WHEN Resident books a pickup
    api_client.force_authenticate(user=resident)
    booking_url = reverse("pickup-list")
    booking_data = {
        "waste_type": "dry",
        "location": {
            "type": "Point",
            "coordinates": [76.9634, 8.5284]
        },
        "scheduled_date": "2026-04-01",
        "time_slot": "10:00-12:00"
    }
    response = api_client.post(booking_url, booking_data, format='json')
    assert response.status_code == status.HTTP_201_CREATED, response.data
    pickup_id = response.data["id"]
    
    # 3. AND Worker accepts and completes the pickup
    api_client.force_authenticate(user=worker)
    complete_url = reverse("pickup-complete", kwargs={"pk": pickup_id})
    complete_data = {
        "weight_kg": 5.5,
        "waste_photo_url": "http://example.com/waste.jpg",
        "distance_meters": 10.5
    }
    response = api_client.patch(complete_url, complete_data)
    assert response.status_code == status.HTTP_200_OK
    
    # 4. THEN Verify Greenleaf points are awarded
    pickup = Pickup.objects.get(id=pickup_id)
    assert pickup.status == "completed"
    assert pickup.completed_at is not None
    
    rewards = Reward.objects.filter(resident=resident)
    assert rewards.exists()
    assert rewards.count() == 1
    assert "GreenLeaf" in rewards.first().description
    print(f"Points awarded: {rewards.first().points}")
