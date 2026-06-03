import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import (
    DetailView,
    ListView,
    TemplateView,
)

from code_compiler.models import CodeActivity, TaskStatus
from user.models import SystemSetting

from .forms import QuestionFilter, QuestionForm, TagForm, TestFormSet, TestFormSetHelper
from .models import ProgrammingLanguages, Question, Tag, Test
from .utils import (
    get_days_from_request,
    get_default_days,
    get_history_with_diff,
    htmx_modal_response,
)

logger = logging.getLogger(__name__)


class AssistentStudentQuestionListView(LoginRequiredMixin, TemplateView):
    """View para listar as questões criadas pelo assistente de aluno, com informações adicionais sobre o progresso do assistente."""

    template_name = "questions/assistentstudent_questions.html"

    def get_context_data(self, **kwargs):

        active_period = SystemSetting.get_solo().active_period
        user_questions = Question.objects.filter(
            author=self.request.user, period=active_period
        ).order_by("-created_at")

        counts = user_questions.aggregate(
            basic_c_cpp=Count(
                "id",
                filter=Q(
                    language__in=[ProgrammingLanguages.C, ProgrammingLanguages.CPP],
                    type=Question.Types.BASIC,
                ),
            ),
            advanced_c_cpp=Count(
                "id",
                filter=Q(
                    language__in=[ProgrammingLanguages.C, ProgrammingLanguages.CPP],
                    type=Question.Types.ADVANCED,
                ),
            ),
            basic_haskell=Count(
                "id", filter=Q(language=ProgrammingLanguages.HASKELL, type=Question.Types.BASIC)
            ),
            advanced_haskell=Count(
                "id", filter=Q(language=ProgrammingLanguages.HASKELL, type=Question.Types.ADVANCED)
            ),
            basic_prolog=Count(
                "id", filter=Q(language=ProgrammingLanguages.PROLOG, type=Question.Types.BASIC)
            ),
            advanced_prolog=Count(
                "id", filter=Q(language=ProgrammingLanguages.PROLOG, type=Question.Types.ADVANCED)
            ),
        )

        system_settings = SystemSetting.get_solo()
        context = super().get_context_data(**kwargs)
        context["questions"] = user_questions
        context["current_tab"] = "assistentstudent_list"
        context["info"] = {
            "min_basic_cpp_questions": system_settings.min_basic_cpp_questions,
            "min_advanced_cpp_questions": system_settings.min_advanced_cpp_questions,
            "min_basic_haskell_questions": system_settings.min_basic_haskell_questions,
            "min_advanced_haskell_questions": system_settings.min_advanced_haskell_questions,
            "min_basic_prolog_questions": system_settings.min_basic_prolog_questions,
            "min_advanced_prolog_questions": system_settings.min_advanced_prolog_questions,
            "cpp_deadline": system_settings.cpp_deadline,
            "haskell_deadline": system_settings.haskell_deadline,
            "prolog_deadline": system_settings.prolog_deadline,
            "basic_cpp_questions_count": counts["basic_c_cpp"],
            "advanced_cpp_questions_count": counts["advanced_c_cpp"],
            "basic_haskell_questions_count": counts["basic_haskell"],
            "advanced_haskell_questions_count": counts["advanced_haskell"],
            "basic_prolog_questions_count": counts["basic_prolog"],
            "advanced_prolog_questions_count": counts["advanced_prolog"],
        }
        return context


def render_updated_tags_table(request):
    """Função auxiliar para renderizar a tabela de tags atualizada após operações de criação, edição, exclusão ou restauração."""
    return render(
        request, "questions/partials/tag/tags_table_list.html", {"tags": Tag.objects.all()}
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
def tag_create(request):
    """View para criar uma nova tag. Utiliza HTMX para atualizar a tabela de tags sem recarregar a página."""
    form = TagForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        return htmx_modal_response(
            request, render_updated_tags_table, "#tag-table-body", "#modalTagForm", "#modalTagList"
        )

    return render(
        request,
        "questions/partials/tag/tag_form_inner.html",
        {"tag": None, "tag_form": form, "action": "create"},
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
def tag_edit(request, tag_id):
    """View para editar uma tag existente. Utiliza HTMX para atualizar a tabela de tags sem recarregar a página."""
    tag = get_object_or_404(Tag, id=tag_id)
    form = TagForm(request.POST or None, instance=tag)

    if request.method == "POST" and form.is_valid():
        form.save()
        return htmx_modal_response(
            request, render_updated_tags_table, "#tag-table-body", "#modalTagForm", "#modalTagList"
        )

    return render(
        request,
        "questions/partials/tag/tag_form_inner.html",
        {"tag": tag, "tag_form": form, "action": "edit"},
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
def tag_delete(request, tag_id):
    """View para excluir uma tag existente. Utiliza HTMX para atualizar a tabela de tags sem recarregar a página."""
    tag = get_object_or_404(Tag, id=tag_id)

    if request.method == "POST":
        tag.delete()
        return htmx_modal_response(
            request,
            render_updated_tags_table,
            "#tag-table-body",
            "#modalTagDelete",
            "#modalTagList",
        )

    return render(request, "questions/partials/tag/tag_delete_inner.html", {"tag": tag})


@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def tag_restore(request, tag_id):
    """View para restaurar uma tag excluída. Utiliza HTMX para atualizar a tabela de tags sem recarregar a página."""
    latest_history = Tag.history.filter(id=tag_id).latest()
    restored_tag = latest_history.instance
    restored_tag.id = tag_id
    restored_tag.save()

    return htmx_modal_response(
        request, render_updated_tags_table, "#tag-table-body", "#modalTagHistory", "#modalTagList"
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
@require_GET
def tag_history(request, tag_id):
    """View para exibir o histórico de alterações de uma tag específica. Utiliza HTMX para exibir o histórico em um modal."""
    tag = get_object_or_404(Tag, id=tag_id)
    days = get_days_from_request(request)

    tag_history_qs = (
        tag.history.days_ago(days).select_related("history_user").order_by("-history_date")
    )
    history_records = get_history_with_diff(tag, tag_history_qs)

    return render(
        request,
        "questions/partials/tag/tag_history.html",
        {"tag": tag, "history_records": history_records, "selected_days": days},
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
@require_GET
def tag_deleted_history(request):
    """View para exibir o histórico de tags excluídas. Utiliza HTMX para exibir o histórico em um modal."""
    days = get_days_from_request(request)

    deleted_qs = (
        Tag.history.days_ago(days)
        .filter(history_type="-")
        .select_related("history_user")
        .order_by("-history_date")
    )

    return render(
        request,
        "questions/partials/tag/tags_deleted_list.html",
        {"records": deleted_qs, "selected_days": days},
    )


class QuestionListView(LoginRequiredMixin, ListView):
    """View para listar todas as questões disponíveis, com suporte a filtros e paginação. Exibe informações adicionais para usuários staff, como histórico de alterações."""

    model = Question
    template_name = "questions/questions.html"
    context_object_name = "questions"
    paginate_by = 6

    def get_queryset(self):
        self.filterset = QuestionFilter(
            self.request.GET, queryset=Question.objects.all().order_by("-created_at")
        )
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter"] = self.filterset
        context["current_tab"] = "question_list"
        return context


class QuestionDetailView(LoginRequiredMixin, DetailView):
    """View para exibir os detalhes de uma questão específica, incluindo seus testes públicos e privados. Exibe informações adicionais para usuários staff, como histórico de alterações e atividades em andamento relacionadas à questão."""

    model = Question
    template_name = "questions/question.html"
    context_object_name = "question"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        if self.kwargs.get("slug") != self.object.slug:
            return redirect("questions:question_detail", pk=self.object.pk, slug=self.object.slug)

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["public_tests"] = self.object.tests.filter(type=Test.TestType.PUBLIC)
        context["private_tests"] = self.object.tests.filter(type=Test.TestType.PRIVATE)
        context["current_tab"] = "assistentstudent_list"

        # Verifica se há execuções de código em andamento para o usuário logado
        active_activity = CodeActivity.objects.filter(
            user=self.request.user, status__in=[TaskStatus.PENDING, TaskStatus.RUNNING]
        ).first()
        context["active_activity_id"] = str(active_activity.id) if active_activity else None

        history_qs = (
            self.object.history.days_ago(get_default_days())
            .select_related("history_user")
            .order_by("-history_date")
        )
        context["history_records"] = (
            get_history_with_diff(self.object, history_qs) if self.request.user.is_staff else None
        )
        context["selected_days"] = get_default_days()

        return context


@login_required
def question_create(request):
    """View para criar uma nova questão. Permite que o usuário preencha um formulário com os detalhes da questão e adicione testes associados. Após a criação, redireciona para a lista de questões do assistente de aluno."""
    question = Question()
    if request.method == "POST":
        form = QuestionForm(request.POST, instance=question)
        formset = TestFormSet(request.POST, instance=question)
        if form.is_valid() and formset.is_valid():
            question.author = request.user
            question.period = SystemSetting.get_solo().active_period
            saved_question = form.save()
            formset.instance = saved_question
            formset.save()
            messages.success(request, "Questão criada com sucesso!")
            return redirect("questions:assistentstudent_list")
    else:
        form = QuestionForm(instance=question)
        formset = TestFormSet(instance=question)

    return render(
        request,
        "questions/question_form.html",
        {
            "form": form,
            "formset": formset,
            "max_tests": Question.MAX_TESTS_COUNT,
            "formset_helper": TestFormSetHelper(),
        },
    )


@login_required
def question_edit(request, question_id):
    """View para editar uma questão existente. Permite que o usuário modifique os detalhes da questão e seus testes associados. Verifica se o usuário tem permissão para editar a questão (autor ou staff) antes de permitir as alterações. Após a edição, redireciona para a lista de questões do assistente de aluno."""
    question = get_object_or_404(Question, id=question_id)
    formset_helper = TestFormSetHelper()

    if not (request.user == question.author or request.user.is_staff):
        messages.warning(request, "Você não tem permissão para modificar essa questão!")
        return redirect("questions:assistentstudent_list")

    if request.method == "POST":
        form = QuestionForm(request.POST, instance=question)
        formset = TestFormSet(request.POST, instance=question)

        if form.is_valid() and formset.is_valid():
            saved_question = form.save(commit=False)

            # Gerar um resumo das mudanças para o campo change_reason, incluindo se a questão foi alterada e quantos testes foram criados, atualizados ou deletados
            synthetic_changes = {}
            if form.has_changed():
                synthetic_changes["question_changed"] = True
            if formset.has_changed():
                deleted_count = len(formset.deleted_forms)
                updated_count = sum(
                    1
                    for f in formset.initial_forms
                    if f.has_changed() and f not in formset.deleted_forms
                )
                created_count = sum(
                    1
                    for f in formset.extra_forms
                    if f.has_changed() and f not in formset.deleted_forms
                )
                synthetic_changes["tests"] = {
                    "created": created_count,
                    "updated": updated_count,
                    "deleted": deleted_count,
                }
            if synthetic_changes:
                saved_question._change_reason = json.dumps(synthetic_changes)

            saved_question.save()
            form.save_m2m()

            formset.instance = saved_question
            formset.save()

            messages.success(request, "Questão atualizada com sucesso!")
            return redirect("questions:assistentstudent_list")

        messages.error(request, "Erro ao atualizar questão. Verifique os campos abaixo.")
    else:
        form = QuestionForm(instance=question)
        formset = TestFormSet(instance=question)

    return render(
        request,
        "questions/question_form.html",
        {
            "form": form,
            "formset": formset,
            "max_tests": Question.MAX_TESTS_COUNT,
            "formset_helper": formset_helper,
        },
    )


@login_required
@require_POST
def question_delete(request, question_id):
    """View para excluir uma questão existente. Verifica se o usuário tem permissão para excluir a questão (autor ou staff) antes de permitir a exclusão. Após a exclusão, redireciona para a lista de questões do assistente de aluno. Utiliza HTMX para retornar a lista atualizada de questões sem recarregar a página."""
    question = get_object_or_404(Question, id=question_id)

    if not (request.user == question.author or request.user.is_staff):
        messages.warning(request, "Você não tem permissão para remover essa questão!")
        return redirect("questions:assistentstudent_list")

    question.delete()

    active_period = SystemSetting.get_solo().active_period
    questions = Question.objects.filter(author=request.user, period=active_period).order_by(
        "-created_at"
    )

    return render(
        request,
        "questions/partials/assistentstudent_questions_list.html",
        context={"questions": questions},
    )


@login_required
def question_history(request, question_id):
    """View para exibir o histórico de alterações de uma questão específica. Verifica se o usuário tem permissão para acessar o histórico (staff) antes de exibir as informações. Permite filtrar o histórico por um número específico de dias. Exibe as diferenças entre as versões da questão, incluindo mudanças nos campos da questão e nos testes associados. Utiliza HTMX para exibir o histórico em um modal sem recarregar a página."""
    if not request.user.is_staff:
        messages.warning(request, "Você não tem autorização para acessar essa funcionalidade!")
        return redirect("questions:question_list")

    question = get_object_or_404(Question, id=question_id)
    days = get_days_from_request(request)

    history_qs = (
        question.history.days_ago(days).select_related("history_user").order_by("-history_date")
    )
    history_records = get_history_with_diff(question, history_qs)

    return render(
        request,
        "questions/question_history.html",
        {"question": question, "history_records": history_records, "selected_days": days},
    )


@login_required
@require_POST
def question_feedback(request, question_id):
    """
    View para enviar feedback sobre uma questão específica.
    """
    if not request.user.is_staff:
        messages.warning(request, "Você não tem autorização para acessar essa funcionalidade!")
        return redirect("questions:question_list")

    question = get_object_or_404(Question, id=question_id)

    feedback_text = request.POST.get("feedback_text", "").strip()

    if not feedback_text:
        messages.error(request, "O texto do feedback não pode estar vazio!")
        return redirect("questions:question_list")

    try:
        autor = question.author

        subject = f"{settings.EMAIL_SUBJECT_PREFIX}Feedback sobre questão"
        message = (
            f"Olá, {autor.name or autor.email},\n\n"
            f"Sua questão '{question.title}' ({question.get_language_display()} / {question.get_type_display()}) recebeu um novo feedback:\n\n"
            f'"{feedback_text}"\n\n'
            f"Por favor, revise os pontos mencionados se necessário.\n\n"
            f"Atenciosamente,\n{request.user.name}."
        )
        recipient_list = [autor.email]

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False,
        )
        messages.success(request, "Feedback enviado para o autor da questão!")
    except Exception as e:
        logger.error(f"Erro ao enviar email: {e}")
        messages.error(request, "Erro ao enviar feedback por e-mail. Tente novamente mais tarde.")

    return redirect(
        "questions:question_detail",
        question_id=question.id,
        slug=question.slug,
    )
