import pytest
from django.utils import timezone
from datetime import timedelta
from apps.rewards.utils import calculate_streak
from tests.factories import ResidentFactory, PickupFactory, PickupVerificationFactory, RewardFactory, RewardItemFactory

@pytest.mark.django_db
def test_calculate_streak_empty():
    resident = ResidentFactory()
    assert calculate_streak(resident) == 0

@pytest.mark.django_db
def test_calculate_streak_perfect():
    resident = ResidentFactory()
    now = timezone.now()
    # 4 weeks of perfect segregation
    for i in range(4):
        # Week starts i weeks ago
        week_start = (now - timedelta(days=now.weekday()) - timedelta(weeks=i)).replace(hour=10)
        pickup = PickupFactory(resident=resident, status='completed', completed_at=week_start)
        PickupVerificationFactory(pickup=pickup, contamination_flag=False, verified_at=week_start)
    
    # We expect 4 weeks because the current week also counts if it's clean (or has nothing yet)
    # Wait, my logic: if weeks_back == 0 and count == 0, we continue. 
    # So if we have 4 past weeks of clean data, streak should be 4.
    assert calculate_streak(resident) == 4

@pytest.mark.django_db
def test_calculate_streak_broken_by_contamination():
    resident = ResidentFactory()
    now = timezone.now()
    
    # 2 weeks perfect
    for i in range(2):
        week_start = (now - timedelta(days=now.weekday()) - timedelta(weeks=i)).replace(hour=10)
        pickup = PickupFactory(resident=resident, status='completed', completed_at=week_start)
        PickupVerificationFactory(pickup=pickup, contamination_flag=False, verified_at=week_start)
        
    # 1 week contaminated (3 weeks ago)
    week_start = (now - timedelta(days=now.weekday()) - timedelta(weeks=2)).replace(hour=10)
    pickup = PickupFactory(resident=resident, status='completed', completed_at=week_start)
    PickupVerificationFactory(pickup=pickup, contamination_flag=True, verified_at=week_start)
    
    assert calculate_streak(resident) == 2

@pytest.mark.django_db
def test_calculate_streak_broken_by_inactivity():
    resident = ResidentFactory()
    now = timezone.now()
    
    # 2 weeks perfect
    for i in range(2):
        week_start = (now - timedelta(days=now.weekday()) - timedelta(weeks=i)).replace(hour=10)
        pickup = PickupFactory(resident=resident, status='completed', completed_at=week_start)
        PickupVerificationFactory(pickup=pickup, contamination_flag=False, verified_at=week_start)
        
    # Week 2 (3 weeks ago) is empty -> breaks streak
    
    assert calculate_streak(resident) == 2

@pytest.mark.django_db
def test_reward_summary_api(api_client):
    resident = ResidentFactory()
    api_client.force_authenticate(user=resident)
    
    # Add some rewards to check running_balance
    RewardFactory(resident=resident, points=10) # balance 10
    RewardFactory(resident=resident, points=20) # balance 30
    
    from django.urls import reverse
    url = reverse('reward-summary')
    response = api_client.get(url)
    
    assert response.status_code == 200
    assert response.data['balance'] == 30
    assert 'streak' in response.data
    assert len(response.data['recent_history']) == 2
    assert response.data['recent_history'][0]['running_balance'] == 30
