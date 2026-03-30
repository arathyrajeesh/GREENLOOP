from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class ReportCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = _("Report Category")
        verbose_name_plural = _("Report Categories")

    def __str__(self):
        return self.name

class Report(models.Model):
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="reports"
    )
    category = models.ForeignKey(
        ReportCategory,
        on_delete=models.PROTECT,
        related_name="reports"
    )
    title = models.CharField(max_length=255)
    content = models.TextField()
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Report")
        verbose_name_plural = _("Reports")
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class NPSSurvey(models.Model):
    """
    Stores a resident's NPS (Net Promoter Score) survey response.
    - Shown once after 30 days since registration.
    - Cannot be shown again for 60 days after submission.
    """
    resident = models.OneToOneField(
        "users.User",
        on_delete=models.CASCADE,
        related_name="nps_survey",
        limit_choices_to={"role": "RESIDENT"},
    )
    score = models.PositiveSmallIntegerField(
        help_text="NPS score from 0 to 10"
    )
    comment = models.TextField(
        blank=True,
        help_text="Optional qualitative feedback"
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    next_prompt_at = models.DateTimeField(
        help_text="Earliest date the survey can be shown again"
    )

    class Meta:
        verbose_name = _("NPS Survey Response")
        verbose_name_plural = _("NPS Survey Responses")
        indexes = [
            models.Index(fields=["submitted_at"], name="nps_submitted_at_idx"),
        ]

    def save(self, *args, **kwargs):
        if not self.next_prompt_at:
            self.next_prompt_at = timezone.now() + timezone.timedelta(days=60)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"NPS: {self.resident.name} → {self.score}/10"

    @property
    def category(self):
        """Classify score into NPS categories."""
        if self.score >= 9:
            return "promoter"
        elif self.score >= 7:
            return "passive"
        return "detractor"

class WardCollectionReport(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
    )

    ward = models.ForeignKey(
        "wards.Ward",
        on_delete=models.CASCADE,
        related_name="collection_reports"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    pdf_file = models.FileField(upload_to="reports/pdfs/", null=True, blank=True)
    csv_file = models.FileField(upload_to="reports/csvs/", null=True, blank=True)
    generated_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        limit_choices_to={'role': 'ADMIN'}
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("Ward Collection Report")
        verbose_name_plural = _("Ward Collection Reports")
        ordering = ['-created_at']

    def __str__(self):
        return f"Report for {self.ward.name} ({self.start_date} to {self.end_date})"
