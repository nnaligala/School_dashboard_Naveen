from django.contrib import admin

from .models import AttendanceRecord


@admin.register(AttendanceRecord)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("date", "student", "section", "status", "marked_by")
    list_filter = ("status", "date")
