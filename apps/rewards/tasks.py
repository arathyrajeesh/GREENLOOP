from celery import shared_task
import logging
from apps.pickups.models import Pickup
from .models import Reward, RewardSettings
from .utils import calculate_streak

logger = logging.getLogger(__name__)

@shared_task
def award_greenleaf_points(pickup_id):
    """
    Awards GreenLeaf points to a resident for a successfully completed pickup.
    Points are dynamically awarded based on the waste classification.
    """
    try:
        pickup = Pickup.objects.get(id=pickup_id)
        resident = pickup.resident
        
        # Check if a reward already exists for this pickup (idempotency)
        if Reward.objects.filter(pickup=pickup, transaction_type="EARNED").exists():
            logger.info(f"Points already awarded for pickup {pickup_id}")
            return
            
        # Fetch reward settings
        settings = RewardSettings.get_settings()
        points = settings.clean_pickup_points
        
        # Check contamination flag if verification exists
        if hasattr(pickup, 'verification'):
            if pickup.verification.contamination_flag:
                points = settings.contaminated_pickup_points
                
        Reward.objects.create(
            resident=resident,
            pickup=pickup,
            points=points,
            transaction_type="EARNED",
            description=f"GreenLeaf Points for Pickup {pickup.id} ({'Clean' if points == 10 else 'Contaminated'})"
        )
        logger.info(f"Awarded {points} points to {resident.email} for pickup {pickup_id}")

        # Check for streak milestone bonus
        streak = calculate_streak(resident)
        if streak >= settings.streak_threshold_weeks:
            bonus_desc = f"{settings.streak_threshold_weeks}-week Perfect Segregation Streak Bonus!"
            if not Reward.objects.filter(resident=resident, description=bonus_desc).exists():
                Reward.objects.create(
                    resident=resident,
                    points=settings.streak_bonus_points,
                    transaction_type="EARNED",
                    description=bonus_desc
                )
                logger.info(f"Awarded {settings.streak_threshold_weeks}-week streak bonus to {resident.email}")
            
    except Pickup.DoesNotExist:
        logger.error(f"Pickup {pickup_id} not found when awarding points.")
    except Exception as e:
        logger.exception(f"Error awarding points for pickup {pickup_id}: {str(e)}")
