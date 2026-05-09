import json
import logging
import traceback


class JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON — no external dependencies."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            payload["exc_info"] = traceback.format_exception(*record.exc_info)

        # Carry through any extra= fields attached by the caller.
        for key, value in record.__dict__.items():
            if key not in logging.LogRecord.__dict__ and key not in payload:
                payload[key] = value

        return json.dumps(payload, default=str)
