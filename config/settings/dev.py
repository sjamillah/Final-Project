import os
import sys

from . import base

globals().update({name: value for name, value in vars(base).items() if name.isupper()})

DEBUG = True

DATABASES = base.DATABASES
DATABASES["default"]["TEST"] = {
    "NAME": "urlshortener_test",
}

# When running under pytest prefer a fast in-memory SQLite database so tests
# don't depend on a local Postgres instance. This keeps developer workflow
# simple while preserving Postgres for normal development runs.
if "pytest" in " ".join(sys.argv) or os.environ.get("PYTEST_CURRENT_TEST"):
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
