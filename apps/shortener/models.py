from django.db import models


class URLManager(models.Manager):
    def get_by_code(self, code: str):
        return self.filter(short_code=code).first()

    def create_unique(self, original_url: str, short_code: str):
        # thin wrapper for explicit intent; transactions handled in services
        return self.create(original_url=original_url, short_code=short_code)

    def get_or_create_by_original(self, original_url: str, short_code: str):
        """Attempt to return an existing URL for original_url or create one with short_code.

        Returns a tuple (obj, created).
        """
        return self.get_or_create(
            original_url=original_url, defaults={"short_code": short_code}
        )


class URL(models.Model):
    original_url = models.URLField(max_length=2048)
    short_code = models.CharField(max_length=10, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = URLManager()

    class Meta:
        db_table = "urls"

    def __str__(self):
        return f"{self.short_code} -> {self.original_url}"
