import environ

from .base import *  # noqa: F401,F403

env = environ.Env()
DEBUG = False

# Fail fast if any service host is missing or points at the local machine.
for _name in ("DB_HOST", "RABBITMQ_HOST"):
    if env(_name) in ("localhost", "127.0.0.1", "::1"):
        raise RuntimeError(f"{_name} must not be localhost in production")
if any(h.split(":")[0] in ("localhost", "127.0.0.1") for h in env.list("MEMCACHED_HOSTS")):
    raise RuntimeError("MEMCACHED_HOSTS must not be localhost in production")
if not ALLOWED_HOSTS:  # noqa: F405
    raise RuntimeError("DJANGO_ALLOWED_HOSTS is required in production")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = False  # Nginx performs the redirect
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False
