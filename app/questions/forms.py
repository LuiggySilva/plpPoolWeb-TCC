from django import forms
from django.forms.models import BaseInlineFormSet
from django.core.exceptions import ValidationError
from django.db.models import Count, Q


import django_filters
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, HTML
from crispy_bootstrap5.bootstrap5 import FloatingField

from user.models import SystemSetting
from .models import Test, Question, Tag, Period



class TestInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        settings = SystemSetting.get_solo()
        public_tests = 0
        private_tests = 0
        errors = []

        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                if form.cleaned_data.get('type') == Test.TestType.PUBLIC:
                    public_tests += 1
                else:
                    private_tests += 1

        min_public_tests = settings.min_public_tests_in_questions
        min_private_tests = settings.min_private_tests_in_questions
        if public_tests < min_public_tests:
            errors.append(
                f"É necessário no mínimo {min_public_tests} teste(s) público(s)."
            )
        if private_tests < min_private_tests:
            errors.append(
                f"É necessário no mínimo {min_private_tests} teste(s) privado(s)."
            )

        if errors:
            raise ValidationError(errors)
        

class QuestionFilter(django_filters.FilterSet):
    title = django_filters.CharFilter(
        label="Título",
        lookup_expr='icontains',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Buscar por título'})
    )

    tags = django_filters.ModelMultipleChoiceFilter(
        label="Tags",
        queryset=Tag.objects.all(),
        method='filter_tags_with_all',
        to_field_name='slug',
        widget=forms.CheckboxSelectMultiple
    )

    period = django_filters.ModelChoiceFilter(
        label="Período",
        queryset=Period.objects.all(),
        to_field_name='name',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    language = django_filters.ChoiceFilter(
        label="Linguagem",
        choices=Question.Languages.choices,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    type = django_filters.ChoiceFilter(
        label="Tipo",
        choices=Question.Types.choices,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Question
        fields = ['title', 'tags', 'period', 'language', 'type']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form.helper = FormHelper()
        self.form.helper.form_method = 'get'
        self.form.helper.layout = Layout(
            Row(Column(FloatingField('title', css_class='col-12'))),
            Row(Column('tags', css_class='col-12 fs-5')),
            Row(Column('period', css_class='col-12')),
            Row(Column('language', css_class='col-12')),
            Row(Column('type', css_class='col-12')),
            HTML('<button type="submit" class="btn btn-primary w-100"><i class="bi bi-funnel"></i>&nbsp;Filtrar</button>'),
        )

    def filter_tags_with_all(self, queryset, name, value):
        tag_slugs = [tag.slug for tag in value if tag.slug]
        if tag_slugs:
            return queryset.annotate(
                matched_tags=Count('tags', filter=Q(tags__slug__in=tag_slugs), distinct=True)
            ).filter(matched_tags=len(tag_slugs))
        return queryset
