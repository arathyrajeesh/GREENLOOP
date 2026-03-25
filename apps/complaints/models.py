from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _

class Complaint(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("IN_PROGRESS", "In Progress"),
        ("RESOLVED", "Resolved"),
        ("REJECTED", "Rejected"),
    )

    CATEGORY_CHOICES = (
        ("PICKUP", "Missed Pickup"),
        ("CLEANLINESS", "Lack of Cleanliness"),
        ("BEHAVIOR", "Staff Behavior"),
        ("PAYMENT", "Payment Issue"),
        ("OTHER", "Other"),
    )

    resident = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="complaints",
        limit_choices_to={'role': 'RESIDENT'}
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField()
    location = models.PointField(null=True, blank=True, help_text="GPS location of the complaint")
    image = models.ImageField(upload_to="complaints/", null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['resident'], name='complaint_resident_idx'),
            models.Index(fields=['status'], name='complaint_status_idx'),
        ]
        verbose_name = _("Complaint")
        verbose_name_plural = _("Complaints")
        ordering = ['-created_at']

    def __str__(self):
        return f"Complaint {self.id} - {self.resident.name} ({self.status})"
