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

    def active(self):
        return self.get_queryset().active()

    def expired(self):
        return self.get_queryset().expired()

    def popular(self, threshold=100):
        return self.get_queryset().popular(threshold)
