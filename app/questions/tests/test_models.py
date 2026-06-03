from django.test import TestCase
from django.utils.text import slugify

from questions.models import Period, ProgrammingLanguages, Question, Tag, Test
from user.models import AssistentStudent


class PeriodModelTests(TestCase):
    def test_period_str(self):
        period = Period.objects.create(name="2040.0")
        self.assertEqual(str(period), "2040.0")


class TagModelTests(TestCase):
    def test_tag_slug_generated_on_save(self):
        tag = Tag.objects.create(name="My Special Tag")
        self.assertEqual(tag.slug, slugify("My Special Tag"))


class QuestionModelTests(TestCase):
    def setUp(self):
        self.period = Period.objects.create(name="2040.0")
        self.author = AssistentStudent.objects.create(
            email="author@example.com",
            name="Author",
            registration="111222333",
            period=self.period,
        )

    def test_question_save_creates_slug_and_normalizes_code(self):
        title = "This is a Title!"
        raw_code = "  line1\r\nline2\r\n  "
        q = Question.objects.create(
            title=title,
            code=raw_code,
            description="descr",
            author=self.author,
            period=self.period,
            language=ProgrammingLanguages.CPP,
            type=Question.Types.ADVANCED,
        )

        # slug set from title
        self.assertEqual(q.slug, slugify(title[:150]))

        # code normalized (CRLF -> LF and stripped)
        self.assertEqual(q.code, "line1\nline2")

        # language_devicon mapping for cpp -> cplusplus
        self.assertEqual(q.language_devicon, "cplusplus")

        # get_absolute_url contains id and slug
        url = q.get_absolute_url()
        self.assertIn(str(q.pk), url)
        self.assertIn(q.slug, url)


class TestModelTests(TestCase):
    def setUp(self):
        self.period = Period.objects.create(name="2040.0")
        self.author = AssistentStudent.objects.create(
            email="author@example.com",
            name="Author",
            registration="111222333",
            period=self.period,
        )

    def test_test_normalize_text_and_str(self):
        q = Question.objects.create(
            title="T1",
            code="int main() {\r\n}",
            description="desc",
            author=self.author,
            period=self.period,
            language=ProgrammingLanguages.C,
            type=Question.Types.BASIC,
        )
        t = Test.objects.create(
            question=q, input_data="a\r\nb\r\n", output_data="ok\r\n", type=Test.TestType.PUBLIC
        )
        self.assertEqual(t.input_data, "a\nb")
        self.assertEqual(t.output_data, "ok")
        # __str__ returns pk
        self.assertEqual(str(t), str(t.pk))
