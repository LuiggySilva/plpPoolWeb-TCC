from celery import shared_task

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils import timezone

from questions.models import Test
from user.models import SystemSetting

from .models import (
    CodeActivity,
    CodeVerdict,
    ExecutionType,
    TaskStatus,
    ValidationTestResult,
)
from .utils import get_executor


@shared_task(bind=True)
def process_code_activity_task(self, activity_id):
    try:
        activity = CodeActivity.objects.get(id=activity_id)
        activity.status = TaskStatus.RUNNING
        activity.task_id = self.request.id
        activity.save()

        executor = get_executor()

        # Execução Manual
        if activity.activity_type == ExecutionType.MANUAL:
            res = executor.execute(activity.language, activity.source_code, activity.manual_inputs)

            if res.get("is_system_error"):
                activity.manual_verdict = CodeVerdict.PENDING
                activity.manual_stderr = (
                    "Ocorreu um erro interno no servidor ao tentar rodar seu código."
                )
                activity.status = TaskStatus.SYSTEM_ERROR

            elif res.get("is_timeout"):
                activity.manual_verdict = CodeVerdict.TLE
                activity.manual_stderr = f"Tempo Limite Excedido. O código demorou mais que {executor.TIMEOUT} segundos para finalizar."

            else:
                activity.manual_stdout = res.get("stdout", "")
                activity.manual_stderr = res.get("stderr", "")
                activity.manual_verdict = (
                    CodeVerdict.RE if res.get("exit_code") != 0 else CodeVerdict.AC
                )

            if activity.status != TaskStatus.SYSTEM_ERROR:
                activity.status = TaskStatus.COMPLETED

        # Execução para Validação de Testes
        elif activity.activity_type == ExecutionType.VALIDATION:
            tests = activity.question.tests.all()
            final_verdict = CodeVerdict.AC

            for test in tests:
                res = executor.execute(activity.language, activity.source_code, test.input_data)

                current_test_verdict = CodeVerdict.AC
                is_passed = False
                stdout_clean = ""
                stderr_clean = ""

                # Avaliação de Erros de Sistema e TLE
                if res.get("is_system_error"):
                    current_test_verdict = CodeVerdict.PENDING
                    stderr_clean = "Erro interno no servidor ao validar este caso de teste."
                    activity.status = TaskStatus.SYSTEM_ERROR  # Falha estrutural
                    break  # Interrompe os testes se o servidor quebrou

                if res.get("is_timeout"):
                    current_test_verdict = CodeVerdict.TLE
                    stderr_clean = "Tempo limite excedido neste caso de teste."

                # Avaliação Normal (Executou até o fim)
                else:
                    stdout_clean = res.get("stdout", "").strip()
                    stderr_clean = res.get("stderr", "")
                    exit_code = res.get("exit_code")

                    actual_output = Test.normalize_text(stdout_clean).splitlines()
                    expected_output = Test.normalize_text(test.output_data).splitlines()

                    if exit_code != 0:
                        current_test_verdict = CodeVerdict.RE
                    elif actual_output != expected_output:
                        current_test_verdict = CodeVerdict.WA
                    else:
                        is_passed = True

                # Registra o resultado deste teste
                ValidationTestResult.objects.create(
                    activity=activity,
                    test=test,
                    passed=is_passed,
                    stdout=stdout_clean,
                    stderr=stderr_clean,
                )

                # Atualiza o veredito final (o primeiro erro "suja" a submissão toda)
                if not is_passed and final_verdict == CodeVerdict.AC:
                    final_verdict = current_test_verdict

            activity.verdict = final_verdict
            if activity.status != TaskStatus.SYSTEM_ERROR:
                activity.status = TaskStatus.COMPLETED

    except Exception:
        # Se algo quebrar FORA do sandbox (ex: falha no banco de dados)
        activity.status = TaskStatus.SYSTEM_ERROR
        activity.manual_stderr = "Falha crítica no sistema de submissão."

    finally:
        activity.finished_at = timezone.now()
        activity.save()

    return activity.status


@shared_task
def check_and_send_deadline_reminders():
    setting = SystemSetting.get_solo()
    if not setting or not setting.active_period:
        return "Sem período ativo."

    monitors = setting.active_period.users.all()
    recipients = [m.email for m in monitors if m.email]
    if not recipients:
        return "Sem destinatários."

    hoje = timezone.localdate()

    languages = [
        {
            "name": "C/C++",
            "qtd": setting.min_basic_cpp_questions + setting.min_advanced_cpp_questions,
            "deadline": setting.cpp_deadline,
        },
        {
            "name": "Haskell",
            "qtd": setting.min_basic_haskell_questions + setting.min_advanced_haskell_questions,
            "deadline": setting.haskell_deadline,
        },
        {
            "name": "Prolog",
            "qtd": setting.min_basic_prolog_questions + setting.min_advanced_prolog_questions,
            "deadline": setting.prolog_deadline,
        },
    ]

    emails_sent = 0
    for lang in languages:
        if lang["qtd"] > 0 and lang["deadline"]:
            deadline_date = timezone.localtime(lang["deadline"]).date()
            remaining_days = (deadline_date - hoje).days

            cache_key_7d = f"reminder_7d_{setting.id}_{lang['name']}"
            cache_key_1d = f"reminder_1d_{setting.id}_{lang['name']}"

            if 1 < remaining_days <= 7 and not cache.get(cache_key_7d):
                send_email_reminder(
                    lang["name"], f"{remaining_days} dias", lang["deadline"], recipients
                )
                cache.set(cache_key_7d, True, timeout=None)
                emails_sent += 1

            elif 0 <= remaining_days <= 1 and not cache.get(cache_key_1d):
                send_email_reminder(lang["name"], "1 dia", lang["deadline"], recipients)
                cache.set(cache_key_1d, True, timeout=None)
                emails_sent += 1

    return f"Task concluída. {emails_sent} lembretes disparados."


def send_email_reminder(language, remaining_time, deadline_datetime, recipients):
    """Função auxiliar para montar e enviar o e-mail"""
    deadline_local = timezone.localtime(deadline_datetime)
    formatted_date = deadline_local.strftime("%d/%m/%Y às %H:%M")

    subject = (
        f"{settings.EMAIL_SUBJECT_PREFIX} Lembrete: Prazo de {language} encerra em {remaining_time}"
    )
    message = (
        f"Olá,\n\n"
        f"Este é um lembrete automático de que o prazo final para o cadastro de questões de {language} "
        f"se encerra em {remaining_time} ({formatted_date}).\n\n"
        f"Por favor, certifique-se de que a meta de questões foi atingida no sistema.\n\n"
        f"Atenciosamente,\nEquipe plpPoolWeb"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        fail_silently=False,
    )
