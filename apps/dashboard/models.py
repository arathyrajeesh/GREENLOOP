from django.db import models
from django.utils.translation import gettext_lazy as _

class SyncQueue(models.Model):
    ACTION_CHOICES = (
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DELETE", "Delete"),
    )

    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    payload = models.JSONField(default=dict, blank=True)
    is_synced = models.BooleanField(default=False)
    synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['is_synced'], name='sync_pending_idx'),
            models.Index(fields=['model_name', 'object_id'], name='sync_obj_idx'),
        ]
        verbose_name = _("Sync Queue Item")
        verbose_name_plural = _("Sync Queue Items")
        ordering = ['created_at']

    def __str__(self):
        return f"{self.action} {self.model_name}:{self.object_id} (Synced: {self.is_synced})"
