from django.contrib.auth import get_user_model
from django.test import TestCase

from questions.models import Period
from user.models import AssistentStudent, CustomUser, Professor, SystemSetting


class CustomUserModelTests(TestCase):
    def setUp(self):
        self.period = Period.objects.create(name="2025.0")

    def test_str_returns_email(self):
        user = get_user_model().objects.create_user(
            email="user@example.com",
            password="pass123",
            name="User Test",
            period=self.period,
        )

        self.assertEqual(str(user), "user@example.com")

    def test_assistentstudent_save_assigns_role_and_group(self):
        monitor = AssistentStudent.objects.create(
            email="monitor@example.com",
            name="Monitor Test",
            registration="123456789",
            period=self.period,
        )
        monitor.refresh_from_db()

        self.assertEqual(monitor.role, CustomUser.Role.ASSISTENT_STUDENT)
        self.assertTrue(monitor.groups.filter(name="Monitores").exists())

    def test_professor_save_assigns_role_staff_and_group(self):
        professor = Professor.objects.create(
            email="professor@example.com",
            name="Professor Test",
            registration="987654321",
            period=self.period,
        )
        professor.refresh_from_db()

        self.assertEqual(professor.role, CustomUser.Role.PROFESSOR)
        self.assertTrue(professor.is_staff)
        self.assertTrue(professor.groups.filter(name="Professores").exists())

    def test_assistentstudent_manager_filters_only_monitors(self):
        AssistentStudent.objects.create(
            email="monitor1@example.com",
            name="Monitor One",
            registration="123456780",
            period=self.period,
        )
        Professor.objects.create(
            email="professor1@example.com",
            name="Professor One",
            registration="123456781",
            period=self.period,
        )

        self.assertEqual(AssistentStudent.objects.count(), 1)

    def test_professor_manager_filters_only_professors(self):
        AssistentStudent.objects.create(
            email="monitor2@example.com",
            name="Monitor Two",
            registration="123456782",
            period=self.period,
        )
        Professor.objects.create(
            email="professor2@example.com",
            name="Professor Two",
            registration="123456783",
            period=self.period,
        )

        self.assertEqual(Professor.objects.count(), 1)


class AssistentStudentLegacyTests(TestCase):
    def test_get_or_create_legacy_creates_monitor_when_not_exists(self):
        monitor = AssistentStudent.get_or_create_legacy(
            name="Legacy Monitor",
            github_url="https://github.com/legacy-monitor",
        )

        self.assertEqual(monitor.name, "Legacy Monitor")
        self.assertEqual(monitor.github, "https://github.com/legacy-monitor")
        self.assertFalse(monitor.is_active)
        self.assertEqual(monitor.role, CustomUser.Role.ASSISTENT_STUDENT)
        self.assertTrue(monitor.email.startswith("legacy."))
        self.assertTrue(monitor.registration.startswith("0000"))
        self.assertTrue(monitor.groups.filter(name="Monitores").exists())

    def test_get_or_create_legacy_returns_existing_monitor_for_same_github(self):
        first_monitor = AssistentStudent.get_or_create_legacy(
            name="Legacy Monitor",
            github_url="https://github.com/legacy-same",
        )
        second_monitor = AssistentStudent.get_or_create_legacy(
            name="Different Name",
            github_url="https://github.com/legacy-same",
        )

        self.assertEqual(first_monitor.pk, second_monitor.pk)
        self.assertEqual(
            AssistentStudent.objects.filter(github="https://github.com/legacy-same").count(),
            1,
        )


class SystemSettingTests(TestCase):
    def test_system_setting_singleton_str_and_get_solo(self):
        setting = SystemSetting.get_solo()

        self.assertEqual(str(setting), "Configurações")
        self.assertEqual(setting, SystemSetting.get_solo())

    def test_system_setting_defaults_are_present(self):
        setting = SystemSetting.get_solo()

        self.assertGreaterEqual(setting.min_public_tests_in_questions, 1)
        self.assertGreaterEqual(setting.min_private_tests_in_questions, 5)
        self.assertIsNotNone(setting.cpp_deadline)
        self.assertIsNotNone(setting.haskell_deadline)
        self.assertIsNotNone(setting.prolog_deadline)
