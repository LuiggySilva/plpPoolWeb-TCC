import os

from celery import Celery
from celery.schedules import crontab

from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

app = Celery("core")
app.conf.enable_utc = False

app.config_from_object(settings, namespace="CELERY")

app.conf.beat_scheduler = "django_celery_beat.schedulers:DatabaseScheduler"

app.conf.beat_schedule = {
    "verificar-deadlines-diariamente": {
        "task": "code_compiler.tasks.check_and_send_deadline_reminders",
        "schedule": crontab(hour=5, minute=0),
    },
}

app.autodiscover_tasks()
