import pytest
from django.urls import reverse
from rest_framework import status
from tests.factories import ResidentFactory, PickupFactory

@pytest.mark.django_db
class TestRewardViewSet:
    def test_list_rewards(self, authenticated_client, resident_user):
        from apps.rewards.models import Reward
        Reward.objects.create(resident=resident_user, points=10, transaction_type='EARNED', description='Test')
        url = reverse('reward-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK

@pytest.mark.django_db
class TestRewardTasks:
    @pytest.mark.celery(CELERY_TASK_ALWAYS_EAGER=True)
    def test_award_greenleaf_points_clean(self, resident_user, ward):
        from apps.rewards.tasks import award_greenleaf_points
        from apps.rewards.models import Reward
        pickup = PickupFactory(resident=resident_user, ward=ward, status='completed')
        # Create verification
        from apps.pickups.models import PickupVerification
        PickupVerification.objects.create(
            pickup=pickup, verified_by=ResidentFactory(role='HKS_WORKER'),
            ai_classification='clean'
        )
        
        award_greenleaf_points(pickup.id)
        assert Reward.objects.filter(resident=resident_user, points=10).exists()
