# admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import AssistentStudent, Professor, CustomUser


@admin.register(AssistentStudent)
class AssistentStudentAdmin(BaseUserAdmin):
    ordering = ['email']
    list_display = ['email', 'name', 'period', 'registration']
    list_filter = ['is_active']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Informações pessoais'), {'fields': ('name', 'role', 'github', 'period', 'registration')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('name', 'registration', 'email', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )

    search_fields = ['email', 'name', 'registration']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(role='monitor')


@admin.register(Professor)
class ProfessorAdmin(BaseUserAdmin):
    ordering = ['email']
    list_display = ['email', 'name', 'period', 'registration',]
    list_filter = ['is_active']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Informações pessoais'), {'fields': ('name', 'role', 'period', 'registration')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('name', 'registration', 'email', 'password1', 'password2', 'is_active')}
        ),
    )

    search_fields = ['email', 'name', 'registration']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(role='professor')
