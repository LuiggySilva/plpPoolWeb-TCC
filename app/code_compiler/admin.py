from django.contrib import admin
from django.utils.html import format_html

from .models import (
    CodeVerdict,
    ExecutionType,
    ManualRun,
    QuestionValidation,
    TaskStatus,
    ValidationTestResult,
)


class ValidationTestResultInline(admin.TabularInline):
    model = ValidationTestResult
    extra = 0
    readonly_fields = ("test", "passed_icon", "test_output_data", "stdout", "stderr")
    fields = ("test", "passed_icon", "test_output_data", "stdout", "stderr")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="Saída Esperada")
    def test_output_data(self, obj):
        return obj.test.output_data

    @admin.display(description="Passou?")
    def passed_icon(self, obj):
        color = "green" if obj.passed else "red"
        symbol = "✔" if obj.passed else "✘"
        return format_html('<b style="color: {}; size: 1.2em;">{}</b>', color, symbol)


@admin.register(ManualRun)
class ManualRunAdmin(admin.ModelAdmin):
    list_display = ("user", "language", "colored_verdict", "colored_status", "created_at")
    list_filter = ("language", "status", "manual_verdict")
    search_fields = ("user__username", "question__title")
    ordering = ("-created_at",)

    # Organizando campos para leitura
    readonly_fields = (
        "user",
        "language",
        "source_code",
        "manual_inputs",
        "manual_stdout",
        "manual_stderr",
        "manual_verdict",
        "status",
        "finished_at",
    )

    fieldsets = (
        ("Informações do Autor", {"fields": ("user", "language")}),
        ("Código e Entrada", {"fields": ("source_code", "manual_inputs")}),
        ("Resultado da Execução", {"fields": ("manual_verdict", "manual_stdout", "manual_stderr")}),
        ("Metadados do Sistema", {"fields": ("status", "finished_at")}),
    )

    @admin.display(description="Veredito")
    def colored_verdict(self, obj):
        colors = {CodeVerdict.AC: "green", CodeVerdict.RE: "orange", CodeVerdict.TLE: "red"}
        color = colors.get(obj.manual_verdict, "gray")
        return format_html('<b style="color: {};">{}</b>', color, obj.get_manual_verdict_display())

    @admin.display(description="Status Tarefa")
    def colored_status(self, obj):
        color = "blue" if obj.status == TaskStatus.RUNNING else "var(--body-fg)"
        if obj.status == TaskStatus.SYSTEM_ERROR:
            color = "red"
        return format_html('<span style="color: {};">{}</span>', color, obj.get_status_display())

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(activity_type=ManualRun.activity_type.field.default)
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(QuestionValidation)
class QuestionValidationAdmin(admin.ModelAdmin):
    list_display = ("question", "user", "colored_verdict", "colored_status", "created_at")
    list_filter = ("question", "language", "verdict", "status")
    search_fields = ("user__username", "question__title")
    ordering = ("-created_at",)
    inlines = [ValidationTestResultInline]

    readonly_fields = (
        "question",
        "user",
        "language",
        "source_code",
        "verdict",
        "status",
        "task_id",
        "created_at",
        "finished_at",
    )

    fieldsets = (
        ("Contexto", {"fields": ("question", "user", "language")}),
        ("Submissão", {"fields": ("source_code",)}),
        ("Resultado Final", {"fields": ("verdict", "status", "finished_at")}),
    )

    @admin.display(description="Veredito Final")
    def colored_verdict(self, obj):
        color = "green" if obj.verdict == CodeVerdict.AC else "red"
        return format_html('<b style="color: {};">{}</b>', color, obj.get_verdict_display())

    @admin.display(description="Status Celery")
    def colored_status(self, obj):
        if obj.status == TaskStatus.SYSTEM_ERROR:
            return format_html(
                '<b style="color: white; background: red; padding: 2px 5px;">{}</b>',
                obj.get_status_display(),
            )
        return obj.get_status_display()

    def get_queryset(self, request):
        return super().get_queryset(request).filter(activity_type=ExecutionType.VALIDATION)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
