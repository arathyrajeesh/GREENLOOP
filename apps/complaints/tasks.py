from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Complaint
from apps.notifications.tasks import send_fcm_push_task
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
        
        # Notify admins via US-TASK-01
        title = "Urgent: Complaint Escalated"
        message = f"Complaint #{complaint.id} ({complaint.get_category_display()}) is now escalated due to inactivity."
        
        for admin in admins:
            # Task handles both database record and push
            send_fcm_push_task.delay(
                str(admin.id), 
                title, 
                message, 
                extra_data={"complaint_id": str(complaint.id), "type": "ESCALATION"}
            )
        count += 1
        
    return f"Escalated {count} complaints."
