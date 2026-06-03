from .base import *
from .base import TIME_ZONE  # , INSTALLED_APPS

from decouple import config

DEBUG = False


# INSTALLED_APPS += ["django_cleanup.apps.CleanupConfig",]


ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=str).split(" ")


# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_HOST_USER = config("EMAIL_HOST_USER", cast=str)
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", cast=str)
EMAIL_USE_TLS = True


CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", cast=str).split(" ")
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True


CELERY_BROKER_URL = "redis://redis:6379/0"
CELERY_RESULT_BACKEND = "django-db"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("POSTGRES_NAME", cast=str),
        "USER": config("POSTGRES_USER", cast=str),
        "PASSWORD": config("POSTGRES_PASSWORD", cast=str),
        "HOST": config("POSTGRES_HOST", cast=str),
        "PORT": config("POSTGRES_PORT", cast=str),
        "TIME_ZONE": TIME_ZONE,
    }
}


CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://redis:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
        },
    },
}


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"require_debug_false": {"()": "django.utils.log.RequireDebugFalse"}},
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s",
        },
    },
    "handlers": {
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {"level": "INFO", "handlers": ["console"]},
    "loggers": {
        "django.request": {
            "handlers": ["mail_admins"],
            "level": "ERROR",
            "propagate": True,
        },
        "django.security.DisallowedHost": {
            "level": "ERROR",
            "handlers": ["console", "mail_admins"],
            "propagate": True,
        },
        "code_compiler": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": True,
        },
        "docker": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "urllib3": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
