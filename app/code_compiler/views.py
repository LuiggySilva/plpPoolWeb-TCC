import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from questions.validators import sanitize_program_input

from .models import (
    CodeActivity,
    ExecutionType,
    Question,
    TaskStatus,
)
from .tasks import process_code_activity_task


@require_POST
@login_required
def submit_manual_run_view(request, question_id):
    """Roda input livre"""
    question = get_object_or_404(Question, id=question_id)

    # 1. Verifica se já existe algo rodando para esse usuário
    active_activity = CodeActivity.objects.filter(
        user=request.user, status__in=[TaskStatus.PENDING, TaskStatus.RUNNING]
    ).first()

    if active_activity:
        return JsonResponse(
            {
                "error": "Você já possui uma execução em andamento.",
                "activity_id": str(active_activity.id),
            },
            status=429,
        )  # 429: Too Many Requests

    # 2. Se não tem, cria normalmente
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)

    try:
        sanitized_inputs = sanitize_program_input(data["inputs"])
        data["inputs"] = sanitized_inputs
    except ValidationError as e:
        return JsonResponse({"error": e.message}, status=400)

    activity = CodeActivity.objects.create(
        user=request.user,
        language=data.get("language"),
        source_code=data.get("code"),
        manual_inputs=data.get("inputs", ""),
        activity_type=ExecutionType.MANUAL,
        question=question,
    )

    process_code_activity_task.delay(activity.id)
    return JsonResponse({"activity_id": str(activity.id)})


@require_POST
@login_required
def submit_validation_view(request, question_id):
    """Valida código contra os testes de uma questão específica"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)

    question = get_object_or_404(Question, id=question_id)

    activity = CodeActivity.objects.create(
        user=request.user,
        question=question,
        language=data.get("language"),
        source_code=data.get("code"),
        activity_type=ExecutionType.VALIDATION,
    )

    process_code_activity_task.delay(activity.id)
    return JsonResponse({"activity_id": str(activity.id)})


@login_required
def check_activity_status_view(request, activity_id):
    """Verifica o status de uma atividade (execução de código)"""
    activity = get_object_or_404(CodeActivity, id=activity_id, user=request.user)

    response = {
        "status": activity.status,
        "activity_type": activity.activity_type,
        "finished_at": activity.finished_at,
        "delta": (
            (activity.finished_at - activity.created_at).total_seconds()
            if activity.finished_at
            else None
        ),
    }

    # Execução Manual
    if activity.activity_type == ExecutionType.MANUAL:
        response["stdout"] = activity.manual_stdout
        response["stderr"] = activity.manual_stderr
        response["verdict"] = activity.manual_verdict

    # Validação de Casos de Teste
    elif activity.activity_type == ExecutionType.VALIDATION:
        test_results = []

        for run in activity.test_results.all():
            test_results.append(
                {
                    "test_id": run.test_id,
                    "passed": run.passed,
                    "actual_output": run.stdout,
                    "stderr": run.stderr,
                }
            )

        response["test_results"] = test_results

    # Tratamento de Erro Crítico (Infra/Docker)
    if activity.status == TaskStatus.SYSTEM_ERROR:
        response["is_system_error"] = True

    return JsonResponse(response)
