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
# Deve ter as informações sobre as linguagens (nome, extensão e comando de execução), tudo readonly.
# Nessa tela deve ter o botão de baixar o backup dos dados do sistema
class SystemSetting(SingletonModel):
    active_period = models.ForeignKey(
        'questions.Period',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Período ativo",
        help_text = format_html(
            "• Se definido, apenas monitores com este período terão acesso.<br>"
            "• Se deixado em branco, nenhum monitor poderá acessar.<br>"
            "<b>Atenção:</b> o acesso dos professores deve ser removido manualmente."
        )
    )

    class Meta:
        verbose_name = "Configurações do sistema"

    def __str__(self):
        return "Configurações"