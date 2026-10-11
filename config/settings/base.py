from pathlib import Path

import environ
from kombu import Exchange, Queue

BASE_DIR = Path(__file__).resolve().parent.parent.parent
env = environ.Env()

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])
SCHOOL_NAME = env("SCHOOL_NAME", default="Naveen's School")
SITE_DOMAIN = env("SITE_DOMAIN", default="localhost")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "rest_framework",
    "django_prometheus",
    "apps.core",
    "apps.accounts",
    "apps.communication",
    "apps.academics",
    "apps.students",
    "apps.attendance",
    "apps.website",
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "csp.middleware.CSPMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.accounts.middleware.ForcePasswordChangeMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context.school",
            ],
        },
    }
]

# ---------------------------------------------------------------- Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST"),
        "PORT": env("DB_PORT", default="5432"),
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
        "ATOMIC_REQUESTS": False,  # transactions are explicit in services
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ------------------------------------------------------------ Auth / users
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["apps.accounts.backends.LockoutAwareBackend"]
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:dashboard"
LOGOUT_REDIRECT_URL = "website:home"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": env.int("PASSWORD_MIN_LENGTH", default=10)},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
LOGIN_MAX_FAILURES = env.int("LOGIN_MAX_FAILURES", default=5)
LOGIN_LOCK_MINUTES = env.int("LOGIN_LOCK_MINUTES", default=15)
AUDIT_RETENTION_DAYS = env.int("AUDIT_RETENTION_DAYS", default=730)

# ------------------------------------------------------------------- Cache
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.memcached.PyMemcacheCache",
        "LOCATION": env.list("MEMCACHED_HOSTS"),
        "KEY_PREFIX": env("CACHE_KEY_PREFIX", default="naveens"),
        "TIMEOUT": 300,
        "OPTIONS": {"no_delay": True, "ignore_exc": True, "max_pool_size": 4, "use_pooling": True},
    }
}
# cached_db: reads hit Memcached, writes persist to PostgreSQL, so sessions
# survive a Memcached restart or eviction.
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SESSION_COOKIE_AGE = env.int("SESSION_AGE_SECONDS", default=3600)
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# ------------------------------------------------------- RabbitMQ / Celery
CELERY_BROKER_URL = "amqp://{u}:{p}@{h}:{port}/{v}".format(
    u=env("RABBITMQ_USER"),
    p=env("RABBITMQ_PASSWORD"),
    h=env("RABBITMQ_HOST"),
    port=env("RABBITMQ_PORT", default="5672"),
    v=env("RABBITMQ_VHOST"),
)
CELERY_RESULT_BACKEND = None  # results are not stored; tasks are idempotent
CELERY_TASK_IGNORE_RESULT = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_SOFT_TIME_LIMIT = 240
CELERY_TASK_TIME_LIMIT = 300
CELERY_TIMEZONE = "Asia/Kolkata"
CELERY_ENABLE_UTC = True

_dlx = Exchange("dead_letter", type="direct")
_exchange = Exchange("naveens", type="direct")


def _queue(name):
    return Queue(
        name,
        _exchange,
        routing_key=name,
        queue_arguments={
            "x-dead-letter-exchange": "dead_letter",
            "x-dead-letter-routing-key": f"{name}.dead",
        },
    )


CELERY_TASK_QUEUES = (
    _queue("default"),
    _queue("email"),
    _queue("sms"),
    _queue("reports"),
    _queue("imports"),
    Queue("dead_letter", _dlx, routing_key="#"),
)
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_DEFAULT_EXCHANGE = "naveens"
CELERY_TASK_DEFAULT_ROUTING_KEY = "default"
CELERY_TASK_ROUTES = {
    "apps.communication.tasks.send_email*": {"queue": "email"},
    "apps.communication.tasks.send_sms*": {"queue": "sms"},
    "apps.reports.tasks.*": {"queue": "reports"},
    "apps.students.tasks.import_*": {"queue": "imports"},
}
CELERY_BEAT_SCHEDULE = {
    "purge-old-audit-logs": {
        "task": "apps.core.tasks.purge_old_audit_logs",
        "schedule": 60 * 60 * 24,
    },
}

# --------------------------------------------------------------------- I18N
LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# -------------------------------------------------------------------- Files
STATIC_URL = "/static/"
STATIC_ROOT = env("STATIC_ROOT", default=str(BASE_DIR / "staticfiles"))
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = env("MEDIA_ROOT", default=str(BASE_DIR / "media"))
MAX_UPLOAD_BYTES = env.int("MAX_UPLOAD_MB", default=5) * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_BYTES
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024

# -------------------------------------------------------------------- Email
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=25)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@localhost")

# --------------------------------------------------------------------- DRF
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"anon": "30/min", "user": "300/min"},
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
}

# ------------------------------------------------------ Security headers/CSP
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "https://cdn.jsdelivr.net")
CSP_STYLE_SRC = ("'self'", "https://cdn.jsdelivr.net")
CSP_FONT_SRC = ("'self'", "https://cdn.jsdelivr.net")
CSP_IMG_SRC = ("'self'", "data:")
CSP_FRAME_SRC = ("https://www.google.com", "https://www.youtube-nocookie.com")
CSP_FRAME_ANCESTORS = ("'none'",)
CSP_FORM_ACTION = ("'self'",)

# ------------------------------------------------------------------ Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "format": "ts=%(asctime)s level=%(levelname)s logger=%(name)s pid=%(process)d msg=%(message)s"
        }
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "structured"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
    "loggers": {
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "celery": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "audit": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
