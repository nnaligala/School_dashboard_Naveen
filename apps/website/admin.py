from django.contrib import admin

from .models import Enquiry


@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ("created_at", "name", "email", "handled")
    list_filter = ("handled",)
    search_fields = ("name", "email")
