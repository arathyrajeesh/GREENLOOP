from celery import shared_task
import logging
from apps.pickups.models import Pickup

logger = logging.getLogger(__name__)

@shared_task
def notify_resident_pickup_complete(pickup_id):
    """
    Sends an FCM (Firebase Cloud Messaging) push notification to the resident
    informing them that their pickup was successfully completed.
    """
    try:
        pickup = Pickup.objects.get(id=pickup_id)
        resident = pickup.resident
        
        # TODO: Implement actual FCM device token targeting using firebase-admin
        # For now, simulate the notification via logs.
        logger.info(f"[FCM SIMULATION] Sending 'Pickup Completed' notification to resident: {resident.email} (Pickup: {pickup_id})")
        
    except Pickup.DoesNotExist:
        logger.error(f"Pickup {pickup_id} not found when sending notification.")
    except Exception as e:
        logger.exception(f"Error sending completion notification for pickup {pickup_id}: {str(e)}")
