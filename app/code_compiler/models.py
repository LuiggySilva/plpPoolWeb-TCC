import uuid

from django.db import models

from questions.models import ProgrammingLanguages, Question, Test
from user.models import CustomUser

from .managers import ManualRunManager, QuestionValidationManager


class TaskStatus(models.TextChoices):
    """Estado do processamento em background (Celery)"""

    PENDING = "PENDING", "Pendente"
    RUNNING = "RUNNING", "Executando"
    COMPLETED = "COMPLETED", "Concluído"
    SYSTEM_ERROR = "SYSTEM_ERROR", "Erro Interno do Sistema"


class CodeVerdict(models.TextChoices):
    """Resultado lógico da avaliação do código do usuário"""

    PENDING = "PENDING", "Aguardando Avaliação"
    AC = "AC", "Aceito"
    WA = "WA", "Resposta Incorreta"
    TLE = "TLE", "Tempo Limite Excedido"
    RE = "RE", "Erro de Execução"
    MLE = "MLE", "Memória Excedida"
    INSECURE = "INSECURE", "Código Potencialmente Inseguro"


class ExecutionType(models.TextChoices):
    MANUAL = "MANUAL", "Execução Manual"
    VALIDATION = "VALIDATION", "Validação de Questão"


class CodeActivity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="Autor da Execução")
    language = models.CharField(
        max_length=50, choices=ProgrammingLanguages.choices, verbose_name="Linguagem"
    )
    source_code = models.TextField(verbose_name="Código")

    # Diferenciação de fluxo
    activity_type = models.CharField(
        max_length=15,
        choices=ExecutionType.choices,
        default=ExecutionType.MANUAL,
        verbose_name="Tipo de Atividade",
    )

    # Para Execução Manual
    manual_inputs = models.TextField(blank=True, null=True, verbose_name="Entradas")
    manual_stdout = models.TextField(blank=True, null=True, verbose_name="Saída Padrão")
    manual_stderr = models.TextField(blank=True, null=True, verbose_name="Saída de Erro")
    manual_verdict = models.CharField(
        max_length=20, choices=CodeVerdict.choices, default=CodeVerdict.PENDING
    )

    # Para Validação de Questão
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="activities",
        verbose_name="Questão Associada",
    )
    verdict = models.CharField(
        max_length=20,
        choices=CodeVerdict.choices,
        default=CodeVerdict.PENDING,
        verbose_name="Veredito de Validação",
    )

    # Campos Compartilhados
    status = models.CharField(max_length=20, choices=TaskStatus.choices, default=TaskStatus.PENDING)
    task_id = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="ID da Tarefa Celery"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    finished_at = models.DateTimeField(blank=True, null=True, verbose_name="Finalizado em")

    class Meta:
        verbose_name = "Atividade de Código"
        verbose_name_plural = "Atividades de Código"


class ManualRun(CodeActivity):
    """Focado em rodar código solto"""

    objects = ManualRunManager()

    class Meta:
        proxy = True
        verbose_name = "Execução Manual"
        verbose_name_plural = "Execuções Manuais"

    def save(self, *args, **kwargs):
        self.activity_type = ExecutionType.MANUAL
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Execução Manual #{self.id} por {self.user.name} - Status: {self.status}"


class QuestionValidation(CodeActivity):
    """Focado em validar questões contra o banco de testes"""

    objects = QuestionValidationManager()

    class Meta:
        proxy = True
        verbose_name = "Validação de Questão"
        verbose_name_plural = "Validações de Questões"

    def save(self, *args, **kwargs):
        self.activity_type = ExecutionType.VALIDATION
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Validação de Questão #{self.id} por {self.user.name} - Questão: {self.question.title if self.question else 'N/A'} - Status: {self.status}"


class ValidationTestResult(models.Model):
    activity = models.ForeignKey(
        QuestionValidation,
        on_delete=models.CASCADE,
        related_name="test_results",
        verbose_name="Atividade de Validação",
    )
    test = models.ForeignKey(Test, on_delete=models.CASCADE, verbose_name="Teste")

    passed = models.BooleanField(default=False, verbose_name="Teste Aprovado")
    stdout = models.TextField(blank=True, null=True, verbose_name="Saída padrão")
    stderr = models.TextField(blank=True, null=True, verbose_name="Saída de erro")

    class Meta:
        verbose_name = "Resultado de Teste de Validação"

    def __str__(self):
        status = "Aprovado" if self.passed else "Reprovado"
        return f"Teste #{self.test.id} para Atividade #{self.activity.id} - {status}"
