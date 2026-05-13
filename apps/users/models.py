from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Tier(models.TextChoices):
        FREE = "free", "Free"
        PREMIUM = "premium", "Premium"
        ADMIN = "admin", "Admin"

    email = models.EmailField(unique=True)
    is_premium = models.BooleanField(default=False)
    tier = models.CharField(
        max_length=10,
        choices=Tier.choices,
        default=Tier.FREE,
    )

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        """Auto-sync tier and staff access from the current user state."""
        if self.is_staff or self.is_superuser or self.tier == self.Tier.ADMIN:
            self.tier = self.Tier.ADMIN
            self.is_staff = True
        elif self.is_premium:
            self.tier = self.Tier.PREMIUM
            self.is_staff = False
        else:
            self.tier = self.Tier.FREE
            self.is_staff = False
        super().save(*args, **kwargs)
