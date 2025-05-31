from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.shortcuts import render, redirect
from django.urls import path
from django.template.response import TemplateResponse

from solo.admin import SingletonModelAdmin

from .models import AssistentStudent, Professor, SystemSetting
from .forms import ProfessorCreationForm, AssistentStudentCreationForm


@admin.register(SystemSetting)
class SystemSettingAdmin(SingletonModelAdmin):
    fieldsets = (
        (None, {
            'fields': (),
            'description': format_html(
                '<h3>• Se o máximo e mínimo de questões não forem definidos (igual a zero), o sistema não enviará notificações de prazo via email para os monitores.<h3>'
                '<h3>• Um email será enviado relembrando os prazos definidos para os monitores uma semana antes e um dia antes do prazo final.</h3>'
            )
        }),
        ('Período', {
            'fields': ('active_period',),
            'description': format_html(
                "<b>Atenção:</b> o acesso dos <i>professores</i> deve ser <b>removido manualmente</b>.<br>"
                "• Quando um período estiver definido, <b>apenas monitores vinculados a ele</b> poderão acessar o sistema.<br>"
                "• Se deixado em branco, <b>nenhum monitor</b> terá acesso ao sistema."
            )
        }),
        ('C/C++', {
            'fields': ('cpp_deadline', 'max_basic_cpp_questions', 'max_advanced_cpp_questions'),
        }),
        ('Haskell', {
            'fields': ('haskell_deadline', 'max_basic_haskell_questions', 'max_advanced_haskell_questions'),
        }),
        ('Prolog', {
            'fields': ('prolog_deadline', 'max_basic_prolog_questions', 'max_advanced_prolog_questions'),
        }),
    )


class AccessAllowedFilter(admin.SimpleListFilter):
    title = 'Permissão de Login'
    parameter_name = 'login_permission'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Sim'),
            ('no', 'Não'),
        )

    def queryset(self, request, queryset):
        active_period = SystemSetting.get_solo().active_period
        if active_period is None:
            return queryset.all() 
        if self.value() == 'yes':
            return queryset.filter(is_active=True, period=active_period)
        if self.value() == 'no':
            return queryset.exclude(is_active=True, period=active_period)
        return queryset


@admin.register(AssistentStudent)
class AssistentStudentAdmin(BaseUserAdmin):
    add_form = AssistentStudentCreationForm
    ordering = ['email']
    list_display = ['email', 'name', 'period', 'registration', 'is_active']
    list_filter = [AccessAllowedFilter]

    fieldsets = (
        (None, {'fields': ('email', 'groups', 'is_active', 'reset_password_button')}),
        (_('Informações pessoais'), {'fields': ('name', 'github', 'period', 'registration')}),
        (_('Permissões'), {'fields': ('is_superuser', 'is_staff', 'role')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('name', 'registration', 'github', 'period', 'email', 'is_active'),
            'description': format_html(
                '<h4>Um email será enviado para o usuário informando sobre a criação da conta e indicando que a senha inicial é a sua matrícula.</h4>'
            )
        }
        ),
    )

    readonly_fields = ['groups', 'role', 'is_superuser', 'is_staff', 'is_active', 'reset_password_button']    
    search_fields = ['email', 'name', 'registration']

    def reset_password_button(self, obj):
        if obj and obj.pk:
            return format_html(
                '<a class="button" href="?reset_password=1" '
                'onclick="return confirm(\'Tem certeza que deseja redefinir a senha para a matrícula?\')">'
                'Resetar senha para matrícula</a>'
            )
        return ''
    reset_password_button.short_description = 'Redefinir senha'

    def change_view(self, request, object_id, form_url='', extra_context=None):
        if request.GET.get('reset_password') == '1':
            user = self.get_object(request, object_id)
            user.set_password(user.registration)
            user.save()
            messages.success(request, f'A senha de {user.email} foi redefinida para a matrícula.')
            return redirect(request.path)
        return super().change_view(request, object_id, form_url, extra_context)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.set_password(obj.registration)
        obj.save()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(role='monitor')
    



@admin.register(Professor)
class ProfessorAdmin(BaseUserAdmin):
    add_form = ProfessorCreationForm
    ordering = ['email']
    list_display = ['email', 'name', 'registration', 'is_active']
    list_filter = ['is_active']

    fieldsets = (
        (None, {'fields': ('email', 'groups', 'is_active', 'reset_password_button')}),
        (_('Informações pessoais'), {'fields': ('name', 'registration')}),
        (_('Permissões'), {'fields': ('is_superuser', 'is_staff', 'role')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('name', 'registration', 'email'),
            'description': format_html(
                '<h4>Um email será enviado para o usuário informando sobre a criação da conta e indicando que a senha inicial é a sua matrícula.</h4>'
            )  
        }
        ),
    )

    readonly_fields = ['groups', 'role', 'is_superuser', 'is_staff', 'reset_password_button'] 
    search_fields = ['email', 'name', 'registration']

    def reset_password_button(self, obj):
        if obj and obj.pk:
            return format_html(
                '<a class="button" href="?reset_password=1" '
                'onclick="return confirm(\'Tem certeza que deseja redefinir a senha para a matrícula?\')">'
                'Resetar senha para matrícula</a>'
            )
        return ''
    reset_password_button.short_description = 'Redefinir senha'

    def change_view(self, request, object_id, form_url='', extra_context=None):
        if request.GET.get('reset_password') == '1':
            user = self.get_object(request, object_id)
            user.set_password(user.registration)
            user.save()
            messages.success(request, f'A senha de {user.email} foi redefinida para a matrícula.')
            return redirect(request.path)
        return super().change_view(request, object_id, form_url, extra_context)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.set_password(obj.registration)
        obj.save()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(role='professor')
