import json

from django.test import RequestFactory, TestCase
from django.utils.safestring import SafeString

from questions.models import Period, Tag
from questions.utils import (
    get_code_highlighted,
    get_days_from_request,
    get_default_days,
    get_field_labels,
    get_history_with_diff,
    htmx_modal_response,
    resolve_fk_value,
    resolve_m2m_value,
)
from user.models import AssistentStudent, CustomUser


class QuestionUtilsTests(TestCase):
    def setUp(self):
        self.request_factory = RequestFactory()
        self.period = Period.objects.create(name="2024.1")
        user = CustomUser.objects.create_user(
            email="student@example.com",
            password="password",
            name="Aluno Teste",
            registration="123456789",
            period=self.period,
            role=AssistentStudent.Role.ASSISTENT_STUDENT,
        )
        self.user = AssistentStudent.objects.get(pk=user.pk)

    def test_get_code_highlighted_returns_safe_html_for_known_language(self):
        safe_html = get_code_highlighted("cpp", "int main() { return 0; }")

        self.assertIsInstance(safe_html, SafeString)
        self.assertIn("return", str(safe_html))
        self.assertIn("<div", str(safe_html))

    def test_get_code_highlighted_uses_fallback_for_unknown_language(self):
        safe_html = get_code_highlighted("python", "print('hi')")

        self.assertIsInstance(safe_html, SafeString)
        self.assertIn("print", str(safe_html))
        self.assertIn("<div", str(safe_html))

    def test_get_default_days(self):
        self.assertEqual(get_default_days(), 30)

    def test_get_days_from_request_valid_and_invalid_values(self):
        request = self.request_factory.get("/")
        self.assertEqual(get_days_from_request(request), 30)

        request = self.request_factory.get("/", {"days": "60"})
        self.assertEqual(get_days_from_request(request), 60)

        request = self.request_factory.get("/", {"days": "45"})
        self.assertEqual(get_days_from_request(request), 30)

        request = self.request_factory.get("/", {"days": "invalid"})
        self.assertEqual(get_days_from_request(request), 30)

    def test_get_field_labels_contains_question_and_systemsetting_fields(self):
        field_labels = get_field_labels()

        self.assertEqual(field_labels["title"], "Enunciado")
        self.assertEqual(field_labels["active_period"], "Período ativo")
        self.assertEqual(field_labels["tags"], "Tags")
        self.assertEqual(field_labels["tag"], "Tag")

    def test_resolve_fk_value_returns_display_for_known_fk(self):
        self.assertEqual(resolve_fk_value("author", None), "—")
        self.assertEqual(resolve_fk_value("author", 9999), 9999)
        self.assertEqual(resolve_fk_value("author", self.user.pk), str(self.user))

    def test_resolve_m2m_value_returns_tag_names_from_list(self):
        tag1 = Tag.objects.create(name="Python")
        tag2 = Tag.objects.create(name="Django")

        value = [{"pk": tag1.pk, "tag": tag1.pk}, {"pk": tag2.pk, "tag": tag2.pk}]
        self.assertEqual(resolve_m2m_value("tags", value), "Python, Django")
        self.assertEqual(resolve_m2m_value("tags", None), "—")
        self.assertEqual(resolve_m2m_value("tags", []), "—")
        self.assertEqual(resolve_m2m_value("unknown", "foo"), "foo")

    def test_get_history_with_diff_reads_changes_and_tests_summary(self):
        tag = Tag.objects.create(name="Original")
        tag.name = "Modified"
        tag.save()

        history_qs = list(tag.history.all())
        history_qs[0].history_change_reason = json.dumps(
            {"tests": {"created": 1, "updated": 2, "deleted": 3}}
        )
        records = get_history_with_diff(tag, history_qs)

        self.assertEqual(len(records), 2)
        first = records[0]

        self.assertTrue(
            any(
                change["field"] == "name"
                and change["old"].startswith("Original")
                and change["new"].startswith("Modified")
                for change in first.changes_list
            )
        )
        self.assertTrue(
            any(
                change["field"] == "Casos de teste"
                and change["old"] == "3 removido(s)"
                and change["new"] == "1 criado(s), 2 atualizado(s)"
                for change in first.changes_list
            )
        )

    def test_htmx_modal_response_adds_hx_trigger_header(self):
        response = htmx_modal_response(
            None,
            lambda request: {"success": True},
            target="#modal-target",
            modal_id="modal-1",
            modal_list_id="list-1",
        )

        self.assertEqual(response["success"], True)
        self.assertIn("HX-Trigger", response)

        trigger = json.loads(response["HX-Trigger"])
        self.assertEqual(trigger["closeModal"]["target"], "#modal-target")
        self.assertEqual(trigger["closeModal"]["modal"], "modal-1")
        self.assertEqual(trigger["closeModal"]["listModal"], "list-1")
