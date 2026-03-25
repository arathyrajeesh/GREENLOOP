from django.db import models
from django.utils.translation import gettext_lazy as _

class Reward(models.Model):
    TRANSACTION_TYPES = (
        ("EARNED", "Earned"),
        ("REDEEMED", "Redeemed"),
    )

    resident = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="rewards",
        limit_choices_to={'role': 'RESIDENT'}
    )
    points = models.IntegerField(help_text="Positive for earned, negative for redeemed")
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['resident'], name='reward_resident_idx'),
        ]
        verbose_name = _("Reward")
        verbose_name_plural = _("Rewards")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.resident.name}: {self.points} points ({self.transaction_type})"

class RewardRedemption(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("SHIPPED", "Shipped"),
        ("DELIVERED", "Delivered"),
        ("CANCELLED", "Cancelled"),
    )

    resident = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="redemptions",
        limit_choices_to={'role': 'RESIDENT'}
    )
    reward_item = models.CharField(max_length=255)
    points_spent = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['resident'], name='redemption_resident_idx'),
            models.Index(fields=['status'], name='redemption_status_idx'),
        ]
        verbose_name = _("Reward Redemption")
        verbose_name_plural = _("Reward Redemptions")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.resident.name} redeemed {self.reward_item}"
