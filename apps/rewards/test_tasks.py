import pytest
from apps.rewards.tasks import award_greenleaf_points
from apps.rewards.models import Reward
from tests.factories import PickupFactory

@pytest.mark.django_db
def test_award_greenleaf_points_success():
    pickup = PickupFactory(status='completed', waste_type='dry')
    # Use 10kg to ensure points are awarded
    pickup.weight_kg = 10.5
    pickup.save()
    
    # Task is called in save() but we can call it manually to test logic
    award_greenleaf_points(pickup.id)
    
    rewards = Reward.objects.filter(resident=pickup.resident)
    assert rewards.exists()
    # Logic awards a flat 10 points for clean waste as per current implementation
    assert rewards.first().points == 10

@pytest.mark.django_db
def test_award_greenleaf_points_idempotency():
    pickup = PickupFactory(status='completed', weight_kg=5)
    
    # Call twice
    award_greenleaf_points(pickup.id)
    award_greenleaf_points(pickup.id)
    
    assert Reward.objects.filter(resident=pickup.resident).count() == 1
