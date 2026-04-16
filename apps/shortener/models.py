from django.db import models


class URL(models.Model):
    original_url = models.URLField(max_length=2048)
    short_code = models.CharField(max_length=10, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "urls"

    def __str__(self):
        return f"{self.short_code} -> {self.original_url}"
