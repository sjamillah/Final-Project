from django.db import models  # type: ignore[reportMissingImports]
from django.utils import timezone  # type: ignore[reportMissingImports]


class URLQuerySet(models.QuerySet):

    def active(self):
        return self.filter(
            is_active=True,
        ).filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=timezone.now())
        )

    def expired(self):
        return self.filter(
            models.Q(is_active=False) | models.Q(expires_at__lte=timezone.now())
        )

    def popular(self, threshold=100):
        return self.filter(click_count__gte=threshold).order_by("-click_count")


class URLManager(models.Manager):

    def get_queryset(self):
        return URLQuerySet(self.model, using=self._db)

    def active_urls(self):
        return self.get_queryset().active()

    def expired_urls(self):
        return self.get_queryset().expired()

    def popular_urls(self, threshold=100):
        return self.get_queryset().popular(threshold)

    def active(self):
        return self.active_urls()

    def expired(self):
        return self.expired_urls()

    def popular(self, threshold=100):
        return self.popular_urls(threshold)

    def get_or_create_by_original(self, original_url: str, owner=None):
        """Convenience helper to get or create a URL by its original URL and owner.

        This performs a simple `get_or_create` with a generated `short_code` default.
        It does not attempt sophisticated retry handling for short-code collisions;
        callers that need stronger guarantees should use a transactional write
        in the service layer.
        """
        import secrets
        import string

        CODE_LENGTH = 6

        def _gen_code() -> str:
            alphabet = string.ascii_letters + string.digits
            return "".join(secrets.choice(alphabet) for _ in range(CODE_LENGTH))

        defaults = {"short_code": _gen_code()}
        return self.get_or_create(
            original_url=original_url, owner=owner, defaults=defaults
        )
