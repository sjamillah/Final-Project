from django.contrib import admin


class ReadOnlyAdmin(admin.ModelAdmin):
    """Base admin that makes all fields read-only on existing objects."""

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return [f.name for f in obj._meta.get_fields() if hasattr(f, "name")]
        return self.readonly_fields


class TimestampedAdmin(admin.ModelAdmin):
    """Base admin for models with created_at / updated_at — pins them as read-only."""

    readonly_fields = ("created_at",)
