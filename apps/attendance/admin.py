from django.contrib import admin
from .models import AttendanceLog

@admin.register(AttendanceLog)
class AttendanceLogAdmin(admin.ModelAdmin):
    list_display = ("worker", "date", "check_in", "check_out", "status")
    list_filter = ("date", "status", "worker")
    search_fields = ("worker__email", "worker__name")
