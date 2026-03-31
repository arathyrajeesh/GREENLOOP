import logging
from celery import shared_task
from django.conf import settings
from apps.pickups.models import Pickup, PickupVerification
from apps.complaints.models import Complaint
from apps.users.models import User
from .models import Notification
from .utils import send_push_notification

logger = logging.getLogger(__name__)

@shared_task
def notify_resident_pickup_assigned(pickup_id):
    """
    Notifies resident when a pickup is assigned.
    """
    try:
        pickup = Pickup.objects.get(id=pickup_id)
        resident = pickup.resident
        title = "Pickup Scheduled"
        body = f"Great news! Your {pickup.get_waste_type_display()} pickup has been assigned for {pickup.scheduled_date} ({pickup.time_slot or 'Anytime'})."
        
        data = {
            "pickup_id": str(pickup.id),
            "type": "PICKUP_ASSIGNED",
            "scheduled_date": str(pickup.scheduled_date),
            "time_slot": pickup.time_slot or ""
        }
        
        send_push_notification(resident, title, body, data=data)
        
        # Internal notification
        Notification.objects.create(user=resident, title=title, message=body)
        
    except Pickup.DoesNotExist:
        logger.error(f"Pickup {pickup_id} not found.")

@shared_task(bind=True, max_retries=5)
def notify_resident_pickup_complete(self, pickup_id):
    """
    Sends a notification with completion photo and points earned.
    """
    try:
        pickup = Pickup.objects.select_related('resident').get(id=pickup_id)
        resident = pickup.resident
        
        # Try to find the reward for points.
        from apps.rewards.models import Reward
        reward = Reward.objects.filter(pickup=pickup, transaction_type='EARNED').first()
        
        # If reward isn't processed yet, retry this task in a few seconds
        if not reward:
            logger.info(f"Reward for pickup {pickup_id} not found yet. Retrying...")
            raise self.retry(countdown=10)
            
        points = reward.points
        
        # Get completion photo
        photo_url = None
        try:
            verification = PickupVerification.objects.get(pickup=pickup)
            if verification.verification_image:
                photo_url = verification.verification_image.url
        except PickupVerification.DoesNotExist:
            logger.warning(f"Verification not found for completed pickup {pickup_id}")
            
        title = "Pickup Completed! 🎉"
        body = f"Thank you! Your waste was collected. You earned {points} GreenLeaf points."
        
        data = {
            "pickup_id": str(pickup.id),
            "type": "PICKUP_COMPLETED",
            "points": str(points),
            "photo_url": photo_url or ""
        }
        
        send_push_notification(resident, title, body, data=data)
        
        # Create internal record
        Notification.objects.create(user=resident, title=title, message=body)
        
    except Pickup.DoesNotExist:
        logger.error(f"Pickup {pickup_id} not found.")
    except Exception as e:
        if "Retrying" in str(e):
             raise e
        logger.exception(f"Error sending completion notification: {str(e)}")

@shared_task(bind=True, max_retries=3)
def send_bulk_notifications(self, user_ids, title, message, extra_data=None):
    """
    Sends notifications to multiple users in batches of 500.
    Retries up to 3 times on failure.
    """
    try:
        batch_size = 500
        total_sent = 0
        
        for i in range(0, len(user_ids), batch_size):
            batch_slice = user_ids[i:i + batch_size]
            users = User.objects.filter(id__in=batch_slice).exclude(fcm_token__isnull=True).exclude(fcm_token="")
            
            for user in users:
                success = send_push_notification(user, title, message, data=extra_data)
                if success:
                    total_sent += 1
                    # Also create internal records for each user
                    Notification.objects.create(user=user, title=title, message=message)
        
        logger.info(f"Bulk notification completed: {total_sent} users notified in batch mode.")
        return total_sent
                
    except Exception as e:
        logger.error(f"Bulk notification failure: {str(e)}")
        # Linear backoff: 60s, 120s, 180s...
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

@shared_task
def notify_admin_new_complaint(complaint_id):
    """
    Notifies all administrators when a new complaint/field issue is reported.
    """
    try:
        complaint = Complaint.objects.get(id=complaint_id)
        admins = User.objects.filter(role='ADMIN')
        
        title = f"New {complaint.get_category_display()}"
        message = f"Reported by {complaint.reporter.name}: {complaint.description[:50]}..."
        
        for admin in admins:
            Notification.objects.create(
                user=admin,
                title=title,
                message=message
            )
            # Try push if they have a token
            if admin.fcm_token:
                send_push_notification(admin, title, message, data={"complaint_id": str(complaint.id)})
            
    except Complaint.DoesNotExist:
        logger.error(f"Complaint {complaint_id} not found.")
    except Exception as e:
        logger.exception(f"Error notifying admins for complaint {complaint_id}: {str(e)}")

@shared_task
def notify_recycler_certificate_verified(certificate_id):
    """
    Notifies recycler when their PoR certificate is verified by admin.
    """
    try:
        from apps.recyclers.models import RecyclingCertificate
        certificate = RecyclingCertificate.objects.get(id=certificate_id)
        recycler = certificate.recycler
        
        title = "Certificate Verified!"
        body = f"Your Proof-of-Recycling certificate #{certificate.certificate_number} has been verified by the administration."
        
        send_push_notification(recycler, title, body, data={"certificate_id": str(certificate.id)})
        
        # Internal record
        Notification.objects.create(user=recycler, title=title, message=body)
        
    except RecyclingCertificate.DoesNotExist:
        logger.error(f"Certificate {certificate_id} not found.")
    except Exception as e:
        logger.exception(f"Error notifying recycler for certificate {certificate_id}: {str(e)}")

@shared_task
def notify_admin_report_ready(report_id):
    """
    Notifies the admin user when their requested report has finished generating.
    """
    try:
        from apps.reports.models import WardCollectionReport
        report = WardCollectionReport.objects.get(id=report_id)
        if report.generated_by:
            title = f"Report {report.status.capitalize()}"
            body = f"The Ward {report.ward.number} Waste Collection Report you requested is now ready."
            if report.status == 'FAILED':
                body = f"The Ward {report.ward.number} Waste Collection Report you requested failed to generate."
                
            send_push_notification(report.generated_by, title, body, data={"report_id": str(report.id)})
            Notification.objects.create(user=report.generated_by, title=title, message=body)
            
    except Exception as e:
        logger.exception(f"Error notifying admin for report {report_id}: {str(e)}")
@shared_task(bind=True, max_retries=3)
def send_fcm_push_task(self, user_id, title, message, extra_data=None):
    """
    Sends a single push notification via US-TASK-01 with retries.
    """
    try:
        user = User.objects.get(id=user_id)
        success = send_push_notification(user, title, message, data=extra_data)
        if success:
             Notification.objects.create(user=user, title=title, message=message)
             return True
        return False
    except Exception as e:
        logger.error(f"FCM push failure for user {user_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60)
