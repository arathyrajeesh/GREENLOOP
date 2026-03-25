from django.contrib import admin
from .models import FeeCollection

@admin.register(FeeCollection)
class FeeCollectionAdmin(admin.ModelAdmin):
    list_display = ("receipt_number", "resident", "amount", "payment_method", "payment_date")
    list_filter = ("payment_method", "payment_date", "collected_by")
    search_fields = ("receipt_number", "resident__email", "resident__name")
    readonly_fields = ("receipt_number", "created_at", "updated_at")
