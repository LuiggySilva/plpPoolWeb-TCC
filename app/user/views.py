import io
import json
import zipfile
from itertools import chain
from operator import attrgetter

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import TemplateView

from code_compiler.models import ManualRun, QuestionValidation
from code_compiler.services import LanguageExtensions
from questions.forms import PeriodForm
from questions.models import Period, ProgrammingLanguages, Question, Tag, Test
from questions.utils import (
    get_days_from_request,
    get_history_with_diff,
    htmx_modal_response,
)

from .forms import (
    AssistentStudentCreationForm,
    BulkImportForm,
    ProfessorCreationForm,
    SystemSettingsForm,
)
from .models import AssistentStudent, Professor, SystemSetting
from .utils import (
    FieldStatus,
    check_similarity,
    get_periods_with_active_flag,
    get_validation_sets,
    process_database_import,
    validate_import_item,
)


@login_required
def download_backup(request):
    """Permite que um professor baixe um backup completo das questões em formato ZIP, contendo os códigos, descrições, testes e um arquivo JSON com todos os dados estruturados."""
    if not request.user.is_staff:
        messages.warning(request, "Permissão negada.")
        return redirect("questions:question_list")

    zip_buffer = io.BytesIO()
    all_questions_json = []

    questions = Question.objects.select_related("period", "author").prefetch_related(
        "tags", "tests"
    )

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for q in questions:
            author_data = {}
            if q.author:
                author_data = {
                    "name": getattr(q.author, "name", ""),
                    "github_url": getattr(q.author, "github_url", getattr(q.author, "github", "")),
                    "email": getattr(q.author, "email", ""),
                    "registration": getattr(q.author, "registration", ""),
                }

            q_dict = {
                "title": q.title,
                "description": q.description,
                "code": q.code,
                "language": q.language,
                "type": q.type,
                "period": q.period.name if q.period else None,
                "tags": list(q.tags.values_list("slug", flat=True)),
                "author": author_data,
                "tests": [
                    {
                        "input_data": t.input_data,
                        "output_data": t.output_data,
                        "type": t.type,
                    }
                    for t in q.tests.all()
                ],
            }
            all_questions_json.append(q_dict)

            period_folder = q.period.name if q.period else "sem-periodo"
            lang_folder = (
                slugify(q.get_language_display()) if q.language != "cplusplus" else "c_c++"
            )

            type_folder = slugify(q.get_type_display())
            question_folder = f"{q.id}-{slugify(q.title)}"
            base_path = f"{period_folder}/{lang_folder}/{type_folder}/{question_folder}"

            ext = LanguageExtensions.get(q.language)
            code_filename = f"{base_path}/codigo.{ext}"
            zip_file.writestr(code_filename, (q.code or "").replace("\r\n", "\n"))

            txt_filename = f"{base_path}/info.txt"

            tags_str = ", ".join([t.slug for t in q.tags.all()])
            tests_str = ""
            for idx, t in enumerate(q.tests.all(), 1):
                tests_str += f"--- TESTE {idx} [{t.type.upper()}] ---\n"
                tests_str += f"ENTRADA:\n{t.input_data}\nSAÍDA:\n{t.output_data}\n\n"

            txt_content = (
                f"ENUNCIADO: {q.title}\n"
                f"LINGUAGEM: {q.get_language_display()}\n"
                f"TIPO: {q.get_type_display()}\n"
                f"TAGS: {tags_str}\n\n"
                f"=== AUTOR ===\n"
                f"Nome: {author_data.get('name', 'N/A')}\n"
                f"Email: {author_data.get('email', 'N/A')}\n"
                f"Matrícula: {author_data.get('registration', 'N/A')}\n"
                f"GitHub: {author_data.get('github_url', 'N/A')}\n\n"
                f"=== DESCRIÇÃO ===\n"
                f"{q.description}\n\n"
                f"=== TESTES ===\n"
                f"{tests_str}"
            )
            zip_file.writestr(txt_filename, txt_content)

        json_content = json.dumps(all_questions_json, indent=2, ensure_ascii=False)
        zip_file.writestr("backup.json", json_content)

    zip_buffer.seek(0)

    timestamp = timezone.localtime().strftime("%Y%m%d_%H%M%S")
    filename = f"backup_questoes_{timestamp}.zip"

    return FileResponse(zip_buffer, as_attachment=True, filename=filename)


@login_required
def bulk_import_questions(request):
    """
    Permite que um professor importe em massa questões a partir de um arquivo JSON ou texto colado,
    com uma pré-visualização detalhada dos dados, validação estruturada e detecção de duplicatas, além de opções para criar períodos e tags ausentes.
    O processo é dividido em duas fases:
        1) Geração do Preview, onde o professor pode revisar cada questão importada, ver erros de validação e possíveis duplicatas antes de confirmar a importação.
        2) Confirmação do Preview, onde as questões selecionadas são efetivamente salvas no banco de dados.
    """
    if not request.user.is_staff:
        messages.warning(request, "Permissão negada.")
        return redirect("questions:question_list")

    # FASE 2: CONFIRMAÇÃO DO PREVIEW E IMPORTAÇÃO DEFINITIVA
    if request.method == "POST" and "confirm_preview" in request.POST:
        raw_json = request.POST.get("json_data_dump")
        selected_indices = request.POST.getlist("import_indices")

        create_missing_str = request.POST.get("create_missing", "off")
        create_missing = create_missing_str.lower() in ["true", "1", "on"]

        if not raw_json or not selected_indices:
            messages.error(request, "Nenhuma questão selecionada ou dados corrompidos.")
            return redirect("user:bulk_import_questions")

        try:
            json_data = json.loads(raw_json)
            selected_indices_int = [int(i) for i in selected_indices]
            selected_items = [
                item for idx, item in enumerate(json_data) if idx in selected_indices_int
            ]
            q_created, t_created = process_database_import(selected_items, create_missing)

            messages.success(
                request,
                f"Sucesso! {q_created} questões e {t_created} testes importados.",
            )
            return redirect("questions:question_list")

        except ValueError as ve:
            messages.error(request, f"Importação abortada: {str(ve)}")
            return redirect("user:bulk_import_questions")
        except Exception as e:
            messages.error(request, f"Erro crítico ao salvar no banco: {str(e)}")
            return redirect("user:bulk_import_questions")

    # FASE 1: GERAÇÃO DO PREVIEW E VALIDAÇÃO
    form = BulkImportForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        try:
            if form.cleaned_data.get("json_file"):
                json_data = json.load(request.FILES["json_file"])
            else:
                json_data = json.loads(form.cleaned_data["json_text"])
        except json.JSONDecodeError as e:
            messages.error(request, f"Erro de formatação no JSON: {e}")
            return redirect("user:bulk_import_questions")

        if not isinstance(json_data, list):
            messages.error(request, "O JSON deve ser uma lista de questões (array de objetos).")
            return redirect("user:bulk_import_questions")

        create_missing_str = request.POST.get("create_missing", "off")
        create_missing = create_missing_str.lower() in ["true", "1", "on"]

        valid_sets = get_validation_sets()
        target_languages = list(
            {item.get("language", ProgrammingLanguages.CPP) for item in json_data}
        )
        existing_questions = list(Question.objects.filter(language__in=target_languages))

        tag_map = {t.slug: t.name for t in Tag.objects.all()}
        valid_sets["tag_map"] = tag_map
        lang_map = dict(ProgrammingLanguages.choices)

        new_periods_to_create = set()
        new_tags_to_create = set()
        preview_list = []
        has_errors = False

        for index, item in enumerate(json_data):
            item_errors, period_info, tags_info = validate_import_item(
                item, valid_sets, create_missing
            )
            if item_errors:
                has_errors = True

            display_data = item.copy()

            display_data["period_display"] = period_info["name"]
            display_data["period_type"] = period_info["type"]
            if period_info["type"] == FieldStatus.NEW and period_info["name"]:
                new_periods_to_create.add(period_info["name"])

            display_data["tags_display"] = tags_info
            for tag in tags_info:
                if tag["type"] == FieldStatus.NEW:
                    new_tags_to_create.add(tag["slug"])

            lang_key = item.get("language")
            display_data["language_display"] = lang_map.get(lang_key, lang_key)

            duplicate_found = check_similarity(
                new_title=item.get("title", ""),
                new_desc=item.get("description", ""),
                new_code=item.get("code", ""),
                new_language=item.get("language", ""),
                existing_questions=existing_questions,
            )

            if duplicate_found:
                inst = duplicate_found["instance"]
                dup_dict = {
                    "id": inst.id,
                    "title": inst.title,
                    "author": {
                        "name": inst.author.name,
                        "email": getattr(inst.author, "email", ""),
                        "registration": getattr(inst.author, "registration", ""),
                        "github": getattr(inst.author, "github", ""),
                    },
                    "description": inst.description,
                    "language": lang_map.get(inst.language),
                    "period": inst.period.name,
                    "tags": [t.slug for t in inst.tags.all()],
                    "tests_count": inst.tests.count(),
                    "tests": list(inst.tests.values("input_data", "output_data", "type")),
                }
                duplicate_found["json_data"] = json.dumps(dup_dict, indent=2, ensure_ascii=False)

            preview_list.append(
                {
                    "index": index,
                    "data": display_data,
                    "raw_data": item,
                    "json_formatted": json.dumps(display_data, indent=2, ensure_ascii=False),
                    "duplicate": duplicate_found,
                    "validation_errors": item_errors,
                }
            )

        preview_list.sort(
            key=lambda x: (
                0 if x["duplicate"] else 1,
                0 if x["validation_errors"] else 1,
            )
        )

        if has_errors:
            messages.error(
                request,
                "Existem erros estruturais ou itens inválidos no JSON. Corrija antes de continuar.",
            )

        return render(
            request,
            "user/bulk_import_preview.html",
            {
                "preview_list": preview_list,
                "json_data_dump": json.dumps(json_data),
                "create_missing": create_missing,
                "new_periods": sorted(new_periods_to_create),
                "new_tags": sorted(new_tags_to_create),
            },
        )

    # GET INICIAL OU FORMULÁRIO INVÁLIDO - EXIBE A PÁGINA DE IMPORTAÇÃO
    context = {
        "form": form,
        "periods": Period.objects.all().order_by("-name"),
        "tags": Tag.objects.all().order_by("name"),
        "test_types": Test.TestType.choices,
        "question_types": Question.Types.choices,
        "languages": ProgrammingLanguages.choices,
    }
    return render(request, "user/bulk_import.html", context)


def about(request):
    """
    Exibe uma página "Sobre" com informações sobre o sistema, equipe de desenvolvimento e tecnologias utilizadas.
    A página é acessível a todos os usuários, mas destaca as contribuições dos professores e monitores para a construção do acervo de questões.
    """
    return render(request, "user/about.html", context={})


class ProfessorAdminPageView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Exibe uma página de administração para professores, onde eles podem gerenciar configurações do sistema,
    visualizar histórico de alterações, monitorar execuções de código e validar questões.
    A página é protegida para acesso apenas por usuários com permissão de staff.
    """

    template_name = "user/professor_adminpage.html"

    def test_func(self):
        return self.request.user.is_staff

    def get_system_form(self):
        if self.request.method == "POST":
            return SystemSettingsForm(self.request.POST, instance=SystemSetting.get_solo())
        return SystemSettingsForm(instance=SystemSetting.get_solo())

    def post(self, request):
        form = self.get_system_form()

        if form.is_valid():
            if form.has_changed():
                config = form.save(commit=False)
                config.save()
                messages.success(request, "Configurações atualizadas!")
            else:
                messages.info(request, "Nenhuma alteração realizada!")
            return redirect("user:professor_adminpage")
        messages.error(
            request,
            "Erro ao atualizar configurações. Verifique os dados e tente novamente.",
        )

        return self.render_to_response(self.get_context_data(system_settings_form=form))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        settings = SystemSetting.get_solo()

        if "system_settings_form" not in context:
            context["system_settings_form"] = self.get_system_form()

        days = get_days_from_request(self.request)

        # Buscar histórico de alterações das configurações do sistema
        history_qs = (
            settings.history.days_ago(days).select_related("history_user").order_by("-history_date")
        )
        system_settings_history = get_history_with_diff(settings, history_qs)

        period_ids = set()
        verbose_name_active_period = SystemSetting._meta.get_field("active_period").verbose_name

        # Coletar IDs de períodos antigos e novos para otimizar consultas e exibição no histórico
        for record in system_settings_history:
            if record.changes_list:
                for change in record.changes_list:
                    if change["field"].lower() == verbose_name_active_period.lower():
                        if change["old"]:
                            period_ids.add(int(change["old"]))
                        if change["new"]:
                            period_ids.add(int(change["new"]))

        # Criar um lookup de ID para nome dos períodos envolvidos no histórico para exibição amigável
        periods_lookup = {p.id: p.name for p in Period.objects.filter(id__in=period_ids)}

        # Adicionar campos de exibição amigável para os períodos antigos e novos em cada registro do histórico
        for record in system_settings_history:
            if record.changes_list:
                for change in record.changes_list:
                    if change["field"].lower() == verbose_name_active_period.lower():
                        old_id = int(change["old"]) if change["old"] else None
                        new_id = int(change["new"]) if change["new"] else None

                        change["old_display"] = periods_lookup.get(old_id, "—") if old_id else "—"
                        change["new_display"] = periods_lookup.get(new_id, "—") if new_id else "—"

        # Buscar execuções de código recentes para exibir na aba de auditoria, ordenando por data de criação
        manual_runs = ManualRun.objects.days_ago(days).select_related("user", "question")
        validations = QuestionValidation.objects.days_ago(days).select_related("user", "question")
        all_executions = sorted(
            chain(manual_runs, validations), key=attrgetter("created_at"), reverse=True
        )

        context.update(
            {
                "current_tab": "professor_adminpage",
                "periods": get_periods_with_active_flag(),
                "system_settings_history": system_settings_history,
                "selected_days": days,
                "tags": Tag.objects.all(),
                "assistent_students": AssistentStudent.objects.all(),
                "professors": Professor.objects.all(),
                "last_modified": settings.history.first().history_date,
                "max_tests": Question.MAX_TESTS_COUNT,
                "last_modified_by": (
                    settings.history.first().history_user.email
                    if settings.history.first().history_user
                    else "Sistema"
                ),
                "all_executions": all_executions,
            }
        )

        # Ajustar template para respostas HTMX específicas, permitindo que as abas de auditoria sejam atualizadas dinamicamente sem recarregar a página inteira
        if self.request.htmx:
            if self.request.headers.get("Hx-Target") == "audit-content-area":
                self.template_name = "user/partials/systemsettings_audit_history.html"
            elif self.request.headers.get("Hx-Target") == "code-exectution-audit-content-area":
                self.template_name = "user/partials/codeexecution_audit_history.html"

        return context


def render_updated_periods_table(request):
    """
    Renderiza a tabela atualizada de períodos para resposta HTMX após operações de criação, edição, exclusão ou restauração de períodos,
    garantindo que a interface do usuário reflita as mudanças sem recarregar a página inteira.
    """
    periods = get_periods_with_active_flag()

    table_html = render_to_string(
        "user/partials/period/periods_table_list.html",
        {"periods": periods},
        request=request,
    )
    select_html = render_to_string(
        "user/partials/period/period_select_options.html",
        {"periods": periods},
        request=request,
    )

    return HttpResponse(table_html + select_html)


@login_required
@user_passes_test(lambda u: u.is_staff)
def period_create(request):
    """Permite que um professor crie um novo período através de um formulário modal, com validação e atualização dinâmica da tabela de períodos usando HTMX."""
    form = PeriodForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        return htmx_modal_response(
            request,
            render_updated_periods_table,
            "#period-table-body",
            "#modalPeriodForm",
            "#modalPeriodList",
        )

    return render(
        request,
        "user/partials/period/period_form_inner.html",
        {"period": None, "period_form": form, "action": "create"},
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
def period_edit(request, period_id):
    """Permite que um professor edite um período existente através de um formulário modal, com validação e atualização dinâmica da tabela de períodos usando HTMX."""
    period = get_object_or_404(Period, id=period_id)
    form = PeriodForm(request.POST or None, instance=period)

    if request.method == "POST" and form.is_valid():
        form.save()
        return htmx_modal_response(
            request,
            render_updated_periods_table,
            "#period-table-body",
            "#modalPeriodForm",
            "#modalPeriodList",
        )

    return render(
        request,
        "user/partials/period/period_form_inner.html",
        {"period": period, "period_form": form, "action": "edit"},
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
def period_delete(request, period_id):
    """Permite que um professor exclua um período existente através de um formulário modal de confirmação, com atualização dinâmica da tabela de períodos usando HTMX após a exclusão."""
    period = get_object_or_404(Period, id=period_id)

    if request.method == "POST":
        period.delete()
        return htmx_modal_response(
            request,
            render_updated_periods_table,
            "#period-table-body",
            "#modalPeriodDelete",
            "#modalPeriodList",
        )

    return render(request, "user/partials/period/period_delete_inner.html", {"period": period})


@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def period_restore(request, period_id):
    """Permite que um professor restaure um período excluído anteriormente, recuperando a última versão histórica do período e salvando-a novamente, com atualização dinâmica da tabela de períodos usando HTMX após a restauração."""
    period = get_object_or_404(Period, id=period_id)

    latest_history = Period.history.filter(id=period.id).latest()
    restored_period = latest_history.instance
    restored_period.id = period_id
    restored_period.save()

    return htmx_modal_response(
        request,
        render_updated_periods_table,
        "#period-table-body",
        "#modalPeriodHistory",
        "#modalPeriodList",
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
@require_GET
def period_history(request, period_id):
    """Permite que um professor visualize o histórico de alterações de um período específico, filtrando por período selecionado e otimizando consultas relacionadas a usuários e períodos envolvidos nas mudanças."""
    period = get_object_or_404(Period, id=period_id)
    days = get_days_from_request(request)

    period_history_qs = (
        period.history.days_ago(days).select_related("history_user").order_by("-history_date")
    )
    history_records = get_history_with_diff(period, period_history_qs)

    return render(
        request,
        "user/partials/period/period_history.html",
        {"period": period, "history_records": history_records, "selected_days": days},
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
@require_GET
def period_deleted_history(request):
    """Permite que um professor visualize o histórico de períodos excluídos, filtrando por intervalo de tempo e otimizando consultas relacionadas a usuários envolvidos nas exclusões."""
    days = get_days_from_request(request)

    deleted_qs = (
        Period.history.days_ago(days)
        .filter(history_type="-")
        .select_related("history_user")
        .order_by("-history_date")
    )

    return render(
        request,
        "user/partials/period/periods_deleted_list.html",
        {"records": deleted_qs, "selected_days": days},
    )


def render_updated_assistent_students_table(request):
    """
    Renderiza a tabela atualizada de monitores para resposta HTMX após operações de criação, edição, exclusão ou restauração de monitores,
    garantindo que a interface do usuário reflita as mudanças sem recarregar a página inteira.
    """
    return render(
        request,
        "user/partials/assistentstudent/assistentstudents_table_list.html",
        {"assistent_students": AssistentStudent.objects.all()},
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
def monitor_list(request):
    """Permite que um professor visualize a lista de monitores, com funcionalidade de busca por nome, email ou matrícula, e ordenação alfabética por nome."""
    search_query = request.GET.get("search", "")
    monitors = AssistentStudent.objects.all().order_by("name")

    if search_query:
        monitors = monitors.filter(
            Q(name__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(registration__icontains=search_query)
        )

    context = {"assistent_students": monitors}
    return render(
        request,
        "user/partials/assistentstudent/assistentstudents_table_list.html",
        context,
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
def monitor_create(request):
    """Permite que um professor crie um novo monitor através de um formulário modal, com validação e atualização dinâmica da tabela de monitores usando HTMX após a criação."""
    form = AssistentStudentCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return htmx_modal_response(
            request,
            render_updated_assistent_students_table,
            "#monitor-table-body",
            "#modalMonitorForm",
            "#modalMonitorList",
        )

    return render(
        request,
        "user/partials/assistentstudent/assistentstudent_form_inner.html",
        {"assistentstudent": None, "assistentstudent_form": form, "action": "create"},
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
def monitor_edit(request, monitor_id):
    """Permite que um professor edite um monitor existente através de um formulário modal, com validação e atualização dinâmica da tabela de monitores usando HTMX após a edição."""
    monitor = get_object_or_404(AssistentStudent, id=monitor_id)
    form = AssistentStudentCreationForm(request.POST or None, instance=monitor)

    if request.method == "POST" and form.is_valid():
        form.save()
        return htmx_modal_response(
            request,
            render_updated_assistent_students_table,
            "#monitor-table-body",
            "#modalMonitorForm",
            "#modalMonitorList",
        )

    return render(
        request,
        "user/partials/assistentstudent/assistentstudent_form_inner.html",
        {"assistentstudent": monitor, "assistentstudent_form": form, "action": "edit"},
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
def monitor_delete(request, monitor_id):
    """Permite que um professor exclua um monitor existente através de um formulário modal de confirmação, com atualização dinâmica da tabela de monitores usando HTMX após a exclusão."""
    monitor = get_object_or_404(AssistentStudent, id=monitor_id)

    if request.method == "POST":
        monitor.delete()
        return htmx_modal_response(
            request,
            render_updated_assistent_students_table,
            "#monitor-table-body",
            "#modalMonitorDelete",
            "#modalMonitorList",
        )

    return render(
        request,
        "user/partials/assistentstudent/assistentstudent_delete_inner.html",
        {"assistentstudent": monitor},
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def monitor_reset_password(request, monitor_id):
    """Permite que um professor resete a senha de um monitor para o valor padrão (matrícula), com atualização dinâmica da tabela de monitores usando HTMX após o reset."""
    monitor = get_object_or_404(AssistentStudent, id=monitor_id)
    monitor.set_password(monitor.registration)
    monitor.save()

    return htmx_modal_response(
        request,
        render_updated_assistent_students_table,
        "#monitor-table-body",
        "#modalMonitorForm",
        "#modalMonitorList",
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def monitor_restore(request, monitor_id):
    """Permite que um professor restaure um monitor excluído anteriormente, recuperando a última versão histórica do monitor e salvando-a novamente, com atualização dinâmica da tabela de monitores usando HTMX após a restauração."""
    monitor = get_object_or_404(AssistentStudent, id=monitor_id)

    latest_history = AssistentStudent.history.filter(id=monitor.id).latest()
    restored_monitor = latest_history.instance
    restored_monitor.id = monitor_id
    restored_monitor.save()

    return htmx_modal_response(
        request,
        render_updated_assistent_students_table,
        "#monitor-table-body",
        "#modalMonitorHistory",
        "#modalMonitorList",
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
def monitor_history(request, monitor_id):
    """Permite que um professor visualize o histórico de alterações de um monitor específico, filtrando por intervalo de dias e otimizando consultas relacionadas a usuários envolvidos nas mudanças."""
    monitor = get_object_or_404(AssistentStudent, id=monitor_id)
    days = get_days_from_request(request)
    history_qs = (
        monitor.history.days_ago(days).select_related("history_user").order_by("-history_date")
    )

    return render(
        request,
        "user/partials/assistentstudent/assistentstudent_history.html",
        {
            "assistentstudent": monitor,
            "history_records": get_history_with_diff(monitor, history_qs),
            "selected_days": days,
        },
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
def monitor_deleted_history(request):
    """Permite que um professor visualize o histórico de monitores excluídos, filtrando por intervalo de dias e otimizando consultas relacionadas a usuários envolvidos nas exclusões."""
    days = get_days_from_request(request)
    deleted = (
        AssistentStudent.history.days_ago(days)
        .filter(history_type="-")
        .select_related("history_user")
        .order_by("-history_date")
    )

    return render(
        request,
        "user/partials/assistentstudent/assistentstudents_deleted_list.html",
        {"records": deleted, "selected_days": days},
    )


def render_updated_professors_table(request):
    """
    Renderiza a tabela atualizada de professores para resposta HTMX após operações de criação, edição, exclusão ou restauração de professores,
    garantindo que a interface do usuário reflita as mudanças sem recarregar a página inteira.
    """
    return render(
        request,
        "user/partials/professor/professors_table_list.html",
        {"professors": Professor.objects.all()},
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
def professor_list(request):
    """Permite que um professor visualize a lista de professores, com funcionalidade de busca por nome, email ou matrícula, e ordenação alfabética por nome."""
    search_query = request.GET.get("search", "")
    professors = Professor.objects.all().order_by("name")

    if search_query:
        professors = professors.filter(
            Q(name__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(registration__icontains=search_query)
        )

    context = {"professors": professors}
    return render(request, "user/partials/professor/professors_table_list.html", context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def professor_create(request):
    """Permite que um professor crie um novo professor através de um formulário modal, com validação e atualização dinâmica da tabela de professores usando HTMX após a criação."""
    form = ProfessorCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return htmx_modal_response(
            request,
            render_updated_professors_table,
            "#professor-table-body",
            "#modalProfessorForm",
            "#modalProfessorList",
        )

    return render(
        request,
        "user/partials/professor/professor_form_inner.html",
        {"professor": None, "professor_form": form, "action": "create"},
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
def professor_edit(request, professor_id):
    """Permite que um professor edite um professor existente através de um formulário modal, com validação e atualização dinâmica da tabela de professores usando HTMX após a edição."""
    professor = get_object_or_404(Professor, id=professor_id)

    if professor.is_superuser:
        messages.error(request, "Não é permitido editar um superusuário.")
        return htmx_modal_response(
            request,
            render_updated_professors_table,
            "#professor-table-body",
            "#modalProfessorForm",
            "#modalProfessorList",
        )

    form = ProfessorCreationForm(request.POST or None, instance=professor)
    if request.method == "POST" and form.is_valid():
        form.save()
        return htmx_modal_response(
            request,
            render_updated_professors_table,
            "#professor-table-body",
            "#modalProfessorForm",
            "#modalProfessorList",
        )

    return render(
        request,
        "user/partials/professor/professor_form_inner.html",
        {"professor": professor, "professor_form": form, "action": "edit"},
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
def professor_delete(request, professor_id):
    """Permite que um professor exclua um professor existente, com validação e atualização dinâmica da tabela de professores usando HTMX após a exclusão."""
    professor = get_object_or_404(Professor, id=professor_id)

    if request.method == "POST":
        if professor.is_superuser:
            messages.error(request, "Não é permitido excluir um superusuário.")
        else:
            professor.delete()
        return htmx_modal_response(
            request,
            render_updated_professors_table,
            "#professor-table-body",
            "#modalProfessorDelete",
            "#modalProfessorList",
        )

    return render(
        request,
        "user/partials/professor/professor_delete_inner.html",
        {"professor": professor},
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def professor_reset_password(request, professor_id):
    """Permite que um professor resete a senha de um professor para o valor padrão (matrícula), com validação para evitar reset de superusuários e atualização dinâmica da tabela de professores usando HTMX após o reset."""
    professor = get_object_or_404(Professor, id=professor_id)

    if professor.is_superuser:
        messages.error(request, "Não é permitido resetar a senha de um superusuário.")
    else:
        professor.set_password(professor.registration)
        professor.save()

    return htmx_modal_response(
        request,
        render_updated_professors_table,
        "#professor-table-body",
        "#modalProfessorForm",
        "#modalProfessorList",
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def professor_restore(request, professor_id):
    """Permite que um professor restaure um professor excluído anteriormente, recuperando a última versão histórica do professor e salvando-a novamente, com validação para evitar restauração de superusuários e atualização dinâmica da tabela de professores usando HTMX após a restauração."""
    professor = get_object_or_404(Professor, id=professor_id)

    latest_history = Professor.history.filter(id=professor.id).latest()
    restored_prof = latest_history.instance
    restored_prof.id = professor_id
    restored_prof.save()

    return htmx_modal_response(
        request,
        render_updated_professors_table,
        "#professor-table-body",
        "#modalProfessorHistory",
        "#modalProfessorList",
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
def professor_history(request, professor_id):
    """Permite que um professor visualize o histórico de alterações de um professor específico, filtrando por intervalo de dias e otimizando consultas relacionadas a usuários envolvidos nas mudanças, além de exibir as diferenças entre as versões para facilitar a compreensão das alterações realizadas."""
    professor = get_object_or_404(Professor, id=professor_id)
    days = get_days_from_request(request)
    history_qs = (
        professor.history.days_ago(days).select_related("history_user").order_by("-history_date")
    )

    return render(
        request,
        "user/partials/professor/professor_history.html",
        {
            "professor": professor,
            "history_records": get_history_with_diff(professor, history_qs),
            "selected_days": days,
        },
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
def professor_deleted_history(request):
    """Permite que um professor visualize o histórico de professores excluídos, filtrando por intervalo de dias e otimizando consultas relacionadas a usuários envolvidos nas exclusões, além de exibir as diferenças entre as versões para facilitar a compreensão das alterações realizadas."""
    days = get_days_from_request(request)
    deleted = (
        Professor.history.days_ago(days)
        .filter(history_type="-")
        .select_related("history_user")
        .order_by("-history_date")
    )

    return render(
        request,
        "user/partials/professor/professors_deleted_list.html",
        {"records": deleted, "selected_days": days},
    )
