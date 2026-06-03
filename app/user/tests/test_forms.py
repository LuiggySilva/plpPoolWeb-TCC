from django.contrib.auth import get_user_model
from django.test import TestCase

from questions.models import Period, Question
from user.forms import (
    AssistentStudentCreationForm,
    BulkImportForm,
    ProfessorCreationForm,
    SystemSettingsForm,
)
from user.models import AssistentStudent, SystemSetting


class UserCreationFormTests(TestCase):
    def setUp(self):
        self.period = Period.objects.create(name="2025.0")

    def test_professor_creation_form_sets_password_from_registration(self):
        form = ProfessorCreationForm(
            data={
                "email": "professor@example.com",
                "registration": "123456789",
                "name": "Professor Test",
                "is_active": True,
            }
        )

        self.assertTrue(form.is_valid())
        user = form.save()

        self.assertIsInstance(user, get_user_model())
        self.assertEqual(user.email, "professor@example.com")
        self.assertTrue(user.check_password("123456789"))
        self.assertEqual(user.role, get_user_model().Role.PROFESSOR)
        self.assertTrue(user.is_staff)

    def test_assistentstudent_creation_form_sets_password_from_registration(self):
        form = AssistentStudentCreationForm(
            data={
                "email": "monitor@example.com",
                "registration": "987654321",
                "name": "Monitor Test",
                "github": "https://github.com/monitor",
                "period": self.period.pk,
                "is_active": True,
            }
        )

        self.assertTrue(form.is_valid())
        user = form.save()

        self.assertIsInstance(user, AssistentStudent)
        self.assertEqual(user.email, "monitor@example.com")
        self.assertTrue(user.check_password("987654321"))
        self.assertEqual(user.role, get_user_model().Role.ASSISTENT_STUDENT)


class BulkImportFormTests(TestCase):
    def test_bulk_import_form_requires_file_or_text(self):
        form = BulkImportForm(data={})

        self.assertFalse(form.is_valid())
        self.assertIn(
            "Você deve fornecer um arquivo JSON ou colar o texto JSON.", form.non_field_errors()
        )

    def test_bulk_import_form_accepts_json_text(self):
        form = BulkImportForm(data={"json_text": "[]"})

        self.assertTrue(form.is_valid())


class SystemSettingsFormTests(TestCase):
    def test_system_settings_form_accepts_valid_test_counts(self):
        settings = SystemSetting.get_solo()
        data = {
            "active_period": settings.active_period.pk if settings.active_period else "",
            "min_public_tests_in_questions": 2,
            "min_private_tests_in_questions": 3,
            "cpp_deadline": settings.cpp_deadline.strftime("%Y-%m-%dT%H:%M"),
            "haskell_deadline": settings.haskell_deadline.strftime("%Y-%m-%dT%H:%M"),
            "prolog_deadline": settings.prolog_deadline.strftime("%Y-%m-%dT%H:%M"),
            "min_basic_cpp_questions": settings.min_basic_cpp_questions,
            "min_advanced_cpp_questions": settings.min_advanced_cpp_questions,
            "min_basic_haskell_questions": settings.min_basic_haskell_questions,
            "min_advanced_haskell_questions": settings.min_advanced_haskell_questions,
            "min_basic_prolog_questions": settings.min_basic_prolog_questions,
            "min_advanced_prolog_questions": settings.min_advanced_prolog_questions,
        }

        form = SystemSettingsForm(instance=settings, data=data)

        self.assertTrue(form.is_valid())

    def test_system_settings_form_rejects_test_count_sum_above_max(self):
        settings = SystemSetting.get_solo()
        max_tests = Question.MAX_TESTS_COUNT
        data = {
            "active_period": settings.active_period.pk if settings.active_period else "",
            "min_public_tests_in_questions": max_tests,
            "min_private_tests_in_questions": 1,
            "cpp_deadline": settings.cpp_deadline.strftime("%Y-%m-%dT%H:%M"),
            "haskell_deadline": settings.haskell_deadline.strftime("%Y-%m-%dT%H:%M"),
            "prolog_deadline": settings.prolog_deadline.strftime("%Y-%m-%dT%H:%M"),
            "min_basic_cpp_questions": settings.min_basic_cpp_questions,
            "min_advanced_cpp_questions": settings.min_advanced_cpp_questions,
            "min_basic_haskell_questions": settings.min_basic_haskell_questions,
            "min_advanced_haskell_questions": settings.min_advanced_haskell_questions,
            "min_basic_prolog_questions": settings.min_basic_prolog_questions,
            "min_advanced_prolog_questions": settings.min_advanced_prolog_questions,
        }

        form = SystemSettingsForm(instance=settings, data=data)

        self.assertFalse(form.is_valid())
        self.assertIn(
            f"A soma dos testes públicos e privados deve ser de no máximo {max_tests}.",
            form.non_field_errors(),
        )
