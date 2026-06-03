import random
from datetime import timedelta

from simple_history.manager import HistoryManager

from django.contrib.auth.models import BaseUserManager
from django.db import models
from django.utils import timezone

from .utils import get_or_create_professors_group


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("O email é obrigatório")
        if not extra_fields.get("name"):
            raise ValueError("O nome é obrigatório")
        if not extra_fields.get("period") and not extra_fields.get("is_superuser"):
            raise ValueError("O período é obrigatório")

        group = extra_fields.pop("group", None)

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        if group:
            user.groups.add(group)

        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("name", "Professor Admin")
        extra_fields.setdefault("role", self.model.Role.PROFESSOR)
        extra_fields.setdefault("registration", str(random.randint(100000000, 999999999)))

        group = get_or_create_professors_group()
        extra_fields["group"] = group

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superusuário precisa de is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superusuário precisa de is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class AssistentStudentManager(models.Manager):
    def get_queryset(self):
        from .models import CustomUser

        return super().get_queryset().filter(role=CustomUser.Role.ASSISTENT_STUDENT)


class ProfessorManager(models.Manager):
    def get_queryset(self):
        from .models import CustomUser

        return super().get_queryset().filter(role=CustomUser.Role.PROFESSOR)


class HistoricalManager(HistoryManager):
    def days_ago(self, days):
        # days = 1 if days == 30 else days # DEBUG
        limit = timezone.now() - timedelta(days=days)
        return self.filter(history_date__gte=limit)
