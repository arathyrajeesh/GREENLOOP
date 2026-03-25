from django.contrib.gis import admin
from .models import AttendanceLog

@admin.register(AttendanceLog)
class AttendanceLogAdmin(admin.GISModelAdmin):
    list_display = ("worker", "date", "status", "check_in", "has_gloves", "has_mask", "has_vest", "has_boots")
    list_filter = ("status", "date", "has_gloves", "has_mask", "has_vest", "has_boots")
    search_fields = ("worker__email", "worker__name")
