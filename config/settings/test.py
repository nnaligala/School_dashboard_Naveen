import os

_defaults = {
    "DJANGO_SECRET_KEY": "test-only-secret-key-not-for-production-use-0123456789",
    "DB_NAME": "x", "DB_USER": "x", "DB_PASSWORD": "x", "DB_HOST": "x",
    "RABBITMQ_USER": "x", "RABBITMQ_PASSWORD": "x", "RABBITMQ_HOST": "x", "RABBITMQ_VHOST": "x",
    "MEMCACHED_HOSTS": "x:11211",
}
for _k, _v in _defaults.items():
    os.environ.setdefault(_k, _v)

from .base import *  # noqa: E402,F401,F403

DEBUG = False
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
SESSION_ENGINE = "django.contrib.sessions.backends.db"
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
ALLOWED_HOSTS = ["testserver"]
