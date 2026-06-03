from simple_history.models import HistoricalRecords
from solo.models import SingletonModel

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .managers import (
    AssistentStudentManager,
    CustomUserManager,
    HistoricalManager,
    ProfessorManager,
)
from .utils import (
    get_or_create_assistentstudent_group,
    get_or_create_professors_group,
    get_valid_random_registration,
)
from .validators import validate_registration_format


class CustomUser(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        ASSISTENT_STUDENT = "monitor", "Monitor"
        PROFESSOR = "professor", "Professor"

    history = HistoricalRecords(history_manager=HistoricalManager)

    is_active = models.BooleanField(
        verbose_name="Permissão de Login",
        default=True,
        help_text=format_html(
            "Emails só serão enviados para usuários com permissão de login. <br>"
            "Desmarque para desativar o usuário, mas não excluí-lo.<br>"
            "Usuários inativos não podem fazer login."
        ),
    )
    is_staff = models.BooleanField(_("staff status"), default=False)
    email = models.EmailField(unique=True)
    registration = models.CharField(
        verbose_name="Matrícula",
        max_length=9,
        unique=True,
        validators=[validate_registration_format],
        help_text="Exemplo: 123456789",
        blank=True,
        null=True,
    )
    name = models.CharField(verbose_name="Nome", max_length=255, blank=False)
    github = models.URLField(
        verbose_name="GitHub",
        max_length=255,
        blank=True,
        null=True,
        help_text="URL do perfil do GitHub (opcional)",
    )
    period = models.ForeignKey(
        "questions.Period",
        verbose_name="Período",
        related_name="users",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    role = models.CharField(verbose_name="Função", max_length=10, choices=Role.choices, blank=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")


class AssistentStudent(CustomUser):
    objects = AssistentStudentManager()

    history = HistoricalRecords(history_manager=HistoricalManager)

    class Meta:
        proxy = True
        verbose_name = "Monitor"
        verbose_name_plural = "Monitores"

    @classmethod
    def get_or_create_legacy(cls, name, github_url):
        monitor = cls.objects.filter(github=github_url).first()

        if not monitor:
            short_id = get_valid_random_registration()

            monitor = cls.objects.create(
                name=name,
                github=github_url,
                email=f"legacy.{short_id}@archive.local",
                registration=short_id,
                is_active=False,
                role=cls.Role.ASSISTENT_STUDENT,
            )
        return monitor

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        self.role = self.Role.ASSISTENT_STUDENT
        super().save(*args, **kwargs)

        if is_new:
            group = get_or_create_assistentstudent_group()
            self.groups.add(group)


class Professor(CustomUser):
    objects = ProfessorManager()

    history = HistoricalRecords(history_manager=HistoricalManager)

    class Meta:
        proxy = True
        verbose_name = "Professor"
        verbose_name_plural = "Professores"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        self.role = self.Role.PROFESSOR
        self.is_staff = True
        super().save(*args, **kwargs)

        if is_new:
            group = get_or_create_professors_group()
            self.groups.add(group)


class SystemSetting(SingletonModel):
    history = HistoricalRecords(history_manager=HistoricalManager)

    active_period = models.ForeignKey(
        "questions.Period",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Período Ativo",
    )

    min_basic_cpp_questions = models.PositiveIntegerField(
        verbose_name="Mínimo de questões básicas em C/C++",
        default=0,
    )
    min_advanced_cpp_questions = models.PositiveIntegerField(
        verbose_name="Mínimo de questões avançadas em C/C++",
        default=0,
    )

    min_basic_haskell_questions = models.PositiveIntegerField(
        verbose_name="Mínimo de questões básicas em Haskell",
        default=0,
    )
    min_advanced_haskell_questions = models.PositiveIntegerField(
        verbose_name="Mínimo de questões avançadas em Haskell",
        default=0,
    )

    min_basic_prolog_questions = models.PositiveIntegerField(
        verbose_name="Mínimo de questões básicas em Prolog",
        default=0,
    )
    min_advanced_prolog_questions = models.PositiveIntegerField(
        verbose_name="Mínimo de questões avançadas em Prolog",
        default=0,
    )

    cpp_deadline = models.DateTimeField(
        verbose_name="Prazo para criação de questões em C/C++",
        help_text="Data e hora limite para a criação de questões em C/C++.",
        blank=True,
        default=timezone.now,
    )
    haskell_deadline = models.DateTimeField(
        verbose_name="Prazo para criação de questões em Haskell",
        help_text="Data e hora limite para a criação de questões em Haskell.",
        blank=True,
        default=timezone.now,
    )
    prolog_deadline = models.DateTimeField(
        verbose_name="Prazo para criação de questões em Prolog",
        help_text="Data e hora limite para a criação de questões em Prolog.",
        blank=True,
        default=timezone.now,
    )

    min_public_tests_in_questions = models.PositiveIntegerField(
        verbose_name="Mínimo de testes públicos em questões",
        default=1,
    )
    min_private_tests_in_questions = models.PositiveIntegerField(
        verbose_name="Mínimo de testes privados em questões",
        default=5,
    )

    class Meta:
        verbose_name = "Configurações do Sistema"

    def __str__(self):
        return "Configurações"
