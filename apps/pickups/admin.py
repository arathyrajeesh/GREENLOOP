from django.contrib.gis import admin
from .models import Pickup, PickupVerification

@admin.register(Pickup)
class PickupAdmin(admin.GISModelAdmin):
    list_display = ("id", "resident", "waste_type", "status", "scheduled_date")
    list_filter = ("status", "waste_type", "scheduled_date")
    search_fields = ("resident__email", "resident__name", "qr_code")

@admin.register(PickupVerification)
class PickupVerificationAdmin(admin.ModelAdmin):
    list_display = ("pickup", "verified_by", "verified_at")
    list_filter = ("verified_at", "verified_by")
    search_fields = ("pickup__id", "verified_by__email")
