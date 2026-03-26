from celery import shared_task
import logging
from apps.pickups.models import Pickup
from apps.complaints.models import Complaint
from apps.users.models import User
from .models import Notification

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

@shared_task
def notify_admin_new_complaint(complaint_id):
    """
    Notifies all administrators when a new complaint/field issue is reported.
    """
    try:
        complaint = Complaint.objects.get(id=complaint_id)
        admins = User.objects.filter(role='ADMIN')
        
        for admin in admins:
            Notification.objects.create(
                user=admin,
                title=f"New {complaint.get_category_display()}",
                message=f"Reported by {complaint.reporter.name}: {complaint.description[:50]}..."
            )
            logger.info(f"Notification created for admin: {admin.email} (Complaint: {complaint_id})")
            
    except Complaint.DoesNotExist:
        logger.error(f"Complaint {complaint_id} not found.")
    except Exception as e:
        logger.exception(f"Error notifying admins for complaint {complaint_id}: {str(e)}")
