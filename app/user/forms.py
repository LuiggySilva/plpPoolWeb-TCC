from django import forms

from questions.models import Question

from .models import AssistentStudent, Professor, SystemSetting


class ProfessorCreationForm(forms.ModelForm):
    class Meta:
        model = Professor
        fields = ("email", "registration", "name", "is_active")

    def save(self, commit=True):
        user = super().save(commit=False)
        if not user.password:
            user.set_password(user.registration)
        if commit:
            user.save()
        return user


class AssistentStudentCreationForm(forms.ModelForm):
    class Meta:
        model = AssistentStudent
        fields = ("email", "registration", "name", "github", "period", "is_active")

    def save(self, commit=True):
        user = super().save(commit=False)
        if not user.password:
            user.set_password(user.registration)
        if commit:
            user.save()
        return user


class BulkImportForm(forms.Form):
    json_file = forms.FileField(
        label="Arquivo JSON",
        required=False,
        help_text="Faça o upload de um arquivo .json contendo as questões.",
    )
    json_text = forms.CharField(
        label="Texto JSON",
        required=False,
        widget=forms.Textarea(attrs={"rows": 10, "class": "font-monospace"}),
        help_text="Ou cole o conteúdo JSON diretamente aqui.",
    )

    create_missing = forms.BooleanField(
        label="Criar tags e períodos inexistentes automaticamente",
        initial=False,
        required=False,
        help_text="Marque esta opção para criar automaticamente tags e períodos que não existam no banco de dados. Deixe desmarcado para relacionar apenas com tags e períodos já existentes, e ignorar os que não forem encontrados.",
    )

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("json_file") and not cleaned_data.get("json_text"):
            raise forms.ValidationError("Você deve fornecer um arquivo JSON ou colar o texto JSON.")
        return cleaned_data


class SystemSettingsForm(forms.ModelForm):
    class Meta:
        model = SystemSetting
        fields = [
            "active_period",
            "min_public_tests_in_questions",
            "min_private_tests_in_questions",
            "cpp_deadline",
            "min_basic_cpp_questions",
            "min_advanced_cpp_questions",
            "haskell_deadline",
            "min_basic_haskell_questions",
            "min_advanced_haskell_questions",
            "prolog_deadline",
            "min_basic_prolog_questions",
            "min_advanced_prolog_questions",
        ]

        labels = {
            "active_period": "Período Ativo",
            "min_public_tests_in_questions": "Testes Públicos",
            "min_private_tests_in_questions": "Testes Privados",
            "cpp_deadline": "Prazo Final",
            "haskell_deadline": "Prazo Final",
            "prolog_deadline": "Prazo Final",
            "min_basic_cpp_questions": "Mín. Básicas",
            "min_advanced_cpp_questions": "Mín. Avançadas",
            "min_basic_haskell_questions": "Mín. Básicas",
            "min_advanced_haskell_questions": "Mín. Avançadas",
            "min_basic_prolog_questions": "Mín. Básicas",
            "min_advanced_prolog_questions": "Mín. Avançadas",
        }

        help_texts = {
            "cpp_deadline": "Data e hora limite para criação de questões.",
            "haskell_deadline": "Data e hora limite para criação de questões.",
            "prolog_deadline": "Data e hora limite para criação de questões.",
        }

        widgets = {
            "min_public_tests_in_questions": forms.NumberInput(
                attrs={"placeholder": "Ex: 2", "class": "form-control shadow-sm"}
            ),
            "min_private_tests_in_questions": forms.NumberInput(
                attrs={"placeholder": "Ex: 5", "class": "form-control shadow-sm"}
            ),
            "active_period": forms.Select(attrs={"class": "form-select shadow-sm"}),
            "cpp_deadline": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"}, format="%Y-%m-%dT%H:%M"
            ),
            "haskell_deadline": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"}, format="%Y-%m-%dT%H:%M"
            ),
            "prolog_deadline": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"}, format="%Y-%m-%dT%H:%M"
            ),
        }

    def clean(self):
        cleaned_data = super().clean()

        if (
            cleaned_data.get("min_public_tests_in_questions") is not None
            and cleaned_data.get("min_private_tests_in_questions") is not None
        ):
            total_tests = (
                cleaned_data["min_public_tests_in_questions"]
                + cleaned_data["min_private_tests_in_questions"]
            )
            max_tests = Question.MAX_TESTS_COUNT

            if total_tests > max_tests:
                raise forms.ValidationError(
                    f"A soma dos testes públicos e privados deve ser de no máximo {max_tests}."
                )

        return super().clean()
