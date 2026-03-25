from django.db import models
from django.utils.translation import gettext_lazy as _

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
