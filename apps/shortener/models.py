from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
from django.db.models.functions import Lower

from .managers import URLManager


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = "tags"

    def __str__(self):
        return self.name


class URL(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="urls",
        null=True,
        blank=True,
    )
    original_url = models.URLField(max_length=2048)
    short_code = models.CharField(max_length=10, unique=True)
    custom_alias = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        unique=False,
        validators=[
            RegexValidator(
                regex=r"^[A-Za-z0-9_-]+$",
                message="Custom alias may only contain letters, numbers, hyphens and underscores",
            )
        ],
    )
    title = models.CharField(max_length=255, null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    favicon = models.CharField(max_length=2048, null=True, blank=True)
    click_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name="urls")
    created_at = models.DateTimeField(auto_now_add=True)

    objects = URLManager()

    class Meta:
        db_table = "urls"
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "original_url"],
                name="uniq_owner_original_url",
            ),
            models.UniqueConstraint(
                fields=["original_url"],
                condition=models.Q(owner__isnull=True),
                name="uniq_anon_original_url",
            ),
            # Case-insensitive uniqueness for custom_alias (when provided).
            models.UniqueConstraint(
                Lower("custom_alias"),
                name="uniq_lower_custom_alias",
                condition=models.Q(custom_alias__isnull=False),
            ),
        ]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["click_count"]),
            models.Index(fields=["is_active", "expires_at"]),
            models.Index(fields=["owner", "created_at"]),
        ]

    def __str__(self):
        return f"{self.short_code} -> {self.original_url}"

    @property
    def is_expired(self) -> bool:
        return self.expires_at is not None and self.expires_at <= timezone.now()

    def save(self, *args, **kwargs):
        # Normalise custom_alias to a canonical form for lookup and uniqueness.
        if self.custom_alias:
            self.custom_alias = self.custom_alias.strip().lower()
        super().save(*args, **kwargs)


class Click(models.Model):
    url = models.ForeignKey(URL, on_delete=models.CASCADE, related_name="clicks")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    referrer = models.URLField(max_length=2048, null=True, blank=True)
    clicked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "clicks"
        indexes = [
            models.Index(fields=["url", "clicked_at"]),
        ]

    def __str__(self):
        return f"Click on {self.url.short_code} at {self.clicked_at}"
