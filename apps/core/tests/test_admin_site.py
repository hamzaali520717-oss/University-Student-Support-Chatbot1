from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.academics.models import Department, Program
from apps.accounts.models import StudentProfile, User
from apps.assistant import services
from apps.assistant.models import Document
from apps.core.signals import ADMIN_STAFF_GROUP_NAME, sync_admin_staff_group


class GroupBasedAdminStaffTests(TestCase):
    """The "Admin Staff" group is the sole source of admin permissions for
    role=admin users (see apps.core.signals) - is_superuser is deliberately
    never granted, so these exercise a non-superuser staff account against
    both what it should and should not be able to do."""

    def setUp(self):
        sync_admin_staff_group()
        self.department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=self.department, code="CS", name="Computer Science"
        )

        self.staff_user = User.objects.create_user(
            username="group_admin", password="pw", role=User.Role.ADMIN, is_staff=True
        )
        self.staff_user.groups.add(Group.objects.get(name=ADMIN_STAFF_GROUP_NAME))
        assert not self.staff_user.is_superuser
        self.client.force_login(self.staff_user)

    def test_reaches_dashboard_with_full_app_list(self):
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "You don’t have permission to view or edit anything.")
        self.assertContains(response, "Academics")

    def test_can_create_student_with_profile(self):
        response = self.client.post(
            reverse("admin:accounts_user_add"),
            {
                "username": "new_student",
                "password1": "Sup3rSecretPW!1",
                "password2": "Sup3rSecretPW!1",
                "role": "student",
                "student_profile-TOTAL_FORMS": "1",
                "student_profile-INITIAL_FORMS": "0",
                "student_profile-MIN_NUM_FORMS": "0",
                "student_profile-MAX_NUM_FORMS": "1",
                "student_profile-0-registration_no": "REG-1",
                "student_profile-0-program": str(self.program.pk),
                "student_profile-0-id": "",
                "_save": "Save",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(StudentProfile.objects.filter(user__username="new_student").exists())

    def test_can_upload_document(self):
        upload = SimpleUploadedFile("handbook.txt", b"Semester begins in September.")
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("admin:assistant_document_add"),
                {"title": "Handbook", "file": upload, "visibility": "public", "_save": "Save"},
                follow=True,
            )
        self.assertEqual(response.status_code, 200)
        document = Document.objects.get(title="Handbook")
        self.assertEqual(document.status, Document.Status.READY)
        self.assertTrue(document.chunks.exists())

    def test_cannot_access_group_admin(self):
        response = self.client.get(reverse("admin:auth_group_changelist"))
        self.assertEqual(response.status_code, 403)

    def test_cannot_delete_catalog_synced_document(self):
        services.sync_catalog_documents()
        catalog_document = Document.objects.get(
            source_content_type__isnull=False, source_object_id=self.program.pk
        )

        response = self.client.post(reverse("admin:assistant_document_delete", args=[catalog_document.pk]))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Document.objects.filter(pk=catalog_document.pk).exists())


class BootstrapSuperuserAccessTests(TestCase):
    """Regression: role defaults to student (exactly what a plain
    `createsuperuser` produces, since role isn't a REQUIRED_FIELD), and the
    site-entry gate used to check role==admin with no is_superuser bypass -
    locking a freshly bootstrapped superuser out of /admin/ entirely with no
    recovery path."""

    def test_superuser_with_default_role_reaches_dashboard(self):
        bootstrap_superuser = User.objects.create_superuser(username="bootstrap", password="pw")
        self.assertEqual(bootstrap_superuser.role, User.Role.STUDENT)

        self.client.force_login(bootstrap_superuser)
        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "You don’t have permission to view or edit anything.")
