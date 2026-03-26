from celery import shared_task
import logging
from apps.pickups.models import Pickup
from apps.rewards.models import Reward

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
        # Using description to match for now, could add a generic relation or fk later
        description = f"GreenLeaf Points for Pickup {pickup.id}"
        if Reward.objects.filter(resident=resident, description=description).exists():
            logger.info(f"Points already awarded for pickup {pickup_id}")
            return
            
        points = 10 # Default for clean waste
        
        # Adjust points based on AI classification if available
        if hasattr(pickup, 'verification'):
            if pickup.verification.ai_classification == 'contaminated':
                points = 0
            elif pickup.verification.ai_classification == 'mixed':
                points = 5
                
        if points > 0:
            Reward.objects.create(
                resident=resident,
                points=points,
                transaction_type="EARNED",
                description=description
            )
            logger.info(f"Awarded {points} points to {resident.email} for pickup {pickup_id}")
        else:
            logger.info(f"No points awarded for pickup {pickup_id} due to contamination")
            
    except Pickup.DoesNotExist:
        logger.error(f"Pickup {pickup_id} not found when awarding points.")
    except Exception as e:
        logger.exception(f"Error awarding points for pickup {pickup_id}: {str(e)}")
