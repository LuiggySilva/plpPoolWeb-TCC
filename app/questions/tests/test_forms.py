from django.http import QueryDict
from django.test import TestCase

from questions.forms import PeriodForm, QuestionFilter, QuestionForm, TagForm, TestForm
from questions.models import Period, ProgrammingLanguages, Question, Tag
from user.models import AssistentStudent


class PeriodTagFormTests(TestCase):
    def test_period_form_valid_and_invalid(self):
        form = PeriodForm(data={"name": "2025.1"})
        self.assertTrue(form.is_valid())

        form = PeriodForm(data={"name": "badformat"})
        self.assertFalse(form.is_valid())

    def test_tag_form_creates_name(self):
        form = TagForm(data={"name": "New Tag"})
        self.assertTrue(form.is_valid())
        tag = form.save()
        self.assertEqual(tag.name, "New Tag")


class QuestionAndTestFormTests(TestCase):
    def setUp(self):
        self.period = Period.objects.create(name="2040.0")
        self.author = AssistentStudent.objects.create(
            email="author@example.com",
            name="Author",
            registration="111222333",
            period=self.period,
        )
        self.tag = Tag.objects.create(name="algoritmos")
        self.tag2 = Tag.objects.create(name="estruturas")

    def test_test_form_input_sanitization(self):
        form = TestForm(data={"type": "public", "input_data": "a\r\nb", "output_data": "ok"})

        self.assertTrue(form.is_valid())
        cleaned = form.cleaned_data
        self.assertEqual(cleaned["input_data"], "a\r\nb")

    def test_question_form_empty_code_invalid(self):
        data = {
            "title": "Q1",
            "code": "",
            "description": "desc",
            "language": ProgrammingLanguages.C,
            "type": Question.Types.BASIC,
            "tags": [self.tag.id, self.tag2.id],
        }
        form = QuestionForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("code", form.errors)

    def test_question_form_forbidden_code_invalid(self):
        data = {
            "title": "Q2",
            "code": 'system("ls");',
            "description": "desc",
            "language": ProgrammingLanguages.C,
            "type": Question.Types.BASIC,
            "tags": [self.tag.id, self.tag2.id],
        }
        form = QuestionForm(data=data)
        self.assertFalse(form.is_valid())
        # sanitize_source_code raises a ValidationError attached to __all__ in clean
        self.assertIn("__all__", form.errors)

    def test_question_form_null_char_stripped(self):
        data = {
            "title": "Q3",
            "code": "a\x00b",
            "description": "desc",
            "language": ProgrammingLanguages.C,
            "type": Question.Types.BASIC,
            "tags": [self.tag.id, self.tag2.id],
        }
        form = QuestionForm(data=data)
        # current behavior: null characters are rejected
        self.assertFalse(form.is_valid())
        self.assertIn("code", form.errors)
        self.assertTrue(
            any("nulo" in str(e).lower() or "null" in str(e).lower() for e in form.errors["code"])
        )


class QuestionFilterTests(TestCase):
    def setUp(self):
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

        # Create questions for testing
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

    def test_filter_by_title(self):
        """Test filtering questions by title (case-insensitive contains)"""
        data = QueryDict(mutable=True)
        data["title"] = "ordenação"
        filter_form = QuestionFilter(data, queryset=Question.objects.all())
        qs = filter_form.qs
        self.assertIn(self.q1, qs)
        self.assertNotIn(self.q2, qs)
        self.assertNotIn(self.q3, qs)

    def test_filter_by_title_partial(self):
        """Test filtering by partial title"""
        data = QueryDict(mutable=True)
        data["title"] = "lista"
        filter_form = QuestionFilter(data, queryset=Question.objects.all())
        qs = filter_form.qs
        self.assertNotIn(self.q1, qs)
        self.assertIn(self.q2, qs)
        self.assertNotIn(self.q3, qs)

    def test_filter_by_single_tag(self):
        """Test filtering by a single tag"""
        data = QueryDict(mutable=True)
        data.setlist("tags", [self.tag_sorting.slug])
        filter_form = QuestionFilter(data, queryset=Question.objects.all())
        qs = filter_form.qs
        self.assertIn(self.q1, qs)
        self.assertNotIn(self.q2, qs)
        self.assertNotIn(self.q3, qs)

    def test_filter_by_multiple_tags_all_required(self):
        """Test filtering by multiple tags - questions must have ALL tags"""
        # Only q1 has both algoritmos and sorting
        data = QueryDict(mutable=True)
        data.setlist("tags", [self.tag_algoritmos.slug, self.tag_sorting.slug])
        filter_form = QuestionFilter(data, queryset=Question.objects.all())
        qs = filter_form.qs
        self.assertIn(self.q1, qs)
        self.assertNotIn(self.q2, qs)
        self.assertNotIn(self.q3, qs)

    def test_filter_by_multiple_tags_not_all_present(self):
        """Test that questions without all specified tags are excluded"""
        # q3 only has algoritmos, not estruturas
        data = QueryDict(mutable=True)
        data.setlist("tags", [self.tag_algoritmos.slug, self.tag_estruturas.slug])
        filter_form = QuestionFilter(data, queryset=Question.objects.all())
        qs = filter_form.qs
        self.assertNotIn(self.q1, qs)
        self.assertNotIn(self.q2, qs)
        self.assertNotIn(self.q3, qs)

    def test_filter_by_period(self):
        """Test filtering by period"""
        data = QueryDict(mutable=True)
        data["period"] = self.period1.name
        filter_form = QuestionFilter(data, queryset=Question.objects.all())
        qs = filter_form.qs
        self.assertIn(self.q1, qs)
        self.assertIn(self.q2, qs)
        self.assertNotIn(self.q3, qs)

    def test_filter_by_type_basic(self):
        """Test filtering by question type (BASIC)"""
        data = QueryDict(mutable=True)
        data["type"] = Question.Types.BASIC
        filter_form = QuestionFilter(data, queryset=Question.objects.all())
        qs = filter_form.qs
        self.assertIn(self.q1, qs)
        self.assertNotIn(self.q2, qs)
        self.assertIn(self.q3, qs)

    def test_filter_by_type_advanced(self):
        """Test filtering by question type (ADVANCED)"""
        data = QueryDict(mutable=True)
        data["type"] = Question.Types.ADVANCED
        filter_form = QuestionFilter(data, queryset=Question.objects.all())
        qs = filter_form.qs
        self.assertNotIn(self.q1, qs)
        self.assertIn(self.q2, qs)
        self.assertNotIn(self.q3, qs)

    def test_filter_by_language_c_family(self):
        """Test filtering by language C family (C and C++)"""
        data = QueryDict(mutable=True)
        data["language"] = "c_family"
        filter_form = QuestionFilter(data, queryset=Question.objects.all())
        qs = filter_form.qs
        self.assertIn(self.q1, qs)
        self.assertIn(self.q2, qs)
        self.assertNotIn(self.q3, qs)

    def test_filter_combined_title_and_period(self):
        """Test combining title and period filters"""
        data = QueryDict(mutable=True)
        data["title"] = "Busca"
        data["period"] = str(self.period2.id)
        filter_form = QuestionFilter(data, queryset=Question.objects.all())
        qs = filter_form.qs
        self.assertNotIn(self.q1, qs)
        self.assertNotIn(self.q2, qs)
        self.assertIn(self.q3, qs)

    def test_filter_combined_tag_and_type(self):
        """Test combining tag and type filters"""
        data = QueryDict(mutable=True)
        data.setlist("tags", [self.tag_algoritmos.slug])
        data["type"] = Question.Types.ADVANCED
        filter_form = QuestionFilter(data, queryset=Question.objects.all())
        qs = filter_form.qs
        self.assertNotIn(self.q1, qs)
        self.assertNotIn(self.q2, qs)
        self.assertNotIn(self.q3, qs)

    def test_filter_combined_language_and_type(self):
        """Test combining language and type filters"""
        data = QueryDict(mutable=True)
        data["language"] = "c_family"
        data["type"] = Question.Types.BASIC
        filter_form = QuestionFilter(data, queryset=Question.objects.all())
        qs = filter_form.qs
        self.assertIn(self.q1, qs)
        self.assertNotIn(self.q2, qs)
        self.assertNotIn(self.q3, qs)

    def test_filter_empty_queryset_no_matches(self):
        """Test that filters return empty queryset when no matches"""
        data = QueryDict(mutable=True)
        data["title"] = "NonexistentQuestion"
        filter_form = QuestionFilter(data, queryset=Question.objects.all())
        qs = filter_form.qs
        self.assertEqual(qs.count(), 0)

    def test_filter_no_criteria_returns_all(self):
        """Test that no filter criteria returns all questions"""
        data = QueryDict(mutable=True)
        filter_form = QuestionFilter(data, queryset=Question.objects.all())
        qs = filter_form.qs
        self.assertEqual(qs.count(), 3)
        self.assertIn(self.q1, qs)
        self.assertIn(self.q2, qs)
        self.assertIn(self.q3, qs)
