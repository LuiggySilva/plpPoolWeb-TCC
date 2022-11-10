from django.db import models
from django.contrib.auth.models import (
    AbstractUser, 
    AbstractBaseUser, 
    BaseUserManager
)
from django.core.validators import MinValueValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db.models import signals
from django.template.defaultfilters import slugify
from django.contrib.auth.models import AbstractUser, BaseUserManager

class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """
    def create_user(self, email, password, **extra_fields):
        """
        Create and save a User with the given email and password.
        """
        if not email:
            raise ValueError(_('The Email must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = models.CharField("Nome", max_length=150, blank=False, null=False)
    email = models.EmailField(_('email address'), unique=True, blank=False, null=False)
    slug = models.SlugField(max_length=150)

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.email}"

def user_pre_save(signal, instance, sender, **kwargs):
    instance.slug = slugify(instance.username)
signals.pre_save.connect(user_pre_save, sender=User)



MATRICULA_REGEX = RegexValidator(r'^\d{9}$', 'Formato de matrícula inválido')
class Monitor(User):
    matricula = models.CharField(
        "Matrícula", 
        max_length=9, 
        validators=[MATRICULA_REGEX], 
        unique=True, 
        blank=False, 
        null=False
    )

    def __str__(self):
        return f"{self.email}"

    class Meta:
        verbose_name = "Monitor"
        verbose_name_plural = "Monitores"

def monitor_pre_save(signal, instance, sender, **kwargs):
    instance.set_password(instance.matricula)
signals.pre_save.connect(monitor_pre_save, sender=Monitor)



class Professor(User):
    def __str__(self):
        return f"{self.email}"

    class Meta:
        verbose_name = "Professor"
        verbose_name_plural = "Professores"



class Tag(models.Model):
    nome = models.CharField(max_length=100, unique=True, blank=False, null=False)

    def __str__(self):
        return f"{self.nome}"



EXTENSAO_REGEX = RegexValidator(r'^.{1}[a-z]*$', 'Formato de extensão inválido')
class Linguagem(models.Model):
    nome = models.CharField(max_length=50, blank=False, null=False)
    extensao = models.CharField(
        "Extensão", 
        max_length=50, 
        blank=False, 
        null=False, 
        validators=[EXTENSAO_REGEX]
    )
    compilador = models.BooleanField(default=False, blank=False, null=False)
    executar = models.CharField(max_length=100, blank=False, null=False)

    def __str__(self):
        return f"{self.nome}"

    class Meta:
        verbose_name = "Linguagem"
        verbose_name_plural = "Linguagens"


class Questao(models.Model):
    enunciado = models.CharField(max_length=150, blank=False, null=False)
    codigo = models.TextField("Código", blank=False)
    descricao = models.TextField("Descrição", blank=False)
    tags = models.ManyToManyField(Tag, related_name="tags", blank=False)
    autor = models.ForeignKey(Monitor, on_delete=models.DO_NOTHING)
    linguagem = models.ForeignKey(Linguagem, on_delete=models.DO_NOTHING) 
    periodo = models.ForeignKey("Periodo", on_delete=models.DO_NOTHING, blank=True)
    
    class Tipo(models.TextChoices):
        BASICA = 'Básica', _('Básica')
        AVANCADA = 'Avançada', _('Avançada')

    tipo = models.CharField(
        max_length=10, 
        choices=Tipo.choices, 
        default=Tipo.BASICA
    )

    def __str__(self):
        return f"{self.enunciado}"

    class Meta:
        verbose_name = "Questão"
        verbose_name_plural = "Questões"
        
def questao_post_save(signal, instance, sender, **kwargs):
    instance.codigo = instance.codigo.strip()
    instance.descricao = instance.descricao.strip()
signals.post_save.connect(questao_post_save, sender=Questao)



class Atividade(models.Model):
    linguagem = models.ForeignKey(
        Linguagem, 
        on_delete=models.DO_NOTHING, 
        blank=True, null=True
    )
    qtd_basicas = models.IntegerField(
        "Questões básicas", 
        default=0, 
        validators=[MinValueValidator(0)]
    )
    qtd_avancadas = models.IntegerField(
        "Questões avançadas", 
        default=0, 
        validators=[MinValueValidator(0)]
    )
    data = models.DateField()
    descricao = models.TextField(
        "Descrição",
        max_length=200, 
        blank=False, 
        null=False)
    periodo = models.ForeignKey(
        "Periodo", 
        on_delete=models.CASCADE, 
        blank=False, 
        null=False
    )

    def __str__(self):
        return f"{self.data} • {self.periodo}"


    class Meta:
        verbose_name = "Atividade"
        verbose_name_plural = "Atividades"



class Teste(models.Model):
    class Tipo(models.TextChoices):
        PUBLICO = 'Público', _('Público')
        PRIVADO = 'Privado', _('Privado')

    questao = models.ForeignKey(
        Questao, 
        related_name="testes", 
        on_delete=models.CASCADE
    )
    entrada = models.TextField()
    saida = models.TextField("Saída")
    tipo = models.CharField(
        max_length=7, 
        choices=Tipo.choices, 
        default=Tipo.PRIVADO
    )

    def __str__(self):
        return f"{self.pk}"

    class Meta:
        verbose_name = "Teste"
        verbose_name_plural = "Testes"



PERIODO_REGEX = RegexValidator(r'^[0-9]{4}.[0-9][a-zA-z]?$', 'Formato de período inválido')
class Periodo(models.Model):
    nome = models.CharField(
        "Período", 
        max_length=10, 
        unique=True, 
        blank=False, 
        null=False,
        validators=[PERIODO_REGEX] 
    )
    monitores = models.ManyToManyField(Monitor, blank=False)
    ativo = models.BooleanField(
        default=True, 
        blank=False, 
        null=False,
        help_text="Indica que o período está ativo. Apenas um período pode estar ativo.",
    )

    def __str__(self):
        return f"{self.nome}"

    class Meta:
        verbose_name = "Período"
        verbose_name_plural = "Períodos"
