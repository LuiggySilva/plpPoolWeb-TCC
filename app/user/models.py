from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from solo.models import SingletonModel


from .managers import CustomUserManager
from .validators import validate_registration_format


class CustomUser(AbstractBaseUser, PermissionsMixin):
    is_active = models.BooleanField(
        verbose_name="Permissão de Login", 
        default=True,
        help_text=format_html(
            "Emails só serão enviados para usuários com permissão de login. <br>" 
            "Desmarque para desativar o usuário, mas não excluí-lo.<br>" 
            "Usuários inativos não podem fazer login."
        )
    )
    is_staff = models.BooleanField(_("staff status"), default=False)
    ROLE_CHOICES = (
        ('monitor', 'Monitor'),
        ('professor', 'Professor'),
    )

    email = models.EmailField(unique=True)
    registration = models.CharField(
        verbose_name="Matrícula", 
        max_length=9, unique=True, 
        validators=[validate_registration_format],
        help_text="Exemplo: 123456789"
    )
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
            self.role = 'monitor'
        super().save(*args, **kwargs)


class Professor(CustomUser):
    class Meta:
        proxy = True
        verbose_name = "Professor"
        verbose_name_plural = "Professores"

    def save(self, *args, **kwargs):
        if not self.pk:
            self.role = 'professor'
            self.is_staff = True 
        super().save(*args, **kwargs)

# TODO adicionar as configuraçoes de quantidade de questoes basicas e avançadas por linguagem (c/c++, haskll e prolog).
# Caso a quantidade de questões basicas e avancadas de uma linguagem seja 0, não deve aparecer para o monitor.
# Deve ter o deadline de criacão de questões para cada linguagem.
# Nessa tela deve ter o botão de baixar o backup dos dados do sistema
class SystemSetting(SingletonModel):
    active_period = models.ForeignKey(
        'questions.Period',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Período ativo"
    )

    max_basic_cpp_questions = models.PositiveIntegerField(
        verbose_name="Máximo de questões básicas em C/C++",
        default=0,
        help_text="Número máximo de questões básicas que podem ser criadas em C/C++."
    )
    max_advanced_cpp_questions = models.PositiveIntegerField(
        verbose_name="Máximo de questões avançadas em C/C++",
        default=0,
        help_text="Número máximo de questões avançadas que podem ser criadas em C/C++."
    )

    max_basic_haskell_questions = models.PositiveIntegerField(
        verbose_name="Máximo de questões básicas em Haskell",
        default=0,
        help_text="Número máximo de questões básicas que podem ser criadas em Haskell."
    )
    max_advanced_haskell_questions = models.PositiveIntegerField(
        verbose_name="Máximo de questões avançadas em Haskell",
        default=0,
        help_text="Número máximo de questões avançadas que podem ser criadas em Haskell."
    )
    max_basic_prolog_questions = models.PositiveIntegerField(
        verbose_name="Máximo de questões básicas em Prolog",
        default=0,
        help_text="Número máximo de questões básicas que podem ser criadas em Prolog."
    )
    max_advanced_prolog_questions = models.PositiveIntegerField(
        verbose_name="Máximo de questões avançadas em Prolog",
        default=0,
        help_text="Número máximo de questões avançadas que podem ser criadas em Prolog."
    )

    cpp_deadline = models.DateTimeField(
        verbose_name="Prazo para criação de questões em C/C++",
        help_text="Data e hora limite para a criação de questões em C/C++.",
        blank=True,
        default=timezone.now
    )
    haskell_deadline = models.DateTimeField(
        verbose_name="Prazo para criação de questões em Haskell",
        help_text="Data e hora limite para a criação de questões em Haskell.",
        blank=True,
        default=timezone.now
    )
    prolog_deadline = models.DateTimeField(
        verbose_name="Prazo para criação de questões em Prolog",
        help_text="Data e hora limite para a criação de questões em Prolog.",
        blank=True,
        default=timezone.now
    )

    class Meta:
        verbose_name = "Configurações do sistema"

    def __str__(self):
        return "Configurações"