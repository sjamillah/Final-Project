class ShortenerError(Exception):
    """Base exception for shortener domain errors."""


class UniqueCodeError(ShortenerError):
    """Raised when a unique short code cannot be generated or persisted."""
