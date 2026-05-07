from .models import User


def create_user(*, username: str, email: str, password: str) -> User:
    return User.objects.create_user(
        username=username,
        email=email,
        password=password,
    )


def update_user_tier(user: User, tier: str) -> User:
    user.tier = tier
    user.is_premium = tier in (User.Tier.PREMIUM, User.Tier.ADMIN)
    user.save(update_fields=["tier", "is_premium"])
    return user
