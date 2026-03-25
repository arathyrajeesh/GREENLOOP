import uuid
from django.contrib.gis.db import models
from django.utils import timezone

class Pickup(models.Model):
    WASTE_CHOICES = (
        ('dry', 'Dry Waste'),
        ('wet', 'Wet Waste'),
        ('hazardous', 'Hazardous Waste'),
        ('e-waste', 'E-Waste'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('arrived', 'Arrived'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resident = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="pickups")
    ward = models.ForeignKey("wards.Ward", on_delete=models.CASCADE, related_name="pickups")
    location = models.PointField(help_text="GPS location of the pickup point")
    waste_type = models.CharField(max_length=20, choices=WASTE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    scheduled_date = models.DateField(default=timezone.now)
    qr_code = models.CharField(max_length=64, unique=True, blank=True, null=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['ward', 'scheduled_date', 'status'], name='pickup_ward_date_status_idx'),
        ]

    def __str__(self):
        return f"Pickup {self.id} ({self.status})"

class PickupVerification(models.Model):
    pickup = models.OneToOneField(Pickup, on_delete=models.CASCADE, related_name="verification")
    verified_by = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="verified_pickups",
        limit_choices_to={'role': 'HKS_WORKER'}
    )
    verified_at = models.DateTimeField(auto_now_add=True)
    verification_image = models.ImageField(upload_to="pickups/verifications/", null=True, blank=True)
    comments = models.TextField(blank=True)

    class Meta:
        verbose_name = "Pickup Verification"
        verbose_name_plural = "Pickup Verifications"

    def __str__(self):
        return f"Verification for Pickup {self.pickup.id}"
