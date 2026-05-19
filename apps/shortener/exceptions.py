class ShortenerError(Exception):
    """Base exception for all shortener domain errors."""


class UniqueCodeError(ShortenerError):
    """Raised when the service fails to generate a unique short code after max retries."""


class URLLimitExceeded(ShortenerError):
    """Raised when a free user tries to create more URLs than their tier allows."""


class PremiumFeatureRequired(ShortenerError):
    """Raised when a free/anonymous user attempts to use a premium-only feature."""


class AliasAlreadyTaken(ShortenerError):
    """Raised when a requested custom alias conflicts with an existing short code or alias."""
