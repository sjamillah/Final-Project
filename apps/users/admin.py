from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "tier", "is_premium", "is_staff", "is_active")
    list_filter = ("tier", "is_staff", "is_active")
    search_fields = ("username", "email")
    ordering = ("username",)

    fieldsets = BaseUserAdmin.fieldsets + (("Tier & Access", {"fields": ("tier",)}),)
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Tier & Access", {"fields": ("tier",)}),
    )
