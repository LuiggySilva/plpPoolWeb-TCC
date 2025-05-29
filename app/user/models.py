from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .managers import CustomUserManager
from .validators import validate_registration_format


class CustomUser(AbstractBaseUser, PermissionsMixin):
    is_active = models.BooleanField(_("active"), default=True)
    is_staff = models.BooleanField(_("staff status"), default=False)
    ROLE_CHOICES = (
        ('monitor', 'Monitor'),
        ('professor', 'Professor'),
    )

    email = models.EmailField(unique=True)
    registration = models.CharField(verbose_name="Matrícula", max_length=9, unique=True, validators=[validate_registration_format])
    name = models.CharField(verbose_name="Nome", max_length=255)
    github = models.URLField(verbose_name="GitHub", max_length=255, blank=True)
    period = models.ForeignKey('questions.Period', verbose_name="Período", related_name='periodo', on_delete=models.CASCADE, blank=True, null=True)
    role = models.CharField(verbose_name="Função", max_length=10, choices=ROLE_CHOICES, blank=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email
    
    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")



class AssistentStudent(CustomUser):
    class Meta:
        proxy = True
        verbose_name = "Monitor"
        verbose_name_plural = "Monitores"

    def clean(self):
        super().clean()
        if not self.period:
            raise ValidationError({'period': 'O período é obrigatório para Monitores.'})


    def save(self, *args, **kwargs):
        if not self.pk:
            self.role = 'aluno'
        super().save(*args, **kwargs)


class Professor(CustomUser):
    class Meta:
        proxy = True
        verbose_name = "Professor"
        verbose_name_plural = "Professores"

    def clean(self):
        super().clean()
        if not self.period:
            raise ValidationError({'period': 'O período é obrigatório para Professores.'})

    def save(self, *args, **kwargs):
        if not self.pk:
            self.role = 'professor'
            self.is_staff = True 
        super().save(*args, **kwargs)