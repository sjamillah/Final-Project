from .models import User


def get_user_by_email(email: str) -> User | None:
    return User.objects.filter(email=email).first()


def get_user_by_username(username: str) -> User | None:
    return User.objects.filter(username=username).first()
