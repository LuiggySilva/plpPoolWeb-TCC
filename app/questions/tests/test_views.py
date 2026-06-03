from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from questions.models import (
    Period,
    ProgrammingLanguages,
    Question,
    Tag,
    Test,
)
from user.models import AssistentStudent, CustomUser, SystemSetting


class AssistentStudentQuestionListViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.period = Period.objects.create(name="2040.0")
        self.assistent = AssistentStudent.objects.create(
            email="student@example.com",
            name="Aluno Teste",
            registration="123456780",
            period=self.period,
        )
        self.setting = SystemSetting.get_solo()
        self.setting.active_period = self.period
        self.setting.save()

    def test_assistentstudent_question_list_renders_for_logged_in_user(self):
        self.client.force_login(self.assistent)

        question = Question.objects.create(
            title="Teste",
            code="int main() { return 0; }",
            description="Exemplo",
            author=self.assistent,
            period=self.period,
            language=ProgrammingLanguages.C,
            type=Question.Types.BASIC,
        )

        response = self.client.get(reverse("questions:assistentstudent_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Teste")
        self.assertEqual(response.context["current_tab"], "assistentstudent_list")
        self.assertIn(question, response.context["questions"])

    def test_assistentstudent_question_list_redirects_when_not_logged_in(self):
        response = self.client.get(reverse("questions:assistentstudent_list"))

        self.assertNotEqual(response.status_code, 200)
        self.assertIn(response.status_code, (302, 301))


class TagViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = CustomUser.objects.create_superuser(
            email="staff@example.com",
            password="password",
        )
        self.client.force_login(self.staff_user)

    def test_tag_create_posts_and_returns_hx_trigger(self):
        response = self.client.post(reverse("questions:tag_create"), {"name": "Nova Tag"})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Tag.objects.filter(name="Nova Tag").exists())
        self.assertIn("HX-Trigger", response)

    def test_tag_edit_posts_and_updates_name(self):
        tag = Tag.objects.create(name="Tag Original")

        response = self.client.post(
            reverse("questions:tag_edit", args=[tag.id]), {"name": "Tag Editada"}
        )

        self.assertEqual(response.status_code, 200)
        tag.refresh_from_db()
        self.assertEqual(tag.name, "Tag Editada")
        self.assertIn("HX-Trigger", response)

    def test_tag_delete_posts_and_removes_tag(self):
        tag = Tag.objects.create(name="Tag Para Deletar")

        response = self.client.post(reverse("questions:tag_delete", args=[tag.id]))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Tag.objects.filter(pk=tag.pk).exists())
        self.assertIn("HX-Trigger", response)

    def test_tag_restore_posts_restores_deleted_tag(self):
        tag = Tag.objects.create(name="Tag Restaurar")
        tag_id = tag.id
        tag.delete()

        response = self.client.post(reverse("questions:tag_restore", args=[tag_id]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Tag.objects.filter(pk=tag_id).exists())
        self.assertIn("HX-Trigger", response)

    def test_tag_history_returns_history_records(self):
        tag = Tag.objects.create(name="Tag Historico")
        tag.name = "Tag Historico Editada"
        tag.save()

        response = self.client.get(reverse("questions:tag_history", args=[tag.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_days"], 30)
        self.assertIsNotNone(response.context["history_records"])

    def test_tag_deleted_history_returns_deleted_records(self):
        self.client.force_login(self.staff_user)

        tag = Tag.objects.create(name="Tag Excluida")
        self.client.post(reverse("questions:tag_delete", args=[tag.id]))

        response = self.client.get(reverse("questions:tag_deleted_history"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("records", response.context)


class QuestionViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.period = Period.objects.create(name="2040.1")
        self.author = AssistentStudent.objects.create(
            email="author@example.com",
            name="Author",
            registration="111222333",
            period=self.period,
        )
        self.staff_user = CustomUser.objects.create_superuser(
            email="staff2@example.com",
            password="password",
        )
        self.question = Question.objects.create(
            title="Questão de Teste",
            code="int main() { return 0; }",
            description="Texto de exemplo",
            author=self.author,
            period=self.period,
            language=ProgrammingLanguages.C,
            type=Question.Types.BASIC,
        )
        Test.objects.create(
            question=self.question,
            input_data="1",
            output_data="1",
            type=Test.TestType.PUBLIC,
        )
        Test.objects.create(
            question=self.question,
            input_data="2",
            output_data="2",
            type=Test.TestType.PRIVATE,
        )

    def test_question_list_view_returns_status_code(self):
        self.client.force_login(self.author)
        response = self.client.get(reverse("questions:question_list"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("current_tab", response.context)
        self.assertEqual(response.context["current_tab"], "question_list")

    def test_question_detail_view_shows_public_and_private_tests(self):
        self.client.force_login(self.author)

        response = self.client.get(
            reverse("questions:question_detail", args=[self.question.id, self.question.slug])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context["public_tests"]),
            list(self.question.tests.filter(type=Test.TestType.PUBLIC)),
        )
        self.assertEqual(
            list(response.context["private_tests"]),
            list(self.question.tests.filter(type=Test.TestType.PRIVATE)),
        )
        self.assertEqual(response.context["current_tab"], "assistentstudent_list")

    def test_question_history_requires_staff_and_returns_records(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("questions:question_history", args=[self.question.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_days"], 30)
        self.assertIsNotNone(response.context["history_records"])

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="from@example.com",
    )
    def test_question_feedback_sends_email_and_redirects(self):
        self.client.force_login(self.staff_user)

        response = self.client.post(
            reverse("questions:question_feedback", args=[self.question.id]),
            {"feedback_text": "Ótimo trabalho!"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.author.email, mail.outbox[0].to)
        self.assertIn("Ótimo trabalho", mail.outbox[0].body)


class QuestionListViewFilterTests(TestCase):
    """Tests for filtering functionality in QuestionListView"""

    def setUp(self):
        self.client = Client()
        self.period1 = Period.objects.create(name="2024.1")
        self.period2 = Period.objects.create(name="2024.2")

        self.author = AssistentStudent.objects.create(
            email="author@example.com",
            name="Author",
            registration="111222333",
            period=self.period1,
        )

        self.tag_algoritmos = Tag.objects.create(name="algoritmos")
        self.tag_estruturas = Tag.objects.create(name="estruturas")
        self.tag_sorting = Tag.objects.create(name="sorting")

        # Create questions with different characteristics
        self.q1 = Question.objects.create(
            title="Ordenação com Bubble Sort",
            description="Implementar bubble sort",
            code="void bubble_sort(int arr[]) {}",
            language=ProgrammingLanguages.C,
            type=Question.Types.BASIC,
            author=self.author,
            period=self.period1,
        )
        self.q1.tags.set([self.tag_algoritmos, self.tag_sorting])

        self.q2 = Question.objects.create(
            title="Lista Ligada em C++",
            description="Implementar lista ligada",
            code="template<typename T> class LinkedList {}",
            language=ProgrammingLanguages.CPP,
            type=Question.Types.ADVANCED,
            author=self.author,
            period=self.period1,
        )
        self.q2.tags.set([self.tag_estruturas])

        self.q3 = Question.objects.create(
            title="Busca Binária",
            description="Implementar busca binária",
            code="binary_search(List, Element) :- true.",
            language=ProgrammingLanguages.PROLOG,
            type=Question.Types.BASIC,
            author=self.author,
            period=self.period2,
        )
        self.q3.tags.set([self.tag_algoritmos])

    def test_question_list_view_without_filters(self):
        """Test that QuestionListView shows all questions without filters"""
        self.client.force_login(self.author)
        response = self.client.get(reverse("questions:question_list"))

        self.assertEqual(response.status_code, 200)
        questions = response.context["questions"]
        self.assertIn(self.q1, questions)
        self.assertIn(self.q2, questions)
        self.assertIn(self.q3, questions)

    def test_question_list_view_filter_by_title(self):
        """Test filtering questions by title"""
        self.client.force_login(self.author)
        response = self.client.get(reverse("questions:question_list"), {"title": "ordenação"})

        self.assertEqual(response.status_code, 200)
        questions = response.context["questions"]
        self.assertIn(self.q1, questions)
        self.assertNotIn(self.q2, questions)
        self.assertNotIn(self.q3, questions)

    def test_question_list_view_filter_by_title_partial_match(self):
        """Test filtering by partial title match"""
        self.client.force_login(self.author)
        response = self.client.get(reverse("questions:question_list"), {"title": "lista"})

        self.assertEqual(response.status_code, 200)
        questions = response.context["questions"]
        self.assertNotIn(self.q1, questions)
        self.assertIn(self.q2, questions)
        self.assertNotIn(self.q3, questions)

    def test_question_list_view_filter_by_single_tag(self):
        """Test filtering questions by a single tag"""
        self.client.force_login(self.author)
        response = self.client.get(
            reverse("questions:question_list"), {"tags": self.tag_sorting.slug}
        )

        self.assertEqual(response.status_code, 200)
        questions = response.context["questions"]
        self.assertIn(self.q1, questions)
        self.assertNotIn(self.q2, questions)
        self.assertNotIn(self.q3, questions)

    def test_question_list_view_filter_by_multiple_tags(self):
        """Test filtering by multiple tags - questions must have ALL tags"""
        self.client.force_login(self.author)
        response = self.client.get(
            reverse("questions:question_list"),
            {"tags": [self.tag_algoritmos.slug, self.tag_sorting.slug]},
        )

        self.assertEqual(response.status_code, 200)
        questions = response.context["questions"]
        self.assertIn(self.q1, questions)
        self.assertNotIn(self.q2, questions)
        self.assertNotIn(self.q3, questions)

    def test_question_list_view_filter_by_period(self):
        """Test filtering questions by period"""
        self.client.force_login(self.author)
        response = self.client.get(
            reverse("questions:question_list"), {"period": self.period1.name}
        )

        self.assertEqual(response.status_code, 200)
        questions = response.context["questions"]
        self.assertIn(self.q1, questions)
        self.assertIn(self.q2, questions)
        self.assertNotIn(self.q3, questions)

    def test_question_list_view_filter_by_type_basic(self):
        """Test filtering by question type BASIC"""
        self.client.force_login(self.author)
        response = self.client.get(
            reverse("questions:question_list"), {"type": Question.Types.BASIC}
        )

        self.assertEqual(response.status_code, 200)
        questions = response.context["questions"]
        self.assertIn(self.q1, questions)
        self.assertNotIn(self.q2, questions)
        self.assertIn(self.q3, questions)

    def test_question_list_view_filter_by_type_advanced(self):
        """Test filtering by question type ADVANCED"""
        self.client.force_login(self.author)
        response = self.client.get(
            reverse("questions:question_list"), {"type": Question.Types.ADVANCED}
        )

        self.assertEqual(response.status_code, 200)
        questions = response.context["questions"]
        self.assertNotIn(self.q1, questions)
        self.assertIn(self.q2, questions)
        self.assertNotIn(self.q3, questions)

    def test_question_list_view_filter_by_language_c_family(self):
        """Test filtering by C family languages (C and C++)"""
        self.client.force_login(self.author)
        response = self.client.get(reverse("questions:question_list"), {"language": "c_family"})

        self.assertEqual(response.status_code, 200)
        questions = response.context["questions"]
        self.assertIn(self.q1, questions)
        self.assertIn(self.q2, questions)
        self.assertNotIn(self.q3, questions)

    def test_question_list_view_combined_filters_title_and_period(self):
        """Test combining title and period filters"""
        self.client.force_login(self.author)
        response = self.client.get(
            reverse("questions:question_list"),
            {"title": "Busca", "period": self.period2.name},
        )

        self.assertEqual(response.status_code, 200)
        questions = response.context["questions"]
        self.assertNotIn(self.q1, questions)
        self.assertNotIn(self.q2, questions)
        self.assertIn(self.q3, questions)

    def test_question_list_view_combined_filters_tag_and_type(self):
        """Test combining tag and type filters"""
        self.client.force_login(self.author)
        response = self.client.get(
            reverse("questions:question_list"),
            {"tags": self.tag_algoritmos.slug, "type": Question.Types.ADVANCED},
        )

        self.assertEqual(response.status_code, 200)
        questions = response.context["questions"]
        self.assertNotIn(self.q1, questions)
        self.assertNotIn(self.q2, questions)
        self.assertNotIn(self.q3, questions)

    def test_question_list_view_combined_filters_language_and_type(self):
        """Test combining language and type filters"""
        self.client.force_login(self.author)
        response = self.client.get(
            reverse("questions:question_list"),
            {"language": "c_family", "type": Question.Types.BASIC},
        )

        self.assertEqual(response.status_code, 200)
        questions = response.context["questions"]
        self.assertIn(self.q1, questions)
        self.assertNotIn(self.q2, questions)
        self.assertNotIn(self.q3, questions)

    def test_question_list_view_no_results_match(self):
        """Test that filter returns empty list when no matches"""
        self.client.force_login(self.author)
        response = self.client.get(
            reverse("questions:question_list"), {"title": "NonexistentQuestion"}
        )

        self.assertEqual(response.status_code, 200)
        questions = response.context["questions"]
        self.assertEqual(list(questions), [])

    def test_question_list_view_has_filter_object_in_context(self):
        """Test that filter object is available in context"""
        self.client.force_login(self.author)
        response = self.client.get(reverse("questions:question_list"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("filter", response.context)
        self.assertIsNotNone(response.context["filter"])

    def test_question_list_view_requires_login(self):
        """Test that QuestionListView requires authentication"""
        response = self.client.get(reverse("questions:question_list"))

        self.assertIn(response.status_code, (302, 301))
        self.assertIn("/login", response.url)
