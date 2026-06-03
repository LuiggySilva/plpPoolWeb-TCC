import json
import uuid
from datetime import timedelta
from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from code_compiler.models import (
    CodeActivity,
    CodeVerdict,
    ExecutionType,
    ManualRun,
    QuestionValidation,
    TaskStatus,
    ValidationTestResult,
)
from questions.models import Period, Question, Tag, Test
from user.models import AssistentStudent, CustomUser


class UserFactory:
    """Factory para criar usuários de teste"""

    @staticmethod
    def create_user(email="testuser@test.com", password="testpass123", name="Test User"):
        period, _ = Period.objects.get_or_create(name="2024.1")
        return CustomUser.objects.create_user(
            email=email,
            password=password,
            name=name,
            period=period,
        )

    @staticmethod
    def create_assistent_student(email="monitor@test.com", password="testpass123", name="Monitor"):
        period, _ = Period.objects.get_or_create(name="2024.1")
        user = CustomUser.objects.create_user(
            email=email,
            password=password,
            name=name,
            period=period,
            role="monitor",
        )
        # Retorna como AssistentStudent proxy
        return AssistentStudent.objects.get(pk=user.pk)


class QuestionFactory:
    """Factory para criar questões"""

    @staticmethod
    def create_question(
        title="Test Question",
        description="Test Description",
        author=None,
        code="int main() { return 0; }",
    ):
        if not author:
            author = UserFactory.create_assistent_student()

        period, _ = Period.objects.get_or_create(name="2024.1")

        question = Question.objects.create(
            title=title,
            description=description,
            author=author,
            period=period,
            code=code,
        )

        # Adicionar pelo menos uma tag
        tag, _ = Tag.objects.get_or_create(name="básico", defaults={"slug": "basico"})
        question.tags.add(tag)

        return question


class TestFactory:
    """Factory para criar testes de questão"""

    @staticmethod
    def create_test(question=None, input_data="", output_data=""):
        if not question:
            question = QuestionFactory.create_question()

        return Test.objects.create(
            question=question,
            input_data=input_data,
            output_data=output_data,
        )


class SubmitManualRunViewTests(TestCase):
    """Testes para a view submit_manual_run_view"""

    def setUp(self):
        self.client = Client()
        self.user = UserFactory.create_user()
        self.question = QuestionFactory.create_question()
        self.url = reverse("code_compiler:submit_manual_run", args=[self.question.id])

    def test_post_requires_authentication(self):
        """Testa se requer autenticação"""
        response = self.client.post(
            self.url,
            data=json.dumps({"code": "print('test')", "language": "python", "inputs": ""}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 302)  # Redireciona para login

    def test_post_with_authenticated_user(self):
        """Testa POST com usuário autenticado"""
        self.client.force_login(self.user)

        with patch("code_compiler.views.process_code_activity_task.delay"):
            response = self.client.post(
                self.url,
                data=json.dumps({"code": "print('test')", "language": "python", "inputs": ""}),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("activity_id", data)

        # Verifica se a atividade foi criada
        activity = CodeActivity.objects.get(id=data["activity_id"])
        self.assertEqual(activity.user, self.user)
        self.assertEqual(activity.activity_type, ExecutionType.MANUAL)

    def test_get_request_not_allowed(self):
        """Testa que GET não é permitido"""
        self.client.force_login(self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)  # Method Not Allowed

    def test_cannot_submit_while_running(self):
        """Testa que não pode submeter enquanto há execução em andamento"""
        self.client.force_login(self.user)

        # Criar uma atividade em andamento
        running_activity = CodeActivity.objects.create(
            user=self.user,
            language="python",
            source_code="print('running')",
            status=TaskStatus.RUNNING,
            activity_type=ExecutionType.MANUAL,
            question=self.question,
        )

        response = self.client.post(
            self.url,
            data=json.dumps({"code": "print('test')", "language": "python", "inputs": ""}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 429)  # Too Many Requests
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertEqual(data["activity_id"], str(running_activity.id))

    def test_cannot_submit_while_pending(self):
        """Testa que não pode submeter enquanto há execução pendente"""
        self.client.force_login(self.user)

        # Criar uma atividade pendente
        pending_activity = CodeActivity.objects.create(
            user=self.user,
            language="python",
            source_code="print('pending')",
            status=TaskStatus.PENDING,
            activity_type=ExecutionType.MANUAL,
            question=self.question,
        )

        response = self.client.post(
            self.url,
            data=json.dumps({"code": "print('test')", "language": "python", "inputs": ""}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 429)  # Too Many Requests

    def test_can_submit_after_completed(self):
        """Testa que pode submeter após conclusão"""
        self.client.force_login(self.user)

        # Criar uma atividade concluída
        CodeActivity.objects.create(
            user=self.user,
            language="python",
            source_code="print('completed')",
            status=TaskStatus.COMPLETED,
            activity_type=ExecutionType.MANUAL,
            question=self.question,
        )

        with patch("code_compiler.views.process_code_activity_task.delay"):
            response = self.client.post(
                self.url,
                data=json.dumps({"code": "print('test')", "language": "python", "inputs": ""}),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)

    def test_activity_created_with_correct_fields(self):
        """Testa se a atividade é criada com campos corretos"""
        self.client.force_login(self.user)

        code = "print('hello')"
        language = "python"
        inputs = "test input"

        with patch("code_compiler.views.process_code_activity_task.delay"):
            response = self.client.post(
                self.url,
                data=json.dumps({"code": code, "language": language, "inputs": inputs}),
                content_type="application/json",
            )

        data = json.loads(response.content)
        activity = CodeActivity.objects.get(id=data["activity_id"])

        self.assertEqual(activity.source_code, code)
        self.assertEqual(activity.language, language)
        self.assertEqual(activity.manual_inputs, inputs)
        self.assertEqual(activity.status, TaskStatus.PENDING)

    def test_task_delay_is_called(self):
        """Testa se o task delay é chamado"""
        self.client.force_login(self.user)

        with patch("code_compiler.views.process_code_activity_task.delay") as mock_task:
            self.client.post(
                self.url,
                data=json.dumps({"code": "print('test')", "language": "python", "inputs": ""}),
                content_type="application/json",
            )

        mock_task.assert_called_once()

    def test_question_not_found(self):
        """Testa erro quando questão não existe"""
        self.client.force_login(self.user)
        invalid_url = reverse("code_compiler:submit_manual_run", args=[99999])

        response = self.client.post(
            invalid_url,
            data=json.dumps({"code": "print('test')", "language": "python", "inputs": ""}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)

    def test_invalid_json_request(self):
        """Testa erro com JSON inválido"""
        self.client.force_login(self.user)

        response = self.client.post(
            self.url,
            data="invalid json",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)


class SubmitValidationViewTests(TestCase):
    """Testes para a view submit_validation_view"""

    def setUp(self):
        self.client = Client()
        self.user = UserFactory.create_user()
        self.question = QuestionFactory.create_question()
        self.url = reverse("code_compiler:submit_validation", args=[self.question.id])

    def test_post_with_authenticated_user(self):
        """Testa POST com usuário autenticado"""
        self.client.force_login(self.user)

        with patch("code_compiler.views.process_code_activity_task.delay"):
            response = self.client.post(
                self.url,
                data=json.dumps({"code": "print('test')", "language": "python"}),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("activity_id", data)

    def test_validation_activity_created(self):
        """Testa se uma atividade de validação é criada"""
        self.client.force_login(self.user)

        code = "int main() { return 0; }"
        language = "c"

        with patch("code_compiler.views.process_code_activity_task.delay"):
            response = self.client.post(
                self.url,
                data=json.dumps({"code": code, "language": language}),
                content_type="application/json",
            )

        data = json.loads(response.content)
        activity = CodeActivity.objects.get(id=data["activity_id"])

        self.assertEqual(activity.activity_type, ExecutionType.VALIDATION)
        self.assertEqual(activity.question, self.question)
        self.assertEqual(activity.source_code, code)
        self.assertEqual(activity.language, language)

    def test_get_request_not_allowed(self):
        """Testa que GET não é permitido"""
        self.client.force_login(self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)

    def test_requires_authentication(self):
        """Testa se requer autenticação"""
        response = self.client.post(
            self.url,
            data=json.dumps({"code": "print('test')", "language": "python"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 302)

    def test_question_not_found(self):
        """Testa erro quando questão não existe"""
        self.client.force_login(self.user)
        invalid_url = reverse("code_compiler:submit_validation", args=[99999])

        response = self.client.post(
            invalid_url,
            data=json.dumps({"code": "print('test')", "language": "python"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)

    def test_task_delay_is_called(self):
        """Testa se o task delay é chamado"""
        self.client.force_login(self.user)

        with patch("code_compiler.views.process_code_activity_task.delay") as mock_task:
            self.client.post(
                self.url,
                data=json.dumps({"code": "print('test')", "language": "python"}),
                content_type="application/json",
            )

        mock_task.assert_called_once()


class CheckActivityStatusViewTests(TestCase):
    """Testes para a view check_activity_status_view"""

    def setUp(self):
        self.client = Client()
        self.user = UserFactory.create_user()
        self.question = QuestionFactory.create_question()

    def test_get_manual_run_status(self):
        """Testa verificação de status de execução manual"""
        activity = ManualRun.objects.create(
            user=self.user,
            language="python",
            source_code="print('test')",
            status=TaskStatus.COMPLETED,
            manual_stdout="test\n",
            manual_stderr="",
            manual_verdict=CodeVerdict.AC,
            question=self.question,
        )

        self.client.force_login(self.user)
        url = reverse("code_compiler:check_activity_status", args=[activity.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertEqual(data["status"], TaskStatus.COMPLETED)
        self.assertEqual(data["activity_type"], ExecutionType.MANUAL)
        self.assertEqual(data["stdout"], "test\n")
        self.assertEqual(data["stderr"], "")
        self.assertEqual(data["verdict"], CodeVerdict.AC)

    def test_get_validation_status(self):
        """Testa verificação de status de validação"""
        activity = QuestionValidation.objects.create(
            user=self.user,
            language="python",
            source_code="print('test')",
            status=TaskStatus.COMPLETED,
            question=self.question,
            verdict=CodeVerdict.AC,
        )

        self.client.force_login(self.user)
        url = reverse("code_compiler:check_activity_status", args=[activity.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertEqual(data["status"], TaskStatus.COMPLETED)
        self.assertEqual(data["activity_type"], ExecutionType.VALIDATION)

    def test_validation_with_test_results(self):
        """Testa validação com resultados de testes"""
        activity = QuestionValidation.objects.create(
            user=self.user,
            language="python",
            source_code="print('test')",
            status=TaskStatus.COMPLETED,
            question=self.question,
        )

        test1 = TestFactory.create_test(
            question=self.question,
            input_data="",
            output_data="test\n",
        )
        test2 = TestFactory.create_test(
            question=self.question,
            input_data="2",
            output_data="4\n",
        )

        ValidationTestResult.objects.create(
            activity=activity,
            test=test1,
            passed=True,
            stdout="test\n",
        )
        ValidationTestResult.objects.create(
            activity=activity,
            test=test2,
            passed=False,
            stdout="2\n",
            stderr="Wrong output",
        )

        self.client.force_login(self.user)
        url = reverse("code_compiler:check_activity_status", args=[activity.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertEqual(len(data["test_results"]), 2)
        self.assertTrue(data["test_results"][0]["passed"])
        self.assertFalse(data["test_results"][1]["passed"])

    def test_requires_authentication(self):
        """Testa se requer autenticação"""
        activity = ManualRun.objects.create(
            user=self.user,
            language="python",
            source_code="print('test')",
            question=self.question,
        )

        url = reverse("code_compiler:check_activity_status", args=[activity.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)

    def test_user_cannot_see_other_user_activity(self):
        """Testa que usuário não pode ver atividade de outro usuário"""
        other_user = UserFactory.create_user(email="otheruser@test.com")
        activity = ManualRun.objects.create(
            user=other_user,
            language="python",
            source_code="print('test')",
            question=self.question,
        )

        self.client.force_login(self.user)
        url = reverse("code_compiler:check_activity_status", args=[activity.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_activity_not_found(self):
        """Testa erro quando atividade não existe"""
        self.client.force_login(self.user)
        invalid_id = uuid.uuid4()
        url = reverse("code_compiler:check_activity_status", args=[invalid_id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_delta_calculation(self):
        """Testa o cálculo do delta (tempo total de execução)"""
        now = timezone.now()
        activity = ManualRun.objects.create(
            user=self.user,
            language="python",
            source_code="print('test')",
            status=TaskStatus.COMPLETED,
            created_at=now,
            finished_at=now + timedelta(seconds=5),
            manual_stdout="test\n",
            question=self.question,
        )

        self.client.force_login(self.user)
        url = reverse("code_compiler:check_activity_status", args=[activity.id])
        response = self.client.get(url)

        data = json.loads(response.content)
        self.assertAlmostEqual(data["delta"], 5.0, delta=0.01)

    def test_delta_is_none_when_not_finished(self):
        """Testa que delta é None quando ainda está em execução"""
        activity = ManualRun.objects.create(
            user=self.user,
            language="python",
            source_code="print('test')",
            status=TaskStatus.RUNNING,
            question=self.question,
        )

        self.client.force_login(self.user)
        url = reverse("code_compiler:check_activity_status", args=[activity.id])
        response = self.client.get(url)

        data = json.loads(response.content)
        self.assertIsNone(data["delta"])

    def test_system_error_flag(self):
        """Testa a flag de erro de sistema"""
        activity = ManualRun.objects.create(
            user=self.user,
            language="python",
            source_code="print('test')",
            status=TaskStatus.SYSTEM_ERROR,
            question=self.question,
        )

        self.client.force_login(self.user)
        url = reverse("code_compiler:check_activity_status", args=[activity.id])
        response = self.client.get(url)

        data = json.loads(response.content)
        self.assertTrue(data.get("is_system_error"))

    def test_finished_at_timestamp(self):
        """Testa o timestamp de finalização"""
        now = timezone.now()
        activity = ManualRun.objects.create(
            user=self.user,
            language="python",
            source_code="print('test')",
            status=TaskStatus.COMPLETED,
            finished_at=now,
            manual_stdout="test\n",
            question=self.question,
        )

        self.client.force_login(self.user)
        url = reverse("code_compiler:check_activity_status", args=[activity.id])
        response = self.client.get(url)

        data = json.loads(response.content)
        self.assertIsNotNone(data["finished_at"])


class ViewIntegrationTests(TestCase):
    """Testes de integração entre views"""

    def setUp(self):
        self.client = Client()
        self.user = UserFactory.create_user()
        self.question = QuestionFactory.create_question()

    def test_full_manual_run_workflow(self):
        """Testa o fluxo completo de execução manual"""
        self.client.force_login(self.user)
        submit_url = reverse("code_compiler:submit_manual_run", args=[self.question.id])

        with patch("code_compiler.views.process_code_activity_task.delay"):
            response = self.client.post(
                submit_url,
                data=json.dumps({"code": "print('hello')", "language": "python", "inputs": ""}),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        activity_id = json.loads(response.content)["activity_id"]

        # Simular conclusão da tarefa
        activity = CodeActivity.objects.get(id=activity_id)
        activity.status = TaskStatus.COMPLETED
        activity.manual_stdout = "hello\n"
        activity.manual_verdict = CodeVerdict.AC
        activity.save()

        # Verificar status
        status_url = reverse("code_compiler:check_activity_status", args=[activity_id])
        response = self.client.get(status_url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], TaskStatus.COMPLETED)
        self.assertEqual(data["stdout"], "hello\n")

    def test_full_validation_workflow(self):
        """Testa o fluxo completo de validação"""
        self.client.force_login(self.user)
        submit_url = reverse("code_compiler:submit_validation", args=[self.question.id])

        with patch("code_compiler.views.process_code_activity_task.delay"):
            response = self.client.post(
                submit_url,
                data=json.dumps({"code": "print('test')", "language": "python"}),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        activity_id = json.loads(response.content)["activity_id"]

        # Criar teste e resultado
        test = TestFactory.create_test(
            question=self.question,
            input_data="",
            output_data="test\n",
        )

        activity = CodeActivity.objects.get(id=activity_id)
        activity.status = TaskStatus.COMPLETED
        activity.save()

        ValidationTestResult.objects.create(
            activity=activity,
            test=test,
            passed=True,
            stdout="test\n",
        )

        # Verificar status
        status_url = reverse("code_compiler:check_activity_status", args=[activity_id])
        response = self.client.get(status_url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data["test_results"]), 1)
        self.assertTrue(data["test_results"][0]["passed"])
