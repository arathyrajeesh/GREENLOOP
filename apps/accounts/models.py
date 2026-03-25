from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.utils.translation import gettext_lazy as _

class OTPCode(models.Model):
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="otp_codes"
    )
    code = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    failed_attempts = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=['user', 'code'], name='otp_user_code_idx'),
        ]
        verbose_name = _("OTP Code")
        verbose_name_plural = _("OTP Codes")
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at and self.failed_attempts < 5

    def __str__(self):
        return f"OTP for {self.user.email}"
