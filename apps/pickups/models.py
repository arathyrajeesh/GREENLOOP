import uuid
from django.contrib.gis.db import models
from django.utils import timezone

class Pickup(models.Model):
    WASTE_CHOICES = (
        ('dry', 'Dry Waste'),
        ('wet', 'Wet Waste'),
        ('hazardous', 'Hazardous Waste'),
        ('e-waste', 'E-Waste'),
        ('biomedical', 'Biomedical Waste'),
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
    time_slot = models.CharField(max_length=50, blank=True, null=True, help_text="e.g., '10:00-12:00'")
    notes = models.TextField(blank=True, help_text="Mandatory note if GPS override was used")

    @property
    def scheduled_datetime(self):
        """
        Attempts to parse the start time from `time_slot` (e.g. '10:00-12:00' -> 10:00) 
        and combine it with `scheduled_date`. If it fails or is missing, defaults to 00:00 of that date.
        """
        from datetime import datetime
        import re
        
        start_time = "00:00"
        if self.time_slot:
            # Look for HR:MIN pattern
            match = re.search(r'(\d{1,2}:\d{2})', self.time_slot)
            if match:
                start_time = match.group(1)
                
        time_format = "%H:%M"
        try:
            parsed_time = datetime.strptime(start_time, time_format).time()
        except ValueError:
            parsed_time = datetime.min.time()
            
        dt_naive = datetime.combine(self.scheduled_date, parsed_time)
        return timezone.make_aware(dt_naive)
    qr_code = models.CharField(max_length=64, unique=True, blank=True, null=True)
    weight_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Estimated weight of waste collected")
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.qr_code:
            import hashlib
            hash_input = f"{self.id}{self.resident_id}{self.ward_id}{timezone.now().timestamp()}"
            self.qr_code = hashlib.sha256(hash_input.encode()).hexdigest()
            
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
    waste_photo_url = models.URLField(max_length=500, null=True, blank=True)
    ai_classification = models.CharField(max_length=50, blank=True)
    contamination_confidence = models.FloatField(null=True, blank=True)
    requires_admin_review = models.BooleanField(default=False)
    distance_meters = models.FloatField(null=True, blank=True)
    is_gps_override = models.BooleanField(default=False)
    comments = models.TextField(blank=True)

    class Meta:
        verbose_name = "Pickup Verification"
        verbose_name_plural = "Pickup Verifications"

    def __str__(self):
        return f"Verification for Pickup {self.pickup.id}"
