from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """
    Limits login attempts to 5 per minute per IP address.
    Applies to unauthenticated requests only since login requires no token.
    """

    scope = "login"


class URLCreateRateThrottle(UserRateThrottle):
    """
    Limits URL creation to 30 per minute per authenticated user.
    Prevents abuse of the shortening endpoint.
    """

    scope = "url_create"
