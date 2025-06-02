from .base import *
from .base import INSTALLED_APPS, MIDDLEWARE


DEBUG = True


# https://django-debug-toolbar.readthedocs.io/en/latest/
INSTALLED_APPS += ["debug_toolbar", ]


ALLOWED_HOSTS = ["localhost", "0.0.0.0", "127.0.0.1"]


CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'cache+memory://'


INTERNAL_IPS = [ 
    "127.0.0.1",
]


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}



# https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-dev-cache',
    },
}



MIDDLEWARE += [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "rich.logging.RichHandler",
            "rich_tracebacks": True,
            "tracebacks_show_locals": True,
            "markup": True,
        },
    },
    "loggers": {
        "root": {
            "handlers": ["console"],
            "level": "DEBUG",
        },
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}