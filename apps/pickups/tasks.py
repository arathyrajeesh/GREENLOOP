from celery import shared_task
import logging
from .models import Pickup

logger = logging.getLogger(__name__)

@shared_task
def flag_pickup_for_review(pickup_id):
    """
    Flags a pickup verification for administrative review if the AI 
    model returns low confidence on the contamination classification.
    """
    try:
        pickup = Pickup.objects.get(id=pickup_id)
        
        if hasattr(pickup, 'verification'):
            pickup.verification.requires_admin_review = True
            pickup.verification.save()
            logger.warning(f"Pickup {pickup_id} flagged for admin review due to low AI confidence.")
        else:
            logger.info(f"Pickup {pickup_id} has no verification to flag.")
            
    except Pickup.DoesNotExist:
        logger.error(f"Pickup {pickup_id} not found when attempting to flag for review.")
    except Exception as e:
        logger.exception(f"Error flagging pickup {pickup_id} for review: {str(e)}")
