from django.db import models
from django.utils.translation import gettext_lazy as _

class MaterialType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=50, blank=True, help_text="e.g., Plastic, Paper, Metal")
    unit = models.CharField(max_length=20, default="kg")
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = _("Material Type")
        verbose_name_plural = _("Material Types")

    def __str__(self):
        return self.name

class RecyclerPurchase(models.Model):
    recycler = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="purchases",
        limit_choices_to={'role': 'RECYCLER'}
    )
    material_type = models.ForeignKey(MaterialType, on_delete=models.PROTECT)
    weight_kg = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    source_ward = models.ForeignKey(
        "wards.Ward",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recycler_purchases"
    )
    purchase_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['recycler', 'purchase_date'], name='purchase_recycler_date_idx'),
        ]
        verbose_name = _("Recycler Purchase")
        verbose_name_plural = _("Recycler Purchases")
        ordering = ['-purchase_date']

    def __str__(self):
        return f"{self.recycler.name} bought {self.weight_kg} {self.material_type.unit} of {self.material_type.name}"

class RecyclingCertificate(models.Model):
    resident = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="recycling_certificates",
        limit_choices_to={'role': 'RESIDENT'},
        null=True,
        blank=True
    )
    recycler = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="issued_certificates",
        limit_choices_to={'role': 'RECYCLER'}
    )
    certificate_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(
        max_length=20, 
        choices=[('PENDING', 'Pending'), ('VERIFIED', 'Verified'), ('REJECTED', 'Rejected')], 
        default='PENDING'
    )
    certificate_file = models.FileField(upload_to='certificates/', blank=True, null=True)
    purchases = models.ManyToManyField(RecyclerPurchase, related_name='certificates')
    issued_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['certificate_number'], name='cert_number_idx'),
            models.Index(fields=['resident'], name='cert_resident_idx'),
        ]
        verbose_name = _("Recycling Certificate")
        verbose_name_plural = _("Recycling Certificates")
        ordering = ['-issued_at']

    def __str__(self):
        name = self.resident.name if self.resident else "Recycler Account"
        return f"Cert {self.certificate_number} for {name}"
