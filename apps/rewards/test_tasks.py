import pytest
from apps.rewards.tasks import award_greenleaf_points
from apps.rewards.models import Reward
from tests.factories import PickupFactory, PickupVerificationFactory

@pytest.mark.django_db
def test_award_greenleaf_points_clean_waste():
    from apps.pickups.models import PickupVerification
    pickup = PickupFactory(status='completed')
    PickupVerificationFactory(pickup=pickup, contamination_flag=False)
    
    award_greenleaf_points(pickup.id)
    
    rewards = Reward.objects.filter(pickup=pickup)
    assert rewards.exists()
    assert rewards.first().points == 10

@pytest.mark.django_db
def test_award_greenleaf_points_contaminated_waste():
    from apps.pickups.models import PickupVerification
    pickup = PickupFactory(status='completed')
    PickupVerificationFactory(pickup=pickup, contamination_flag=True)
    
    award_greenleaf_points(pickup.id)
    
    rewards = Reward.objects.filter(pickup=pickup)
    assert rewards.exists()
    assert rewards.first().points == 5

@pytest.mark.django_db
def test_award_greenleaf_points_idempotency():
    pickup = PickupFactory(status='completed', weight_kg=5)
    
    # Call twice
    award_greenleaf_points(pickup.id)
    award_greenleaf_points(pickup.id)
    
    assert Reward.objects.filter(resident=pickup.resident).count() == 1
