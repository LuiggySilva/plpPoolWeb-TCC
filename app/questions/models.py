from simple_history.models import HistoricalRecords

from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from user.managers import HistoricalManager

from .validators import validate_period_format


class Period(models.Model):
    name = models.CharField(
        verbose_name="Nome do Período",
        max_length=6,
        unique=True,
        validators=[validate_period_format],
        help_text="Exemplos: 2023.0, 2023.1, 2024.2, etc.",
    )

    history = HistoricalRecords(history_manager=HistoricalManager)

    class Meta:
        verbose_name = "Período"
        verbose_name_plural = "Períodos"

    def __str__(self):
        return self.name


class Tag(models.Model):
    slug = models.SlugField(max_length=100, unique=True)
    name = models.CharField(
        max_length=100, unique=True, blank=False, null=False, verbose_name="Nome da Tag"
    )

    history = HistoricalRecords(history_manager=HistoricalManager)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class ProgrammingLanguages(models.TextChoices):
    C = "c", "C"
    CPP = "cpp", "C++"
    HASKELL = "haskell", "Haskell"
    PROLOG = "prolog", "Prolog"


class Question(models.Model):

    class Types(models.TextChoices):
        BASIC = "basic", "Básica"
        ADVANCED = "advanced", "Avançada"

    MAX_TESTS_COUNT = 12
    MAX_TAGS_COUNT = 5
    MIN_TAGS_COUNT = 1

    slug = models.SlugField(unique=False, blank=True, max_length=512)
    title = models.CharField("Enunciado", max_length=150, blank=False, null=False)
    code = models.TextField(
        "Código",
        blank=False,
        max_length=10000,
        help_text="É realizada uma normalização automática para remover espaços em branco extras e padronizar quebras de linha. Ex: '   int main() {\\r\\n' se torna 'int main() {\\n'",
    )
    description = models.TextField("Descrição", blank=False, max_length=10000)
    tags = models.ManyToManyField(
        "Tag",
        related_name="questions",
        blank=False,
        help_text=f"Escolha pelo menos {MIN_TAGS_COUNT} e no máximo {MAX_TAGS_COUNT} tag(s).",
    )
    author = models.ForeignKey(
        "user.AssistentStudent",
        verbose_name="Autor",
        on_delete=models.PROTECT,
        related_name="questions",
        blank=False,
    )
    period = models.ForeignKey(
        "Period",
        verbose_name="Período",
        on_delete=models.PROTECT,
        related_name="questions",
        blank=False,
    )

    language = models.CharField(
        "Linguagem",
        max_length=10,
        choices=ProgrammingLanguages.choices,
        blank=False,
        null=False,
    )

    type = models.CharField(
        "Tipo",
        max_length=10,
        choices=Types.choices,
        default=Types.BASIC,
        blank=False,
        null=False,
    )

    history = HistoricalRecords(history_manager=HistoricalManager, m2m_fields=[tags])

    created_at = models.DateTimeField(verbose_name="Criada em", auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name="Atualizada em", auto_now=True)

    @property
    def language_devicon(self):
        mapping = {
            "c": "c",
            "cpp": "cplusplus",
            "haskell": "haskell",
            "prolog": "prolog",
        }
        return mapping.get(self.language, "code")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title[:150])
        self.code = self.code.replace("\r\n", "\n").replace("\r", "\n").strip()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse(
            "questions:question_detail", kwargs={"question_id": self.pk, "slug": self.slug}
        )

    class Meta:
        verbose_name = "Questão"
        verbose_name_plural = "Questões"


class Test(models.Model):
    class TestType(models.TextChoices):
        PUBLIC = "public", "Público"
        PRIVATE = "private", "Privado"

    history = HistoricalRecords(history_manager=HistoricalManager)

    question = models.ForeignKey("Question", related_name="tests", on_delete=models.CASCADE)
    input_data = models.TextField(verbose_name="Entrada", blank=False, null=False)
    output_data = models.TextField(verbose_name="Saída", blank=False, null=False)
    type = models.CharField(
        verbose_name="Tipo",
        max_length=7,
        choices=TestType.choices,
        default=TestType.PRIVATE,
    )

    def save(self, *args, **kwargs):
        input_data = self.input_data
        output_data = self.output_data

        self.input_data = Test.normalize_text(input_data)
        self.output_data = Test.normalize_text(output_data)

        super().save(*args, **kwargs)

    @classmethod
    def normalize_text(cls, text):
        return text.replace("\r\n", "\n").replace("\r", "\n").strip()

    def __str__(self):
        return f"{self.pk}"

    class Meta:
        verbose_name = "Teste"
        verbose_name_plural = "Testes"
