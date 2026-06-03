from django.test import TestCase

from questions.models import Period, Question, Tag, Test
from user.models import AssistentStudent, SystemSetting
from user.utils import (
    FieldStatus,
    check_similarity,
    get_or_create_assistentstudent_group,
    get_or_create_professors_group,
    get_valid_random_registration,
    get_validation_sets,
    process_database_import,
    validate_import_item,
)


class UtilsTests(TestCase):
    def setUp(self):
        self.period = Period.objects.create(name="2026.0")

        settings = SystemSetting.get_solo()
        settings.min_private_tests_in_questions = 0
        settings.min_public_tests_in_questions = 0
        settings.save()

    def test_validate_import_item_missing_fields(self):
        valid_sets = get_validation_sets()
        item = {}

        errors, period_info, tags_info = validate_import_item(item, valid_sets)

        self.assertIn("Campo 'title' é obrigatório.", errors)
        self.assertIn("Campo 'description' é obrigatório.", errors)
        self.assertIn("Campo 'code' é obrigatório.", errors)
        self.assertIn("Campo 'author.name' é obrigatório.", errors)
        self.assertIn("Campo 'period' é obrigatório.", errors)

    def test_validate_import_item_create_missing_true_new_period_and_tags(self):
        valid_sets = get_validation_sets()
        valid_sets["tag_map"] = {}

        item = {
            "title": "Teste Import",
            "description": "Descrição",
            "code": "int main(){}",
            "author": {"name": "Autor"},
            "period": "2027.1",
            "tags": ["tag_a", "tag_b"],
            "language": "cpp",
            "type": Question.Types.BASIC,
            "tests": [],
        }

        errors, period_info, tags_info = validate_import_item(item, valid_sets, create_missing=True)

        self.assertEqual(errors, [])
        self.assertEqual(period_info["type"], FieldStatus.NEW)
        self.assertEqual(len(tags_info), 2)
        self.assertTrue(all(t["type"] == FieldStatus.NEW for t in tags_info))

    def test_process_database_import_creates_records_when_create_missing(self):
        valid_tag = Tag.objects.create(slug="t1", name="T1")

        selected_items = [
            {
                "title": "Import Question",
                "description": "Desc",
                "code": "code",
                "author": {"name": "LegacyAuthor", "github_url": "https://github.com/leg"},
                "period": "2028.0",
                "tags": ["t1", "t_new"],
                "language": "cpp",
                "type": Question.Types.BASIC,
                "tests": [
                    {"input_data": "1", "output_data": "1", "type": Test.TestType.PUBLIC},
                    {"input_data": "2", "output_data": "2", "type": Test.TestType.PRIVATE},
                ],
            }
        ]

        # garantir que as regras mínimas de testes não causem falha
        settings = SystemSetting.get_solo()
        settings.min_private_tests_in_questions = 0
        settings.min_public_tests_in_questions = 0
        settings.save()

        questions_created, tests_created = process_database_import(
            selected_items, create_missing=True
        )

        self.assertEqual(questions_created, 1)
        self.assertEqual(tests_created, 2)
        self.assertTrue(Question.objects.filter(title="Import Question").exists())
        self.assertTrue(Tag.objects.filter(slug="t_new").exists())

    def test_process_database_import_raises_on_invalid_item(self):
        selected_items = [
            {
                "description": "No title",
                "code": "code",
                "author": {"name": "A"},
                "period": "2029.0",
                "tags": [],
                "tests": [],
            }
        ]

        settings = SystemSetting.get_solo()
        settings.min_private_tests_in_questions = 0
        settings.min_public_tests_in_questions = 0
        settings.save()

        with self.assertRaises(ValueError):
            process_database_import(selected_items, create_missing=True)

    def test_check_similarity_detects_similar_question(self):
        author = AssistentStudent.get_or_create_legacy(name="A", github_url="https://g")
        period = Period.objects.create(name="2030.0")
        q = Question.objects.create(
            title="Soma",
            description="Soma dois números",
            code="int soma(){return 0;}",
            language="c",
            type=Question.Types.BASIC,
            author=author,
            period=period,
        )

        result = check_similarity(
            "Soma", "Outra desc", "int soma(){return 0;}", "c", [q], threshold=0.5
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["instance"].pk, q.pk)

    def test_get_valid_random_registration_format(self):
        reg = get_valid_random_registration()
        self.assertTrue(reg.startswith("0000"))
        self.assertEqual(len(reg), 9)
        self.assertTrue(reg[4:].isdigit())

    def test_group_helpers_create_groups_with_permissions(self):
        g1 = get_or_create_professors_group()
        g2 = get_or_create_assistentstudent_group()

        self.assertEqual(g1.name, "Professores")
        self.assertEqual(g2.name, "Monitores")
        self.assertTrue(g1.permissions.exists())
        self.assertTrue(g2.permissions.exists())
