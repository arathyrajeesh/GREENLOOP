from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _

class AttendanceLog(models.Model):
    STATUS_CHOICES = (
        ("PRESENT", "Present"),
        ("ABSENT", "Absent"),
        ("LEAVE", "Leave"),
    )

    worker = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="attendance_logs",
        limit_choices_to={'role': 'HKS_WORKER'}
    )
    date = models.DateField()
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    check_in_location = models.PointField(null=True, blank=True, help_text="GPS location at check-in")
    
    # PPE Checklist
    has_gloves = models.BooleanField(default=False)
    has_mask = models.BooleanField(default=False)
    has_vest = models.BooleanField(default=False)
    has_boots = models.BooleanField(default=False)
    
    ppe_selfie = models.ImageField(upload_to="attendance/ppe/", null=True, blank=True)
    ppe_photo_url = models.URLField(max_length=500, null=True, blank=True, help_text="Verifiable remote URL for PPE selfie")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PRESENT")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['worker', 'date'], name='attendance_worker_date_idx'),
        ]
        verbose_name = _("Attendance Log")
        verbose_name_plural = _("Attendance Logs")
        ordering = ['-date', 'worker']

    def __str__(self):
        return f"{self.worker.name} - {self.date} ({self.status})"
