from datetime import timedelta

from django.db import models
from django.utils import timezone


class ManualRunManager(models.Manager):
    def get_queryset(self):
        from .models import ExecutionType

        return super().get_queryset().filter(activity_type=ExecutionType.MANUAL)

    def days_ago(self, days):
        # days = 1 if days == 30 else days # DEBUG
        limit = timezone.now() - timedelta(days=days)
        return self.filter(created_at__gte=limit)


class QuestionValidationManager(models.Manager):
    def get_queryset(self):
        from .models import ExecutionType

        return super().get_queryset().filter(activity_type=ExecutionType.VALIDATION)

    def days_ago(self, days):
        # days = 0 if days == 30 else days # DEBUG
        limit = timezone.now() - timedelta(days=days)
        return self.filter(created_at__gte=limit)
