from django.db import models
from django.utils.text import slugify
from django.urls import reverse
from django.forms import ValidationError


from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
from django.utils.safestring import mark_safe


from .validators import validate_period_format


class Period(models.Model):
    name = models.CharField(
        verbose_name="Nome do Período", 
        max_length=6, 
        unique=True,
        validators=[validate_period_format],
        help_text="Exemplos: 2023.0, 2023.1, 2024.2, etc."    
    )

    class Meta:
        verbose_name = "Período"
        verbose_name_plural = "Períodos"

    def __str__(self):
        return self.name
    

class Tag(models.Model):
    slug = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
    

class Question(models.Model):
    class Languages(models.TextChoices):
        C_CPP = 'cplusplus', 'C/C++'
        HASKELL = 'haskell', 'Haskell'
        PROLOG = 'prolog', 'Prolog'

    class Types(models.TextChoices):
        BASIC = 'basic', 'Básica'
        ADVANCED = 'advanced', 'Avançada'

    MAX_TAGS_COUNT = 6

    slug = models.SlugField(unique=False, blank=True, max_length=512)
    title = models.CharField("Enunciado", max_length=150, blank=False, null=False)
    code = models.TextField("Código", blank=False)
    description = models.TextField("Descrição", blank=False)
    tags = models.ManyToManyField('Tag', related_name="questions", blank=False)
    author = models.ForeignKey('user.AssistentStudent', verbose_name='Autor', on_delete=models.DO_NOTHING, related_name="questions", blank=False)
    period = models.ForeignKey('Period', verbose_name='Período', on_delete=models.DO_NOTHING, related_name="questions", blank=False)

    language = models.CharField(
        "Linguagem",
        max_length=10,
        choices=Languages.choices,
        default=Languages.C_CPP,
        blank=False,
        null=False
    )

    type = models.CharField(
        "Tipo",
        max_length=10,
        choices=Types.choices,
        default=Types.BASIC,
        blank=False,
        null=False
    )

    created_at = models.DateTimeField(verbose_name="Criada em", auto_now=True)
    updated_at = models.DateTimeField(verbose_name="Atualizada em", auto_now_add=True)

    def get_code_highlighted(self):
        lexer = self._get_lexer()
        formatter = HtmlFormatter(style='monokai', full=True, linenos=True)
        highlighted_code = highlight(self.code, lexer, formatter)
        return mark_safe(highlighted_code)
    
    def _get_lexer(self):
        try:
            if self.language == self.Languages.C_CPP:
                return get_lexer_by_name('cpp', stripall=True)
            else:
                return get_lexer_by_name(self.language, stripall=True)
        except Exception as e:
            raise ValueError(f"Erro ao obter lexer para a linguagem '{self.language}': {e}")

    def __str__(self):
        return self.title
    
    def clean_tags(self):
        tags = self.cleaned_data['tags']
        if len(tags) > self.MAX_TAGS_COUNT:
            raise ValidationError(f"Selecione no máximo {self.MAX_TAGS_COUNT} tags.")
        return tags
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title[:150])
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("questions:detail", kwargs={"pk": self.pk, "slug": self.slug})

    class Meta:
        verbose_name = "Questão"
        verbose_name_plural = "Questões"



class Test(models.Model):
    class TestType(models.TextChoices):
        PUBLIC = 'public', 'Público'
        PRIVATE = 'private', 'Privado'

    question = models.ForeignKey(
        'Question',
        related_name="tests",
        on_delete=models.CASCADE
    )
    input_data = models.TextField(verbose_name="Entrada", blank=False, null=False)
    output_data = models.TextField(verbose_name="Saída", blank=False, null=False)
    type = models.CharField(
        verbose_name="Tipo",
        max_length=7,
        choices=TestType.choices,
        default=TestType.PRIVATE
    )

    def __str__(self):
        return f"{self.pk}"

    class Meta:
        verbose_name = "Teste"
        verbose_name_plural = "Testes"
