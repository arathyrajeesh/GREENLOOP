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
        ("OVERFLOW", "Overflowing Bins"),
        ("BLOCKED", "Access Blocked"),
        ("UNAVAILABLE", "Resident Unavailable"),
        ("OTHER", "Other"),
    )

    reporter = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="reported_complaints",
        limit_choices_to={'role__in': ['RESIDENT', 'HKS_WORKER']}
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField()
    location = models.PointField(null=True, blank=True, help_text="GPS location of the complaint")
    image = models.ImageField(upload_to="complaints/", null=True, blank=True)
    assigned_to = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_complaints",
        limit_choices_to={'role__in': ['ADMIN', 'HKS_WORKER']}
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['reporter'], name='complaint_reporter_idx'),
            models.Index(fields=['status'], name='complaint_status_idx'),
        ]
        verbose_name = _("Complaint")
        verbose_name_plural = _("Complaints")
        ordering = ['-created_at']

    def __str__(self):
        return f"Complaint {self.id} - {self.reporter.name} ({self.status})"
