from django.contrib import admin

from apps.core.admin import ReadOnlyAdmin, TimestampedAdmin
from .models import Click, Tag, URL


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(URL)
class URLAdmin(TimestampedAdmin):
    list_display = (
        "short_code",
        "original_url",
        "owner",
        "click_count",
        "is_active",
        "expires_at",
        "created_at",
    )
    list_filter = ("is_active", "tags")
    search_fields = ("short_code", "custom_alias", "original_url", "owner__username")
    readonly_fields = ("short_code", "click_count", "created_at")
    filter_horizontal = ("tags",)
    actions = ["deactivate_urls"]

    @admin.action(description="Deactivate selected URLs")
    def deactivate_urls(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} URL(s) deactivated.")


@admin.register(Click)
class ClickAdmin(ReadOnlyAdmin):
    list_display = ("url", "clicked_at", "ip_address", "country", "city")
    list_filter = ("country",)
    search_fields = ("url__short_code", "ip_address", "country")
