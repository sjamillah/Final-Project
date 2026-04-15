from . import base

# Import all uppercase Django settings from base without wildcard imports.
globals().update({name: value for name, value in vars(base).items() if name.isupper()})

DEBUG = True
