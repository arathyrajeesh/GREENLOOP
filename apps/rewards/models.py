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
    pickup = models.ForeignKey(
        "pickups.Pickup",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rewards"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    running_balance = models.IntegerField(default=0, help_text="Total balance after this transaction")

    class Meta:
        indexes = [
            models.Index(fields=['resident'], name='reward_resident_idx'),
        ]
        verbose_name = _("Reward")
        verbose_name_plural = _("Rewards")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.resident.name}: {self.points} points ({self.transaction_type})"

    def save(self, *args, **kwargs):
        if not self.pk:
            # Calculate running balance based on current total
            last_balance = Reward.objects.filter(resident=self.resident).aggregate(models.Sum('points'))['points__sum'] or 0
            self.running_balance = last_balance + self.points
        super().save(*args, **kwargs)

class RewardItem(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    points_cost = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Reward Item")
        verbose_name_plural = _("Reward Items")
        ordering = ['points_cost']

    def __str__(self):
        return f"{self.name} ({self.points_cost} points)"

class RewardSettings(models.Model):
    clean_pickup_points = models.PositiveIntegerField(default=10)
    contaminated_pickup_points = models.PositiveIntegerField(default=5)
    streak_bonus_points = models.PositiveIntegerField(default=50)
    streak_threshold_weeks = models.PositiveIntegerField(default=4)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Reward Settings")
        verbose_name_plural = _("Reward Settings")

    def __str__(self):
        return "Global Reward Settings"

    @classmethod
    def get_settings(cls):
        obj, created = cls.objects.get_or_create(id=1)
        return obj

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
