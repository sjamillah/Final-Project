from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """Limits login attempts to 5 per minute per IP."""

    scope = "login"


class URLCreateRateThrottle(UserRateThrottle):
    """Limits URL creation to 10 per minute per authenticated user."""

    scope = "url_create"
