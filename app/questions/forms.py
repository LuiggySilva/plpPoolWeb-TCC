import django_filters
from crispy_bootstrap5.bootstrap5 import FloatingField
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Column, Div, Field, Layout, Row

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.forms import inlineformset_factory
from django.forms.models import BaseInlineFormSet

from user.models import SystemSetting

from .models import Period, ProgrammingLanguages, Question, Tag, Test
from .validators import sanitize_program_input, sanitize_source_code


class PeriodForm(forms.ModelForm):
    class Meta:
        model = Period
        fields = ["name"]


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ["name"]


class TestInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        settings = SystemSetting.get_solo()
        public_tests = 0
        private_tests = 0
        errors = []

        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get("DELETE", False):
                if form.cleaned_data.get("type") == Test.TestType.PUBLIC:
                    public_tests += 1
                else:
                    private_tests += 1

        min_public_tests = settings.min_public_tests_in_questions
        min_private_tests = settings.min_private_tests_in_questions
        if public_tests < min_public_tests:
            errors.append(f"É necessário no mínimo {min_public_tests} teste(s) público(s).")
        if private_tests < min_private_tests:
            errors.append(f"É necessário no mínimo {min_private_tests} teste(s) privado(s).")

        if errors:
            raise ValidationError(errors)


LANGUAGE_FILTER_CHOICES = [
    ("c_family", "C / C++"),
    *[(value, label) for value, label in ProgrammingLanguages.choices if value not in ("c", "cpp")],
]


class QuestionFilter(django_filters.FilterSet):
    title = django_filters.CharFilter(
        label="Enunciado",
        lookup_expr="icontains",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Buscar por enunciado"}
        ),
    )

    tags = django_filters.ModelMultipleChoiceFilter(
        label="Tags",
        queryset=Tag.objects.all(),
        method="filter_tags_with_all",
        to_field_name="slug",
        widget=forms.SelectMultiple(
            # attrs={"class": "form-select", "data-placeholder": "Selecione as tags"}
        ),
    )

    period = django_filters.ModelChoiceFilter(
        label="Período",
        queryset=Period.objects.all(),
        to_field_name="name",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    type = django_filters.ChoiceFilter(
        label="Tipo",
        choices=Question.Types.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    language = django_filters.ChoiceFilter(
        label="Linguagem",
        choices=LANGUAGE_FILTER_CHOICES,
        method="filter_language",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def filter_language(self, queryset, name, value):
        if value == "c_family":
            return queryset.filter(language__in=["c", "cpp"])
        return queryset.filter(language=value)

    class Meta:
        model = Question
        fields = ["title", "tags", "period", "language", "type"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form.helper = FormHelper()
        self.form.helper.form_method = "get"
        self.form.helper.form_tag = False
        self.form.helper.layout = Layout(
            Row(Column(FloatingField("title", css_class="col-12"))),
            Row(Column("tags", css_class="col-12 fs-5")),
            Row(Column("period", css_class="col-12")),
            Row(Column("language", css_class="col-12")),
            Row(Column("type", css_class="col-12")),
            HTML(
                '<button type="submit" class="btn btn-primary w-100"><i class="bi bi-funnel"></i>&nbsp;Filtrar</button>'
            ),
        )

    def filter_tags_with_all(self, queryset, name, value):
        tag_slugs = [tag.slug for tag in value if tag.slug]
        if tag_slugs:
            return queryset.annotate(
                matched_tags=Count("tags", filter=Q(tags__slug__in=tag_slugs), distinct=True)
            ).filter(matched_tags=len(tag_slugs))
        return queryset


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = "__all__"
        exclude = ["slug", "author", "period"]
        widgets = {
            "code": forms.Textarea(attrs={"rows": 10, "class": "font-monospace", "wrap": "off"}),
            "description": forms.Textarea(attrs={"rows": 10, "wrap": "off"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.form_show_errors = True
        self.helper.error_text_inline = True
        self.helper.layout = Layout(
            Div(
                Div(
                    FloatingField("title"),
                    Row(
                        Column(FloatingField("language"), css_class="form-group col-md-6 mb-0"),
                        Column(FloatingField("type"), css_class="form-group col-md-6 mb-0"),
                        css_class="form-row",
                    ),
                    Field("tags", css_class="tom-select"),
                    Field("description"),
                    Field("code"),
                    css_class="card-body",
                ),
                css_class="card mb-4 shadow-sm",
            )
        )

    def clean_tags(self):
        tags = self.cleaned_data.get("tags")
        if tags and len(tags) > Question.MAX_TAGS_COUNT:
            raise forms.ValidationError(f"Selecione no máximo {Question.MAX_TAGS_COUNT} tag(s).")
        if tags and len(tags) <= Question.MIN_TAGS_COUNT:
            raise forms.ValidationError(f"Selecione no mínimo {Question.MIN_TAGS_COUNT} tag(s).")
        return tags

    def clean(self):
        cleaned_data = super().clean()

        code = cleaned_data.get("code")
        language = cleaned_data.get("language")

        if code and language:
            cleaned_data["code"] = sanitize_source_code(code, language)

        return cleaned_data


class TestForm(forms.ModelForm):
    class Meta:
        model = Test
        fields = ["type", "input_data", "output_data"]
        widgets = {
            "input_data": forms.Textarea(attrs={"rows": 6, "class": "font-monospace"}),
            "output_data": forms.Textarea(attrs={"rows": 6, "class": "font-monospace"}),
        }

    def clean_input_data(self):
        input_data = self.cleaned_data.get("input_data")
        return sanitize_program_input(input_data)


class TestFormSetHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_tag = False
        self.disable_csrf = True
        self.error_text_inline = True
        self.render_required_fields = True
        self.render_hidden_fields = True
        self.layout = Layout(
            Div(
                Div(
                    Row(
                        Column(FloatingField("type"), css_class="col-md-8"),
                        Column(
                            Field("DELETE", css_class="form-check-input"),
                            css_class="col-md-4 d-flex align-items-center justify-content-end text-danger fw-bold",
                        ),
                    ),
                    Row(
                        Column(Field("input_data"), css_class="col-md-6"),
                        Column(Field("output_data"), css_class="col-md-6"),
                    ),
                    css_class="card-body",
                ),
                css_class="card mb-3 border-secondary test-form-row shadow-sm",
            )
        )


class BaseTestInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        public_count = 0
        private_count = 0

        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue
            test_type = form.cleaned_data.get("type")
            if test_type == "public":
                public_count += 1
            elif test_type == "private":
                private_count += 1

        setting = SystemSetting.get_solo()
        min_public = setting.min_public_tests_in_questions
        min_private = setting.min_private_tests_in_questions
        erros = []

        if public_count < min_public:
            erros.append(
                f"A questão precisa de no mínimo {min_public} teste(s) público(s). Você enviou {public_count}."
            )
        if private_count < min_private:
            erros.append(
                f"A questão precisa de no mínimo {min_private} teste(s) privado(s). Você enviou {private_count}."
            )
        if erros:
            raise ValidationError(erros)

        max_tests = Question.MAX_TESTS_COUNT
        total_forms = sum(
            1
            for form in self.forms
            if not form.cleaned_data.get("DELETE", False) and form.cleaned_data
        )

        if total_forms > max_tests:
            raise ValidationError(
                f"Foram adicionados mais testes ({total_forms}) do que o permitido ({max_tests})."
            )


TestFormSet = inlineformset_factory(
    Question,
    Test,
    form=TestForm,
    formset=BaseTestInlineFormSet,
    extra=0,
    can_delete=True,
    max_num=Question.MAX_TESTS_COUNT,
)
