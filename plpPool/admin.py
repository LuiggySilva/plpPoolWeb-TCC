from django.contrib import admin
from django_admin_multiple_choice_list_filter.list_filters import MultipleChoiceListFilter
from .models import (
    User, 
    Monitor,
    Professor,
    Tag,
    Questao,
    Linguagem,
    Periodo,
    Atividade,
    Teste
)
from .forms import QuestaoForm, PeriodoForm


class TesteInline(admin.StackedInline):
    model = Teste
    extra = 0


@admin.register(Linguagem)
class LinguagemAdmin(admin.ModelAdmin):
    list_display = ('nome', 'extensao', 'compilador')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    exclude = ('questao',)

class TagInline(admin.TabularInline):
    model = Tag
    extra = 1

class TagsListFilter(MultipleChoiceListFilter):
    title = 'Tag'
    parameter_name = 'tags__nome'

    def lookups(self, request, model_admin):
        return Tag.objects.values_list('pk', 'nome')

    def queryset(self, request, queryset):
        if request.GET.get(self.parameter_name):
            kwargs = {
                self.parameter_name: request.GET[self.parameter_name].split(',')
            }
            pks = [int(n) for n in request.GET[self.parameter_name].split(',')]
            for tag_pk in pks:
                queryset = queryset.filter(tags__pk=tag_pk)
        return queryset.distinct()


@admin.register(Monitor)
class MonitorAdmin(admin.ModelAdmin):
    search_fields = ('username', 'email', 'matricula')
    fieldsets = (
        ('Dados', {'fields': ('username', 'email', 'matricula', 'is_active')}),
    )
    list_display = ('username', 'email', 'matricula', 'is_active')
    exclude = (
        'password',
        'last_login',
        'is_superuser',
        'groups',
        'user_permissions',
        'first_name',
        'last_name',
        'is_staff', 
        'slug'
    )


@admin.register(Professor)
class ProfessorAdmin(admin.ModelAdmin):
    search_fields = ('username', 'email')
    fieldsets = (
        ('Dados', {'fields': ('username', 'email')}),
    )
    list_display = ('username', 'email')
    exclude = (
        'last_login',
        'is_superuser',
        'groups',
        'user_permissions',
        'first_name',
        'last_name',
        'is_staff', 
        'slug'
    )


class PeriodoListFilter(MultipleChoiceListFilter):
    title = 'Periodo'
    parameter_name = 'periodo__nome'

    def lookups(self, request, model_admin):
        return Periodo.objects.values_list('pk', 'nome')

    def queryset(self, request, queryset):
        if request.GET.get(self.parameter_name):
            kwargs = {
                self.parameter_name: request.GET[self.parameter_name].split(',')
            }
            pks = [int(n) for n in request.GET[self.parameter_name].split(',')]
            for periodo_pk in pks:
                queryset = queryset.filter(periodo__pk=periodo_pk)
        return queryset.distinct()


@admin.register(Questao)
class QuestaoAdmin(admin.ModelAdmin):
    search_fields = ('enunciado', 'autor__email', 'autor__username')
    fieldsets = (
        ('Dados', {
            'fields': 
                (
                    'enunciado', 
                    'descricao', 
                    'codigo',
                    'tags',
                    'tipo',
                    'linguagem',
                    'autor',
                    'periodo'
                )
            }
        ),
    )
    filter_horizontal = ['tags', ]
    inlines = (TesteInline,)
    list_display = ('enunciado', 'autor', 'linguagem', 'tipo', 'periodo')
    list_filter = (TagsListFilter, 'tipo', 'linguagem', 'periodo__nome')
    actions = ['delete_selected']

    def delete_selected(self, request, obj):
        for o in obj.all():
            o.delete()
    delete_selected.short_description = 'Remover questões selecionadas'

@admin.register(Atividade)
class AtividadeAdmin(admin.ModelAdmin):
    search_fields = ('assunto',)
    fieldsets = (
        ('Dados', {
            'fields': ( 
                'data', 
                'descricao', 
                'qtd_basicas', 
                'qtd_avancadas', 
                'linguagem',
                'periodo'
            )
        }),
    )
    list_display = ('data', 'periodo')

class AtividadeInline(admin.StackedInline):
    model = Atividade
    extra = 0


@admin.register(Periodo)
class PeriodoAdmin(admin.ModelAdmin):
    search_fields = ('nome',)
    fieldsets = (
        ('Dados', {'fields': ('nome', 'ativo')}),
        ('Monitores', {'fields': ('monitores',)}),
    )

    filter_horizontal = ['monitores',]
    inlines = (AtividadeInline,)
    list_display = ('nome', 'ativo')
    ordering = ['-ativo', '-nome']
    form = PeriodoForm
