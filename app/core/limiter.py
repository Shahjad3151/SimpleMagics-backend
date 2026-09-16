"""
Single shared slowapi Limiter instance.

Both main.py (to register it on the FastAPI app) and individual route
modules (to decorate specific endpoints, e.g. auth login/register) need
access to the same Limiter — pulling it from main.py directly would create
a circular import, so it lives here instead.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
