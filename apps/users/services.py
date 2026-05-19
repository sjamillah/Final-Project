from .models import User


def create_user(*, username: str, email: str, password: str) -> User:
    return User.objects.create_user(
        username=username,
        email=email,
        password=password,
    )


def update_user_tier(user: User, tier: str) -> User:
    user.tier = tier
    # Keep DB `is_premium` in sync with `tier` for backward compatibility.
    # Only PREMIUM counts as premium for billing/features; admins are not premium customers.
    user.is_premium = tier == User.Tier.PREMIUM
    user.is_staff = tier == User.Tier.ADMIN
    user.save(update_fields=["tier", "is_premium", "is_staff"])
    return user
