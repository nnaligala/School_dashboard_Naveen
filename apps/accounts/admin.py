from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import LoginHistory, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("email",)
    list_display = ("email", "full_name", "role", "is_active", "is_locked")
    list_filter = ("role", "is_active")
    search_fields = ("email", "first_name", "last_name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("first_name", "last_name", "phone", "role")}),
        ("Security", {"fields": ("must_change_password", "failed_login_count", "locked_until")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "first_name", "role", "password1", "password2")}),
    )
    readonly_fields = ("failed_login_count",)


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ("created_at", "email_attempted", "success", "ip_address")
    list_filter = ("success",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
