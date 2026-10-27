import io
from datetime import timedelta

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.academics.models import Department, Program
from apps.assistant import services
from apps.assistant.models import Document


class ChunkTextTests(TestCase):
    def test_empty_text_returns_no_chunks(self):
        self.assertEqual(services.chunk_text(text="   "), [])

    def test_short_text_returns_single_chunk(self):
        chunks = services.chunk_text(text="short text", target_tokens=500, overlap_tokens=50)
        self.assertEqual(chunks, ["short text"])

    def test_long_text_splits_with_overlap(self):
        text = " ".join(f"word{i}" for i in range(25))
        chunks = services.chunk_text(text=text, target_tokens=10, overlap_tokens=3)
        self.assertGreater(len(chunks), 1)
        first_words = chunks[0].split()
        second_words = chunks[1].split()
        self.assertEqual(len(first_words), 10)
        self.assertEqual(first_words[-3:], second_words[:3])


class IngestDocumentTests(TestCase):
    def test_ingest_text_document_creates_ready_chunks(self):
        document = Document.objects.create(
            title="Library Hours",
            file=SimpleUploadedFile(
                "library.txt", b"The library opens at 8am and closes at 10pm."
            ),
        )
        result = services.ingest_document(document=document)
        self.assertEqual(result.status, Document.Status.READY)
        chunk = result.chunks.get()
        self.assertEqual(chunk.visibility, Document.Visibility.PUBLIC)
        self.assertEqual(len(chunk.embedding), settings.ASSISTANT_EMBEDDING_DIM)

    def test_extract_text_reads_docx(self):
        import docx

        source = docx.Document()
        source.add_paragraph("Hello from a Word document.")
        buffer = io.BytesIO()
        source.save(buffer)
        document = Document.objects.create(
            title="Handbook", file=SimpleUploadedFile("handbook.docx", buffer.getvalue())
        )
        self.assertIn("Hello from a Word document.", services.extract_text(document=document))

    def test_ingest_document_without_file_marks_failed(self):
        document = Document.objects.create(title="No file")
        result = services.ingest_document(document=document)
        self.assertEqual(result.status, Document.Status.FAILED)
        self.assertTrue(result.error)

    def test_reindex_reprocesses_a_failed_document(self):
        document = Document.objects.create(
            title="Doc",
            file=SimpleUploadedFile("d.txt", b"Reindexed content here."),
            status=Document.Status.FAILED,
            error="previous failure",
        )
        with self.captureOnCommitCallbacks(execute=True):
            services.reindex_document(document=document)
        document.refresh_from_db()
        self.assertEqual(document.status, Document.Status.READY)
        self.assertEqual(document.error, "")

    def test_delete_document_removes_record(self):
        document = Document.objects.create(title="ToDelete")
        services.delete_document(document=document)
        self.assertFalse(Document.objects.filter(id=document.id).exists())

    def test_create_document_triggers_ingestion_via_on_commit(self):
        with self.captureOnCommitCallbacks(execute=True):
            document = services.create_document(
                title="Handbook",
                file=SimpleUploadedFile("handbook.txt", b"Semester begins in September."),
            )
        document.refresh_from_db()
        self.assertEqual(document.status, Document.Status.READY)
        self.assertTrue(document.chunks.exists())


class CatalogSyncedDocumentProtectionTests(TestCase):
    """Regression: reindex_document/delete_document used to have no guard
    against catalog-synced Documents at all - only the Django admin's
    get_readonly_fields/has_delete_permission protected them, so any other
    caller (the assistant API's ReindexDocumentView/DocumentDetailView, a
    management command, a shell session) could reindex or delete a Document
    that apps.assistant.services.catalog owns exclusively via its
    (source_content_type, source_object_id) upsert key."""

    def setUp(self):
        department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        program = Program.objects.create(department=department, code="CS", name="Computer Science")
        self.catalog_document = Document.objects.create(
            title="Synced doc",
            source_content_type=ContentType.objects.get_for_model(Program),
            source_object_id=program.pk,
        )

    def test_reindex_document_rejects_catalog_synced(self):
        with self.assertRaises(PermissionDenied):
            services.reindex_document(document=self.catalog_document)

    def test_delete_document_rejects_catalog_synced(self):
        with self.assertRaises(PermissionDenied):
            services.delete_document(document=self.catalog_document)
        self.assertTrue(Document.objects.filter(pk=self.catalog_document.pk).exists())

    def test_reindex_document_still_works_for_uploaded_documents(self):
        document = Document.objects.create(
            title="Uploaded",
            file=SimpleUploadedFile("d.txt", b"Not catalog-synced."),
            status=Document.Status.FAILED,
        )
        with self.captureOnCommitCallbacks(execute=True):
            services.reindex_document(document=document)
        document.refresh_from_db()
        self.assertEqual(document.status, Document.Status.READY)

    def test_delete_document_still_works_for_uploaded_documents(self):
        document = Document.objects.create(title="Uploaded, deletable")
        services.delete_document(document=document)
        self.assertFalse(Document.objects.filter(pk=document.pk).exists())


class RecoverStuckDocumentsTests(TestCase):
    def setUp(self):
        self.stuck = Document.objects.create(title="Stuck", status=Document.Status.PROCESSING)
        Document.objects.filter(pk=self.stuck.pk).update(
            updated_at=timezone.now() - timedelta(hours=1)
        )
        self.recent = Document.objects.create(title="Recent", status=Document.Status.PROCESSING)

    def test_marks_stuck_documents_as_failed(self):
        count = services.recover_stuck_documents(timeout_minutes=30)

        self.assertEqual(count, 1)
        self.stuck.refresh_from_db()
        self.assertEqual(self.stuck.status, Document.Status.FAILED)
        self.assertTrue(self.stuck.error)

    def test_leaves_recently_started_documents_alone(self):
        services.recover_stuck_documents(timeout_minutes=30)

        self.recent.refresh_from_db()
        self.assertEqual(self.recent.status, Document.Status.PROCESSING)

    def test_management_command_reports_recovered_count(self):
        from io import StringIO

        out = StringIO()
        call_command("recover_stuck_ingestions", "--timeout-minutes=30", stdout=out)

        self.assertIn("Recovered 1 stuck document", out.getvalue())
        self.stuck.refresh_from_db()
        self.assertEqual(self.stuck.status, Document.Status.FAILED)
