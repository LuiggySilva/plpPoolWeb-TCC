from django.apps import AppConfig
from django.conf import settings


class CodeCompilerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "code_compiler"
    verbose_name = "Execuções de Código"

    def ready(self):
        from .services import CodeExecutor

        self.code_executor = CodeExecutor(debug=settings.DEBUG)
