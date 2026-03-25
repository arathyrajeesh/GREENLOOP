from django.contrib import admin
from .models import SyncQueue

@admin.register(SyncQueue)
class SyncQueueAdmin(admin.ModelAdmin):
    list_display = ("model_name", "object_id", "action", "is_synced", "created_at")
    list_filter = ("is_synced", "action", "model_name")
    search_fields = ("model_name", "object_id")
    readonly_fields = ("created_at",)
