from django.contrib import admin
from .models import MaterialType, RecyclerPurchase, RecyclingCertificate

@admin.register(MaterialType)
class MaterialTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "unit", "base_price")
    search_fields = ("name",)

@admin.register(RecyclerPurchase)
class RecyclerPurchaseAdmin(admin.ModelAdmin):
    list_display = ("recycler", "material_type", "weight_kg", "amount_paid", "purchase_date")
    list_filter = ("purchase_date", "material_type", "recycler")
    search_fields = ("recycler__email", "recycler__name")

@admin.register(RecyclingCertificate)
class RecyclingCertificateAdmin(admin.ModelAdmin):
    list_display = ("certificate_number", "resident", "recycler", "issued_at")
    list_filter = ("issued_at", "recycler")
    search_fields = ("certificate_number", "resident__email", "resident__name")
    readonly_fields = ("issued_at",)
