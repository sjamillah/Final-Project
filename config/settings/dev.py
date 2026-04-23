from . import base

globals().update({name: value for name, value in vars(base).items() if name.isupper()})

DEBUG = True

DATABASES = base.DATABASES
DATABASES["default"]["TEST"] = {
    "NAME": "urlshortener_test",
}
