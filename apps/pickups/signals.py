import hashlib
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Pickup

@receiver(post_save, sender=Pickup)
def generate_qr_code(sender, instance, created, **kwargs):
    """
    Automatically generate a unique SHA-256 hash for the QR code field 
    upon initial creation of a Pickup instance.
    """
    if created and not instance.qr_code:
        # Generate hash based on ID and timestamp for uniqueness
        hash_input = f"{instance.id}-{instance.created_at}"
        instance.qr_code = hashlib.sha256(hash_input.encode()).hexdigest()
        # Use update_fields to avoid recursion and re-running signals or save logic
        instance.save(update_fields=['qr_code'])
