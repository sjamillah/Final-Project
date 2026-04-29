class ShortenerError(Exception):
    """Base exception for shortener domain errors."""


class UniqueCodeError(ShortenerError):
    """Raised when the service fails to generate a unique short code."""
