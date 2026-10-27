from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.academics.models import Department, Program
from apps.accounts.models import StudentProfile, User
from apps.assistant.clients.embeddings import StubEmbeddingClient
from apps.assistant.models import Document, DocumentChunk
from apps.assistant.services.answering import I_DONT_KNOW, PERSONAL_DATA_UNAVAILABLE
from apps.finance.models import FeeStatus

embed = StubEmbeddingClient().embed_query


class DocumentManagementPermissionTests(APITestCase):
    def setUp(self):
        self.document = Document.objects.create(title="Handbook", status=Document.Status.READY)

    def test_anonymous_cannot_list_documents(self):
        response = self.client.get(reverse("document-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_student_cannot_upload_document(self):
        user = User.objects.create_user(username="stu", password="pw", role=User.Role.STUDENT)
        self.client.force_authenticate(user=user)
        response = self.client.post(reverse("document-list"), {"title": "New doc"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_upload_document_and_it_gets_ingested(self):
        admin = User.objects.create_user(username="admin", password="pw", role=User.Role.ADMIN)
        self.client.force_authenticate(user=admin)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("document-list"),
                {
                    "title": "Handbook 2",
                    "file": SimpleUploadedFile("handbook.txt", b"Semester begins in September."),
                },
                format="multipart",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        document = Document.objects.get(id=response.data["id"])
        self.assertEqual(document.status, Document.Status.READY)

    def test_admin_can_reindex_document(self):
        admin = User.objects.create_user(username="admin", password="pw", role=User.Role.ADMIN)
        self.client.force_authenticate(user=admin)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("document-reindex", args=[self.document.id]))

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def test_admin_can_delete_document(self):
        admin = User.objects.create_user(username="admin", password="pw", role=User.Role.ADMIN)
        self.client.force_authenticate(user=admin)
        response = self.client.delete(reverse("document-detail", args=[self.document.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Document.objects.filter(id=self.document.id).exists())

    def test_admin_cannot_delete_catalog_synced_document_via_api(self):
        # Regression: this endpoint had no protection at all against
        # catalog-synced documents - only the Django admin's
        # has_delete_permission did, so this API path could delete a
        # Document that apps.assistant.services.catalog owns exclusively.
        department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        program = Program.objects.create(department=department, code="CS", name="Computer Science")
        catalog_document = Document.objects.create(
            title="Synced doc",
            source_content_type=ContentType.objects.get_for_model(Program),
            source_object_id=program.pk,
        )
        admin = User.objects.create_user(username="admin", password="pw", role=User.Role.ADMIN)
        self.client.force_authenticate(user=admin)

        response = self.client.delete(reverse("document-detail", args=[catalog_document.id]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Document.objects.filter(id=catalog_document.id).exists())

    def test_disallowed_file_extension_rejected(self):
        # Regression: Document.file had no extension allowlist, so any file
        # type could be uploaded for in-memory extract_text() parsing.
        admin = User.objects.create_user(username="admin", password="pw", role=User.Role.ADMIN)
        self.client.force_authenticate(user=admin)

        response = self.client.post(
            reverse("document-list"),
            {
                "title": "Not a document",
                "file": SimpleUploadedFile("payload.exe", b"MZ\x90\x00fake-binary"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Document.objects.filter(title="Not a document").exists())

    @override_settings(ASSISTANT_MAX_UPLOAD_SIZE_MB=1)
    def test_oversized_file_rejected(self):
        # Regression: Document.file had no size cap, so an unbounded upload
        # could be used for memory-exhaustion DoS against extract_text(),
        # which reads the whole file into memory.
        admin = User.objects.create_user(username="admin", password="pw", role=User.Role.ADMIN)
        self.client.force_authenticate(user=admin)

        oversized = SimpleUploadedFile("big.txt", b"x" * (2 * 1024 * 1024))
        response = self.client.post(
            reverse("document-list"),
            {"title": "Too big", "file": oversized},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Document.objects.filter(title="Too big").exists())

    def test_admin_cannot_reindex_catalog_synced_document_via_api(self):
        department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        program = Program.objects.create(department=department, code="CS", name="Computer Science")
        catalog_document = Document.objects.create(
            title="Synced doc",
            source_content_type=ContentType.objects.get_for_model(Program),
            source_object_id=program.pk,
        )
        admin = User.objects.create_user(username="admin", password="pw", role=User.Role.ADMIN)
        self.client.force_authenticate(user=admin)

        response = self.client.post(reverse("document-reindex", args=[catalog_document.id]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AskViewTests(APITestCase):
    def setUp(self):
        department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=department, code="CS", name="Computer Science"
        )
        user_a = User.objects.create_user(username="stu-a", password="pw", role=User.Role.STUDENT)
        self.student_a = StudentProfile.objects.create(
            user=user_a, registration_no="REG-A", program=self.program
        )
        FeeStatus.objects.create(student=self.student_a, semester=1, amount_due="50000.00")

    def test_anonymous_gets_honest_i_dont_know_with_no_documents(self):
        response = self.client.post(reverse("ask"), {"question": "What are the library hours?"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["text"], I_DONT_KNOW)
        self.assertFalse(response.data["grounded"])
        self.assertEqual(response.data["sources"], [])

    def test_anonymous_gets_grounded_answer_from_public_document(self):
        content = "The library opens at 8am and closes at 10pm."
        document = Document.objects.create(title="Library Hours", status=Document.Status.READY)
        DocumentChunk.objects.create(
            document=document,
            ordinal=0,
            content=content,
            embedding=embed(content),
            visibility=Document.Visibility.PUBLIC,
        )

        response = self.client.post(reverse("ask"), {"question": content})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["grounded"])
        self.assertEqual(len(response.data["sources"]), 1)

    def test_authenticated_student_gets_answer_grounded_in_own_records(self):
        self.client.force_authenticate(user=self.student_a.user)
        response = self.client.post(reverse("ask"), {"question": "What is my fee status?"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["grounded"])
        self.assertIn("REG-A", response.data["text"])

    def test_blank_question_is_rejected(self):
        response = self.client.post(reverse("ask"), {"question": ""})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(ASSISTANT_LLM_CLIENT_PRIVATE="")
    def test_student_question_fails_closed_cleanly_instead_of_500(self):
        self.client.force_authenticate(user=self.student_a.user)
        response = self.client.post(reverse("ask"), {"question": "What is my fee status?"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["grounded"])
        self.assertEqual(response.data["text"], PERSONAL_DATA_UNAVAILABLE)
