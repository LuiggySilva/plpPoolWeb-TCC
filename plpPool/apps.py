from django.apps import AppConfig
import os

class PlppoolConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'plpPool'

    def ready(self):
        from plpPool import tasks
        if os.environ.get('RUN_MAIN'):
            tasks.start()
