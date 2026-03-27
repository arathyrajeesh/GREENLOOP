import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import OTPCode

logger = logging.getLogger(__name__)

@shared_task
def cleanup_expired_otps():
    """
    Deletes OTPCode records older than 24 hours.
    Logged for monitoring as per requirements.
    """
    threshold = timezone.now() - timedelta(hours=24)
    expired_otps = OTPCode.objects.filter(created_at__lt=threshold)
    count = expired_otps.count()
    
    if count > 0:
        expired_otps.delete()
        logger.info(f"Deleted {count} expired OTP codes.")
        return f"Deleted {count} expired OTP codes."
    
    return "No expired OTP codes to delete."
