import requests
from django.conf import settings
from celery import shared_task
import logging
from apps.pickups.models import Pickup
from apps.complaints.models import Complaint
from apps.users.models import User
from .models import Notification

logger = logging.getLogger(__name__)

def send_fcm_push(user, title, body, data=None):
    """
    Helper to send a single FCM push notification.
    Clears the fcm_token if it's invalid.
    """
    if not user.fcm_token:
        logger.warning(f"No FCM token for user {user.id}")
        return False
        
    # FCM API Configuration (Mocked/Simulation as per requirements)
    fcm_url = "https://fcm.googleapis.com/fcm/send"
    headers = {
        "Authorization": f"key={getattr(settings, 'FCM_SERVER_KEY', 'mock_key')}",
        "Content-Type": "application/json"
    }
    payload = {
        "to": user.fcm_token,
        "notification": {
            "title": title,
            "body": body
        },
        "data": data or {}
    }
    
    try:
        # In a real scenario, we'd use firebase-admin or requests
        # Simulation: randomly fail for testing invalid token clearing logic
        if user.fcm_token == "invalid_token":
             raise ValueError("NotRegistered")
             
        logger.info(f"[FCM] Sending to {user.fcm_token}: {title} - {body}")
        # response = requests.post(fcm_url, json=payload, headers=headers, timeout=5)
        # response_data = response.json()
        
        # Check for invalid token errors (mocked logic)
        # if response_data.get('failure') and 'NotRegistered' in str(response_data):
        #     user.fcm_token = None
        #     user.save()
        return True
    except (ValueError, Exception) as e:
        if "NotRegistered" in str(e) or "InvalidRegistration" in str(e):
            logger.error(f"Invalid FCM token for user {user.id}, clearing token.")
            user.fcm_token = None
            user.save()
        else:
            logger.error(f"Error sending FCM push: {str(e)}")
        return False

@shared_task
def notify_resident_pickup_assigned(pickup_id):
    """
    Notifies resident when a pickup is assigned (accepted).
    """
    try:
        pickup = Pickup.objects.get(id=pickup_id)
        resident = pickup.resident
        title = "Pickup Assigned"
        body = f"Your pickup for {pickup.waste_type} has been scheduled for {pickup.scheduled_date} at {pickup.time_slot or 'anytime'}."
        
        send_fcm_push(resident, title, body, data={"pickup_id": str(pickup.id)})
        
        # Also create internal notification
        Notification.objects.create(user=resident, title=title, message=body)
        
    except Pickup.DoesNotExist:
        logger.error(f"Pickup {pickup_id} not found.")

@shared_task
def notify_resident_pickup_complete(pickup_id):
    """
    Sends an FCM (Firebase Cloud Messaging) push notification to the resident
    informing them that their pickup was successfully completed.
    """
    try:
        pickup = Pickup.objects.get(id=pickup_id)
        resident = pickup.resident
        
        points = 0
        from apps.rewards.models import Reward
        reward = Reward.objects.filter(resident=resident, description__icontains=str(pickup.id)).first()
        if reward:
            points = reward.points
            
        title = "Pickup Completed!"
        body = f"Thank you! Your waste was collected. You earned {points} points."
        
        # In a real app, we'd add the verification photo URL to 'data'
        data = {
            "pickup_id": str(pickup.id),
            "points": points
        }
        
        send_fcm_push(resident, title, body, data=data)
        
        # Create internal record
        Notification.objects.create(user=resident, title=title, message=body)
        
    except Pickup.DoesNotExist:
        logger.error(f"Pickup {pickup_id} not found.")
    except Exception as e:
        logger.exception(f"Error sending completion notification: {str(e)}")

@shared_task(bind=True, max_retries=3)
def send_bulk_notifications(self, user_ids, title, message):
    """
    Sends notifications to multiple users in batches of 500.
    """
    try:
        batch_size = 500
        for i in range(0, len(user_ids), batch_size):
            batch_ids = user_ids[i:i + batch_size]
            users = User.objects.filter(id__in=batch_ids).exclude(fcm_token__isnull=True).exclude(fcm_token="")
            
            for user in users:
                send_fcm_push(user, title, message)
                
    except Exception as e:
        logger.error(f"Bulk notification error: {str(e)}")
        raise self.retry(exc=e, countdown=60)

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
            # Try push if they have a token
            if admin.fcm_token:
                send_fcm_push(admin, "New Complaint Reported", f"{complaint.reporter.name} reported a {complaint.category}")
            
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
        
        send_fcm_push(recycler, title, body, data={"certificate_id": str(certificate.id)})
        
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
                
            send_fcm_push(report.generated_by, title, body, data={"report_id": str(report.id)})
            Notification.objects.create(user=report.generated_by, title=title, message=body)
            
    except Exception as e:
        logger.exception(f"Error notifying admin for report {report_id}: {str(e)}")
