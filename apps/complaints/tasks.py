from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Complaint
from apps.notifications.models import Notification
from apps.notifications.tasks import send_fcm_push
from apps.users.models import User

@shared_task
def check_pending_complaints():
    """
    Auto-escalates complaints unresolved for 48+ hours.
    Unresolved = submitted, assigned, or in-progress.
    """
    threshold = timezone.now() - timedelta(hours=48)
    pending_complaints = Complaint.objects.filter(
        status__in=['submitted', 'assigned'],  # Adjusted to strictly match AC
        created_at__lt=threshold,
        is_escalated=False
    )
    
    admins = User.objects.filter(role='ADMIN')
    count = 0
    
    for complaint in pending_complaints:
        complaint.is_escalated = True
        # Bump priority to Urgent (4)
        complaint.priority = 4 
        complaint.save()
        
        # Notify admins (Database & Push)
        for admin in admins:
            Notification.objects.create(
                user=admin,
                title="Complaint Auto-Escalation",
                message=f"Complaint {complaint.id} ({complaint.get_category_display()}) has been unresolved for 48+ hours and is now escalated."
            )
            # Push via US-TASK-01
            if admin.fcm_token:
                send_fcm_push(
                    admin, 
                    "Urgent: Complaint Escalated", 
                    f"Complaint {complaint.id} ({complaint.category}) is now escalated."
                )
        count += 1
        
    return f"Escalated {count} complaints."
