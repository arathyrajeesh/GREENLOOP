from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class FeeCollection(models.Model):
    PAYMENT_METHODS = (
        ("CASH", "Cash"),
        ("UPI", "UPI / Digital"),
        ("BANK_TRANSFER", "Bank Transfer"),
    )

    resident = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="fee_collections",
        limit_choices_to={'role': 'RESIDENT'}
    )
    ward = models.ForeignKey(
        "wards.Ward",
        on_delete=models.CASCADE,
        related_name="fee_collections",
        null=True,
        blank=True
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default="CASH")
    receipt_number = models.CharField(max_length=25, unique=True, db_index=True)
    payment_date = models.DateTimeField(default=timezone.now)
    collected_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="collections_made",
        limit_choices_to={'role': 'HKS_WORKER'}
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['receipt_number'], name='fee_receipt_idx'),
            models.Index(fields=['resident', 'payment_date'], name='fee_res_date_idx'),
        ]
        verbose_name = _("Fee Collection")
        verbose_name_plural = _("Fee Collections")
        ordering = ['-payment_date']

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            date_str = timezone.now().strftime("%Y%m%d")
            prefix = f"FC-{date_str}-"
            
            # Find the last receipt number for today
            last_receipt = FeeCollection.objects.filter(
                receipt_number__startswith=prefix
            ).order_by('receipt_number').last()
            
            if last_receipt:
                last_num = int(last_receipt.receipt_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.receipt_number = f"{prefix}{new_num:04d}"
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.receipt_number} - {self.resident.name} ({self.amount})"
