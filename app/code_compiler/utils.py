from django.apps import apps


def get_executor():
    """Retorna a instância única do CodeExecutor configurada no apps.py"""
    return apps.get_app_config("code_compiler").code_executor
