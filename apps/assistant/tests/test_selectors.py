from datetime import timedelta

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.utils import timezone

from apps.academics.models import Department, Program
from apps.accounts.models import StudentProfile, User
from apps.assistant import selectors
from apps.assistant.clients.embeddings import StubEmbeddingClient
from apps.assistant.models import Document, DocumentChunk

embed = StubEmbeddingClient().embed_query


def _make_chunk(*, document, content, ordinal=0, visibility=Document.Visibility.PUBLIC):
    return DocumentChunk.objects.create(
        document=document,
        ordinal=ordinal,
        content=content,
        embedding=embed(content),
        visibility=visibility,
    )


class SearchChunksTests(TestCase):
    def setUp(self):
        self.ready_doc = Document.objects.create(title="Handbook", status=Document.Status.READY)
        self.pending_doc = Document.objects.create(title="Draft", status=Document.Status.PENDING)
        self.failed_doc = Document.objects.create(title="Broken", status=Document.Status.FAILED)

    def test_returns_matching_public_ready_chunk(self):
        target = _make_chunk(document=self.ready_doc, content="The library opens at 8am.")
        results = selectors.search_chunks(embedding=embed("The library opens at 8am."), limit=5)
        self.assertEqual(results[0].id, target.id)

    def test_excludes_chunks_from_non_ready_documents(self):
        _make_chunk(document=self.pending_doc, content="Pending chunk content.")
        _make_chunk(document=self.failed_doc, content="Failed chunk content.")
        results = selectors.search_chunks(embedding=embed("Pending chunk content."), limit=5)
        self.assertEqual(results, [])

    def test_excludes_non_public_visibility_chunks(self):
        _make_chunk(document=self.ready_doc, content="Restricted content.", visibility="restricted")
        results = selectors.search_chunks(embedding=embed("Restricted content."), limit=5)
        self.assertEqual(results, [])

    def test_respects_limit(self):
        for i in range(3):
            _make_chunk(document=self.ready_doc, content=f"Chunk number {i}.", ordinal=i)
        results = selectors.search_chunks(embedding=embed("Chunk number 0."), limit=2)
        self.assertEqual(len(results), 2)

    def test_max_distance_excludes_a_dissimilar_chunk(self):
        chunk_content = "The library opens at 8am."
        chunk_embedding = embed(chunk_content)
        _make_chunk(document=self.ready_doc, content=chunk_content)

        query_embedding = embed("A totally unrelated question about something else.")
        dot = sum(x * y for x, y in zip(query_embedding, chunk_embedding))
        distance = 1 - dot  # both vectors are unit-normalized by StubEmbeddingClient

        self.assertEqual(
            selectors.search_chunks(embedding=query_embedding, limit=5, max_distance=distance - 0.01),
            [],
        )
        self.assertEqual(
            len(
                selectors.search_chunks(
                    embedding=query_embedding, limit=5, max_distance=distance + 0.01
                )
            ),
            1,
        )


class GetAskingStudentTests(TestCase):
    def setUp(self):
        department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=department, code="CS", name="Computer Science"
        )
        self.student_user = User.objects.create_user(
            username="stu", password="pw", role=User.Role.STUDENT
        )
        self.student = StudentProfile.objects.create(
            user=self.student_user, registration_no="REG-1", program=self.program
        )
        self.admin_user = User.objects.create_user(username="admin", password="pw", role=User.Role.ADMIN)

    def test_returns_none_for_anonymous_user(self):
        self.assertIsNone(selectors.get_asking_student(user=AnonymousUser()))

    def test_returns_the_student_profile_for_a_student_user(self):
        result = selectors.get_asking_student(user=self.student_user)
        self.assertEqual(result, self.student)

    def test_returns_none_for_a_non_student_user(self):
        self.assertIsNone(selectors.get_asking_student(user=self.admin_user))


class ListStuckDocumentsTests(TestCase):
    def test_returns_only_processing_documents_older_than_cutoff(self):
        now = timezone.now()
        stuck = Document.objects.create(title="Stuck", status=Document.Status.PROCESSING)
        Document.objects.filter(pk=stuck.pk).update(updated_at=now - timedelta(hours=1))
        Document.objects.create(title="Recent", status=Document.Status.PROCESSING)
        Document.objects.create(title="Ready", status=Document.Status.READY)

        results = selectors.list_stuck_documents(cutoff=now - timedelta(minutes=30))

        self.assertEqual(list(results), [stuck])
