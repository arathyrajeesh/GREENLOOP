import io
import hashlib
import qrcode
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.files.base import ContentFile
from .models import Pickup

@receiver(post_save, sender=Pickup)
def generate_qr_code(sender, instance, created, **kwargs):
    """
    Automatically generate a unique SHA-256 hash and a QR code image
    upon initial creation of a Pickup instance.
    Hash components: pickup_id + resident_id + ward_id + timestamp
    """
    if created and not instance.qr_code:
        # 1. Generate SHA-256 hash
        # pickup_id + resident_id + ward_id + timestamp
        timestamp = instance.created_at.timestamp()
        hash_input = f"{instance.id}{instance.resident_id}{instance.ward_id}{timestamp}"
        qr_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        
        # 2. Generate QR Image
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_hash)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # 3. Save Image to Buffer
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        filename = f"qr_{instance.id}.png"
        
        # 4. Update the instance without triggering save signals again
        instance.qr_code = qr_hash
        # Save the file to the field without calling save() on the model again
        instance.qr_code_image.save(filename, ContentFile(buffer.getvalue()), save=False)
        
        # Use update() to persist both fields safely
        Pickup.objects.filter(pk=instance.pk).update(
            qr_code=qr_hash,
            qr_code_image=instance.qr_code_image.name
        )
