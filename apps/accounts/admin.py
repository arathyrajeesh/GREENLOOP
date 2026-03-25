from django.contrib import admin
from .models import OTPCode

@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    list_display = ("user", "code", "is_used", "expires_at", "created_at")
    list_filter = ("is_used", "created_at")
    search_fields = ("user__email", "user__name", "code")
