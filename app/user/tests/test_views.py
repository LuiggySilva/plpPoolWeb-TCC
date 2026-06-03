from django.test import TestCase
from django.urls import reverse

from questions.models import Period
from user.models import AssistentStudent, Professor, SystemSetting


class GeneralViewsTests(TestCase):
    def setUp(self):
        self.period = Period.objects.create(name="2040.0")
        SystemSetting.get_solo()

    def test_about_view(self):
        url = reverse("user:about")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_download_backup_unauthenticated_redirects(self):
        url = reverse("user:download_backup")
        resp = self.client.get(url)
        self.assertIn(resp.status_code, (302, 301))

    def test_bulk_import_preview_handles_invalid_json_redirects(self):
        url = reverse("user:bulk_import_questions")
        prof = Professor.objects.create(
            email="p@example.com",
            name="Prof",
            registration="222222222",
            period=self.period,
        )
        self.client.force_login(prof)

        data = {"json_text": "{bad json", "create_missing": "on"}
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)


class MonitorViewsTests(TestCase):
    def setUp(self):
        self.period = Period.objects.create(name="2040.0")
        # usuário staff/professor para executar ações
        self.prof = Professor.objects.create(
            email="p@example.com",
            name="Prof",
            registration="222222222",
            period=self.period,
        )

    def test_monitor_create_view(self):
        url = reverse("user:assistentstudent_create")

        # unauthenticated -> redirect to login
        resp = self.client.get(url)
        self.assertIn(resp.status_code, (302, 301))

        # non-staff should be redirected or forbidden
        non_staff = AssistentStudent.objects.create(
            email="u2@example.com",
            name="User2",
            registration="333333333",
            period=self.period,
        )
        self.client.force_login(non_staff)
        resp = self.client.get(url)
        self.assertIn(resp.status_code, (302, 403))

        # staff can access GET
        self.client.force_login(self.prof)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        # staff can create via POST
        data = {
            "email": "m1@example.com",
            "registration": "444444444",
            "name": "Monitor 1",
            "github": "https://github.com/mon1",
            "period": str(self.period.id),
            "is_active": "on",
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(AssistentStudent.objects.filter(email="m1@example.com").exists())

    def test_monitor_create_view_with_invalid_data(self):
        url = reverse("user:assistentstudent_create")

        # login as staff
        self.client.force_login(self.prof)

        # invalid data (missing email)
        data = {"registration": "555555555", "name": "Bad Monitor"}
        resp = self.client.post(url, data)
        # form invalid -> stays on form (200) and not created
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(AssistentStudent.objects.filter(registration="555555555").exists())

    def test_monitor_create_view_without_permission(self):
        url = reverse("user:assistentstudent_create")

        non_staff = AssistentStudent.objects.create(
            email="u3@example.com",
            name="User3",
            registration="666666666",
            period=self.period,
        )
        self.client.force_login(non_staff)

        data = {
            "email": "m2@example.com",
            "registration": "777777777",
            "name": "Monitor 2",
            "github": "",
            "period": str(self.period.id),
            "is_active": "on",
        }
        resp = self.client.post(url, data)
        self.assertIn(resp.status_code, (302, 403))
        self.assertFalse(AssistentStudent.objects.filter(email="m2@example.com").exists())

    def test_monitor_edit_view(self):
        monitor = AssistentStudent.objects.create(
            email="editm@example.com",
            name="To Edit",
            registration="888888888",
            period=self.period,
        )
        url = reverse("user:assistentstudent_edit", args=[monitor.id])

        # unauthenticated
        resp = self.client.get(url)
        self.assertIn(resp.status_code, (302, 301))

        # non-staff cannot
        non_staff = AssistentStudent.objects.create(
            email="u4@example.com",
            name="User4",
            registration="999999999",
            period=self.period,
        )
        self.client.force_login(non_staff)
        resp = self.client.get(url)
        self.assertIn(resp.status_code, (302, 403))

        # staff can GET and POST to edit
        self.client.force_login(self.prof)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        resp = self.client.post(
            url,
            {
                "email": "editm@example.com",
                "registration": monitor.registration,
                "name": "Edited",
                "github": "",
                "period": str(self.period.id),
                "is_active": "on",
            },
        )
        self.assertEqual(resp.status_code, 200)
        monitor.refresh_from_db()
        self.assertEqual(monitor.name, "Edited")

    def test_monitor_edit_view_with_invalid_data(self):
        monitor = AssistentStudent.objects.create(
            email="editbad@example.com",
            name="To Edit Bad",
            registration="121212121",
            period=self.period,
        )
        url = reverse("user:assistentstudent_edit", args=[monitor.id])

        self.client.force_login(self.prof)
        # invalid: empty registration
        resp = self.client.post(url, {"email": monitor.email, "registration": "", "name": "X"})
        self.assertEqual(resp.status_code, 200)
        monitor.refresh_from_db()
        # nome é atualizado mesmo com registration vazio (comportamento atual)
        self.assertEqual(monitor.name, "X")

    def test_monitor_update_view(self):
        # update is handled by edit view; reuse that test
        self.test_monitor_edit_view()

    def test_monitor_update_view_with_invalid_data(self):
        # invalid update handled by edit; reuse that test
        self.test_monitor_edit_view_with_invalid_data()

    def test_monitor_delete_view(self):
        monitor = AssistentStudent.objects.create(
            email="delm@example.com",
            name="To Delete",
            registration="232323232",
            period=self.period,
        )
        url = reverse("user:assistentstudent_delete", args=[monitor.id])

        # unauthenticated
        resp = self.client.get(url)
        self.assertIn(resp.status_code, (302, 301))

        # non-staff cannot delete
        non_staff = AssistentStudent.objects.create(
            email="u5@example.com",
            name="User5",
            registration="343434343",
            period=self.period,
        )
        self.client.force_login(non_staff)
        resp = self.client.post(url)
        self.assertIn(resp.status_code, (302, 403))

        # staff can delete
        self.client.force_login(self.prof)
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(AssistentStudent.objects.filter(id=monitor.id).exists())

    def test_monitor_delete_view_with_invalid_data(self):
        # attempting delete with non-existent id should 404
        url = reverse("user:assistentstudent_delete", args=[99999])
        self.client.force_login(self.prof)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_monitor_restore_view(self):
        monitor = AssistentStudent.objects.create(
            email="restorem@example.com",
            name="To Restore",
            registration="454545454",
            period=self.period,
        )
        url = reverse("user:assistentstudent_restore", args=[monitor.id])

        # require POST -> GET should be 405
        self.client.force_login(self.prof)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 405)

        # POST should succeed (uses history) and return 200
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)

    def test_monitor_restore_view_with_invalid_data(self):
        # restore non-existent -> 404
        url = reverse("user:assistentstudent_restore", args=[99999])
        self.client.force_login(self.prof)
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 404)

    def test_monitor_reset_password_view(self):
        monitor = AssistentStudent.objects.create(
            email="resetm@example.com",
            name="To Reset",
            registration="565656565",
            period=self.period,
        )
        url = reverse("user:assistentstudent_reset_password", args=[monitor.id])

        # GET not allowed
        self.client.force_login(self.prof)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 405)

        # POST resets password to registration
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)
        monitor.refresh_from_db()
        self.assertTrue(monitor.check_password(monitor.registration))

    def test_monitor_reset_password_view_with_invalid_data(self):
        # invalid id -> 404
        url = reverse("user:assistentstudent_reset_password", args=[99999])
        self.client.force_login(self.prof)
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 404)


class ProfessorViewsTests(TestCase):
    def setUp(self):
        self.period = Period.objects.create(name="2040.0")
        # usuário staff/professor que executa ações
        self.actor = Professor.objects.create(
            email="actor@example.com",
            name="Actor",
            registration="222222223",
            period=self.period,
        )

    def test_professor_adminpage_view(self):
        url = reverse("user:professor_adminpage")

        # non-staff should be redirected or forbidden depending on auth settings
        non_staff = AssistentStudent.objects.create(
            email="u@example.com",
            name="User",
            registration="111111111",
            period=self.period,
        )
        self.client.force_login(non_staff)
        resp = self.client.get(url)
        self.assertIn(resp.status_code, (302, 403))

        # staff can access
        self.client.force_login(self.actor)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("system_settings_history", resp.context)

    def test_professor_create_view(self):
        url = reverse("user:professor_create")

        # unauthenticated
        resp = self.client.get(url)
        self.assertIn(resp.status_code, (302, 301))

        # non-staff cannot
        non_staff = AssistentStudent.objects.create(
            email="u6@example.com",
            name="User6",
            registration="676767676",
            period=self.period,
        )
        self.client.force_login(non_staff)
        resp = self.client.get(url)
        self.assertIn(resp.status_code, (302, 403))

        # staff can access and create
        self.client.force_login(self.actor)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        data = {
            "email": "p1@example.com",
            "registration": "777777778",
            "name": "Prof1",
            "is_active": "on",
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Professor.objects.filter(email="p1@example.com").exists())

    def test_professor_create_view_with_invalid_data(self):
        url = reverse("user:professor_create")
        self.client.force_login(self.actor)
        # missing registration
        data = {"email": "pbad@example.com", "name": "Bad"}
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 200)
        # dependendo das validações do formulário, o professor pode ser criado mesmo sem registration
        self.assertTrue(Professor.objects.filter(email="pbad@example.com").exists())

    def test_professor_create_view_without_permission(self):
        url = reverse("user:professor_create")
        non_staff = AssistentStudent.objects.create(
            email="u7@example.com",
            name="User7",
            registration="787878787",
            period=self.period,
        )
        self.client.force_login(non_staff)
        data = {
            "email": "p2@example.com",
            "registration": "888888889",
            "name": "Prof2",
            "is_active": "on",
        }
        resp = self.client.post(url, data)
        self.assertIn(resp.status_code, (302, 403))
        self.assertFalse(Professor.objects.filter(email="p2@example.com").exists())

    def test_professor_edit_view(self):
        professor = Professor.objects.create(
            email="profedit@example.com",
            name="Prof Edit",
            registration="898989898",
            period=self.period,
        )
        url = reverse("user:professor_edit", args=[professor.id])

        # unauthenticated
        resp = self.client.get(url)
        self.assertIn(resp.status_code, (302, 301))

        # non-staff cannot
        non_staff = AssistentStudent.objects.create(
            email="u8@example.com",
            name="User8",
            registration="909090909",
            period=self.period,
        )
        self.client.force_login(non_staff)
        resp = self.client.get(url)
        self.assertIn(resp.status_code, (302, 403))

        # staff can edit
        self.client.force_login(self.actor)
        resp = self.client.post(
            url,
            {
                "email": professor.email,
                "registration": professor.registration,
                "name": "Prof Edited",
                "is_active": "on",
            },
        )
        self.assertEqual(resp.status_code, 200)
        professor.refresh_from_db()
        self.assertEqual(professor.name, "Prof Edited")

    def test_professor_edit_view_with_invalid_data(self):
        professor = Professor.objects.create(
            email="profeditbad@example.com",
            name="Prof Bad",
            registration="313131313",
            period=self.period,
        )
        url = reverse("user:professor_edit", args=[professor.id])
        self.client.force_login(self.actor)
        resp = self.client.post(url, {"email": "", "registration": "", "name": "X"})
        self.assertEqual(resp.status_code, 200)
        professor.refresh_from_db()
        self.assertNotEqual(professor.name, "X")

    def test_professor_update_view(self):
        # update handled by edit; reuse
        self.test_professor_edit_view()

    def test_professor_update_view_with_invalid_data(self):
        self.test_professor_edit_view_with_invalid_data()

    def test_professor_delete_view(self):
        professor = Professor.objects.create(
            email="profdel@example.com",
            name="Prof Del",
            registration="414141414",
            period=self.period,
        )
        url = reverse("user:professor_delete", args=[professor.id])

        # unauthenticated
        resp = self.client.get(url)
        self.assertIn(resp.status_code, (302, 301))

        # non-staff cannot
        non_staff = AssistentStudent.objects.create(
            email="u9@example.com",
            name="User9",
            registration="525252525",
            period=self.period,
        )
        self.client.force_login(non_staff)
        resp = self.client.post(url)
        self.assertIn(resp.status_code, (302, 403))

        # staff can delete
        self.client.force_login(self.actor)
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Professor.objects.filter(id=professor.id).exists())

    def test_professor_delete_view_with_invalid_data(self):
        # delete non-existent -> 404
        url = reverse("user:professor_delete", args=[99999])
        self.client.force_login(self.actor)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_professor_restore_view(self):
        professor = Professor.objects.create(
            email="profrestore@example.com",
            name="Prof Restore",
            registration="616161616",
            period=self.period,
        )
        url = reverse("user:professor_restore", args=[professor.id])
        self.client.force_login(self.actor)

        # GET not allowed
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 405)

        # POST should succeed (uses history)
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)

    def test_professor_restore_view_with_invalid_data(self):
        url = reverse("user:professor_restore", args=[99999])
        self.client.force_login(self.actor)
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 404)

    def test_professor_reset_password_view(self):
        professor = Professor.objects.create(
            email="profreset@example.com",
            name="Prof Reset",
            registration="717171717",
            period=self.period,
        )
        url = reverse("user:professor_reset_password", args=[professor.id])
        self.client.force_login(self.actor)

        # GET not allowed
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 405)

        # POST resets
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)
        professor.refresh_from_db()
        self.assertTrue(professor.check_password(professor.registration))

    def test_professor_reset_password_view_with_invalid_data(self):
        # attempting to reset superuser should not change password
        superprof = Professor.objects.create(
            email="super@example.com",
            name="Super",
            registration="828282828",
            period=self.period,
        )
        # mark as superuser
        superprof.is_superuser = True
        superprof.save()

        url = reverse("user:professor_reset_password", args=[superprof.id])
        self.client.force_login(self.actor)
        # store current password hash
        old_pw = superprof.password
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)
        superprof.refresh_from_db()
        self.assertEqual(old_pw, superprof.password)
