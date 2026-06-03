from simple_history.admin import SimpleHistoryAdmin
from solo.admin import SingletonModelAdmin

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.shortcuts import redirect
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from questions.models import Question

from .forms import AssistentStudentCreationForm, ProfessorCreationForm, SystemSettingsForm
from .models import AssistentStudent, CustomUser, Professor, SystemSetting


class PermissionsDisplayMixin:
    def get_effective_permissions_table(self, obj):
        if not obj.pk:
            return "-"

        perms = sorted(obj.get_all_permissions())
        if not perms:
            return format_html(
                '<span style="color: #999;">{}</span>', _("Nenhuma permissão atribuída.")
            )

        grouped = {}
        for p in perms:
            app, code = p.split(".")
            grouped.setdefault(app, []).append(code)

        rows = []
        for app, codes in grouped.items():
            badges = "".join(
                [
                    f'<span style="display: inline-block; background: #f0f0f0; color: #444; '
                    f"padding: 2px 10px; border-radius: 12px; margin: 2px; font-size: 11px; "
                    f'font-weight: 500; border: 1px solid #ddd; white-space: nowrap;">{c}</span>'
                    for c in codes
                ]
            )

            rows.append(
                f'<tr style="border-bottom: 1px solid #eee;">'
                f'<td style="padding: 10px; font-weight: bold; color: #555; vertical-align: top; width: 120px; border-right: 1px solid #eee;">{app.upper()}</td>'
                f'<td style="padding: 10px;">{badges}</td></tr>'
            )

        return format_html(
            '<div style="border: 1px solid #ccc; border-radius: 4px; overflow: hidden;">'
            '<table style="width:100%; border-collapse: collapse; background: white; margin: 0;">'
            '<thead style="background: #f8f9fa; border-bottom: 2px solid #dee2e6;">'
            '<tr><th style="padding: 10px; text-align: left;">App</th>'
            '<th style="padding: 10px; text-align: left;">Permissões Efetivas</th></tr></thead>'
            "<tbody>{}</tbody></table></div>",
            format_html("".join(rows)),
        )

    get_effective_permissions_table.short_description = _("Visualização de Permissões")


@admin.register(SystemSetting)
class SystemSettingAdmin(SimpleHistoryAdmin, SingletonModelAdmin):
    fieldsets = (
        (
            None,
            {
                "fields": (),
                "description": mark_safe(
                    "<h3>• Se os valores máximo e mínimo de questões não forem definidos (ou seja, permanecerem iguais a zero), o sistema não enviará notificações de prazo por e-mail aos monitores.</h3>"
                    "<h3>• Um e-mail será enviado relembrando os prazos definidos para os monitores uma semana antes e um dia antes do prazo final.</h3>"
                ),
            },
        ),
        (
            "Período",
            {
                "fields": ("active_period",),
                "description": mark_safe(
                    "<b>Atenção:</b><br>"
                    "• O acesso dos <i>professores</i> deve ser <b>removido manualmente</b>.<br>"
                    "• Quando um período estiver definido, <b>somente os monitores vinculados a ele</b> poderão acessar o sistema.<br>"
                    "• Se o campo for deixado em branco, <b>nenhum monitor</b> terá acesso ao sistema."
                ),
            },
        ),
        (
            "Questões",
            {
                "fields": ("min_public_tests_in_questions", "min_private_tests_in_questions"),
                "description": mark_safe(
                    "• Defina a quantidade mínima de testes públicos e privados obrigatórios para cada questão.<br>"
                    f"• A soma dos testes públicos e privados deve ser de no máximo {Question.MAX_TESTS_COUNT}, para garantir desempenho, estabilidade e tempo adequado de execução das submissões.<br>"
                ),
            },
        ),
        (
            "Linguagem: C/C++",
            {
                "fields": ("cpp_deadline", "min_basic_cpp_questions", "min_advanced_cpp_questions"),
            },
        ),
        (
            "Linguagem: Haskell",
            {
                "fields": (
                    "haskell_deadline",
                    "min_basic_haskell_questions",
                    "min_advanced_haskell_questions",
                ),
            },
        ),
        (
            "Linguagem: Prolog",
            {
                "fields": (
                    "prolog_deadline",
                    "min_basic_prolog_questions",
                    "min_advanced_prolog_questions",
                ),
            },
        ),
    )

    form = SystemSettingsForm

    def save_model(self, request, obj, form, change):
        obj.last_modified_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(CustomUser)
class CustomUserAdmin(PermissionsDisplayMixin, BaseUserAdmin):
    can_add = False
    can_delete = False

    fieldsets = (
        (None, {"fields": ("email", "groups", "is_active", "reset_password_button")}),
        (_("Informações pessoais"), {"fields": ("name", "registration")}),
        (
            _("Permissões"),
            {
                "fields": (
                    "is_superuser",
                    "is_staff",
                    "role",
                    "last_login",
                    "get_effective_permissions_table",
                )
            },
        ),
    )

    list_display = ["email", "name", "is_active"]
    ordering = ["email"]
    search_fields = ["email", "name"]
    readonly_fields = [
        "groups",
        "role",
        "is_superuser",
        "is_staff",
        "reset_password_button",
        "last_login",
        "get_effective_permissions_table",
    ]

    def reset_password_button(self, obj):
        if obj and obj.pk:
            return mark_safe(
                '<a class="button" href="?reset_password=1" '
                "onclick=\"return confirm('Tem certeza que deseja redefinir a senha para a matrícula?')\">"
                "Resetar senha para matrícula</a>"
            )
        return ""

    reset_password_button.short_description = "Redefinir senha"

    def change_view(self, request, object_id, form_url="", extra_context=None):
        if request.GET.get("reset_password") == "1":
            user = self.get_object(request, object_id)
            user.set_password(user.registration)
            user.save()
            messages.success(request, f"A senha de {user.email} foi redefinida para a matrícula.")
            return redirect(request.path)
        return super().change_view(request, object_id, form_url, extra_context)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(is_superuser=True)


class AccessAllowedFilter(admin.SimpleListFilter):
    title = "Permissão de Login"
    parameter_name = "login_permission"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Sim"),
            ("no", "Não"),
        )

    def queryset(self, request, queryset):
        active_period = SystemSetting.get_solo().active_period
        if active_period is None:
            return queryset.all()
        if self.value() == "yes":
            return queryset.filter(is_active=True, period=active_period)
        if self.value() == "no":
            return queryset.exclude(is_active=True, period=active_period)
        return queryset


@admin.register(AssistentStudent)
class AssistentStudentAdmin(SimpleHistoryAdmin, PermissionsDisplayMixin, BaseUserAdmin):
    add_form = AssistentStudentCreationForm
    ordering = ["email"]
    list_display = [
        "email",
        "name",
        "period",
        "registration",
        "is_active",
        "is_staff",
        "is_superuser",
    ]
    list_filter = [AccessAllowedFilter]

    fieldsets = (
        (None, {"fields": ("email", "groups", "reset_password_button")}),
        (_("Informações pessoais"), {"fields": ("name", "github", "period", "registration")}),
        (
            _("Permissões"),
            {
                "fields": (
                    "is_active",
                    "is_superuser",
                    "is_staff",
                    "role",
                    "last_login",
                    "get_effective_permissions_table",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("name", "registration", "github", "period", "email", "is_active"),
                "description": mark_safe(
                    "<h4>Um email será enviado para o usuário informando sobre a criação da conta e indicando que a senha inicial é a sua matrícula.</h4>"
                ),
            },
        ),
    )

    readonly_fields = [
        "groups",
        "role",
        "is_superuser",
        "is_staff",
        "reset_password_button",
        "last_login",
        "get_effective_permissions_table",
    ]
    search_fields = ["email", "name", "registration"]

    def reset_password_button(self, obj):
        if obj and obj.pk:
            return mark_safe(
                '<a class="button" href="?reset_password=1" '
                "onclick=\"return confirm('Tem certeza que deseja redefinir a senha para a matrícula?')\">"
                "Resetar senha para matrícula</a>"
            )
        return ""

    reset_password_button.short_description = "Redefinir senha"

    def change_view(self, request, object_id, form_url="", extra_context=None):
        if request.GET.get("reset_password") == "1":
            user = self.get_object(request, object_id)
            user.set_password(user.registration)
            user.save()
            messages.success(request, f"A senha de {user.email} foi redefinida para a matrícula.")
            return redirect(request.path)
        return super().change_view(request, object_id, form_url, extra_context)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.set_password(obj.registration)
        obj.save()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(role="monitor")


@admin.register(Professor)
class ProfessorAdmin(SimpleHistoryAdmin, PermissionsDisplayMixin, BaseUserAdmin):
    add_form = ProfessorCreationForm
    ordering = ["email"]
    list_display = ["email", "name", "registration", "is_active", "is_staff", "is_superuser"]
    list_filter = ["is_active"]

    fieldsets = (
        (None, {"fields": ("email", "groups", "reset_password_button")}),
        (_("Informações pessoais"), {"fields": ("name", "registration")}),
        (
            _("Permissões"),
            {
                "fields": (
                    "is_active",
                    "is_superuser",
                    "is_staff",
                    "role",
                    "last_login",
                    "get_effective_permissions_table",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("name", "registration", "email"),
                "description": mark_safe(
                    "<h4>Um email será enviado para o usuário informando sobre a criação da conta e indicando que a senha inicial é a sua matrícula.</h4>"
                ),
            },
        ),
    )

    readonly_fields = [
        "groups",
        "role",
        "is_superuser",
        "is_staff",
        "reset_password_button",
        "last_login",
        "get_effective_permissions_table",
    ]
    search_fields = ["email", "name", "registration"]

    def reset_password_button(self, obj):
        if obj and obj.pk:
            return mark_safe(
                '<a class="button" href="?reset_password=1" '
                "onclick=\"return confirm('Tem certeza que deseja redefinir a senha para a matrícula?')\">"
                "Resetar senha para matrícula</a>"
            )
        return ""

    reset_password_button.short_description = "Redefinir senha"

    def change_view(self, request, object_id, form_url="", extra_context=None):
        if request.GET.get("reset_password") == "1":
            user = self.get_object(request, object_id)
            user.set_password(user.registration)
            user.save()
            messages.success(request, f"A senha de {user.email} foi redefinida para a matrícula.")
            return redirect(request.path)
        return super().change_view(request, object_id, form_url, extra_context)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.set_password(obj.registration)
        obj.save()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(role="professor")
