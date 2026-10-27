from datetime import timedelta
from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import Course, Department, Program, Subject
from apps.admissions.models import AdmissionDeadline, AdmissionRequirement, Scholarship
from apps.assistant import services
from apps.assistant.clients.llm import LLMResponse
from apps.assistant.models import Document
from apps.assistant.services.answering import I_DONT_KNOW
from apps.finance.models import FeeStructure

TODAY = timezone.localdate()


class CatalogRendererTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=self.department, code="BSCS", name="BS Computer Science"
        )
        self.course = Course.objects.create(department=self.department, code="CS101", title="Intro to Programming")
        Subject.objects.create(program=self.program, course=self.course, semester=1, credit_hours=3)

    def test_render_program_lists_subjects_by_semester(self):
        rendered = services.render_program(program=self.program)

        self.assertEqual(len(rendered.chunks), 1)
        self.assertIn("Intro to Programming (CS101, 3 credit hours)", rendered.chunks[0].text)
        self.assertIn("Semester 1", rendered.chunks[0].text)
        self.assertEqual(
            rendered.citation_url, reverse("website:program-detail", kwargs={"code": "BSCS"})
        )

    def test_render_program_without_subjects_says_so(self):
        empty_program = Program.objects.create(department=self.department, code="BA", name="BA")
        rendered = services.render_program(program=empty_program)
        self.assertIn("No subjects are on record", rendered.chunks[0].text)

    def test_render_program_folds_in_admission_requirements(self):
        AdmissionRequirement.objects.create(
            program=self.program, title="Transcript", description="Submit official transcripts."
        )
        rendered = services.render_program(program=self.program)

        self.assertEqual(len(rendered.chunks), 1)
        self.assertIn("Transcript: Submit official transcripts.", rendered.chunks[0].text)

    @override_settings(ASSISTANT_CHUNK_TOKENS=5)
    def test_render_program_splits_into_two_chunks_when_content_is_long(self):
        AdmissionRequirement.objects.create(
            program=self.program, title="Transcript", description="Submit official transcripts."
        )
        rendered = services.render_program(program=self.program)

        self.assertEqual(len(rendered.chunks), 2)
        self.assertEqual(rendered.chunks[0].ordinal, 0)
        self.assertEqual(rendered.chunks[1].ordinal, 1)
        self.assertNotIn("Transcript", rendered.chunks[0].text)
        self.assertIn("Transcript", rendered.chunks[1].text)

    def test_render_fee_structure_includes_amount_and_breakdown(self):
        fee_structure = FeeStructure.objects.create(
            program=self.program, semester=1, amount="50000.00", breakdown={"tuition": "45000", "lab": "5000"}
        )
        rendered = services.render_fee_structure(fee_structure=fee_structure)

        self.assertIn("50000.00", rendered.chunks[0].text)
        self.assertIn("tuition: 45000", rendered.chunks[0].text)
        self.assertEqual(
            rendered.citation_url, reverse("website:program-detail", kwargs={"code": "BSCS"})
        )

    def test_render_admission_deadline_text_and_citation(self):
        deadline = AdmissionDeadline.objects.create(
            program=self.program, label="Merit list", date=TODAY + timedelta(days=10)
        )
        rendered = services.render_admission_deadline(deadline=deadline)

        self.assertIn("Merit list", rendered.chunks[0].text)
        self.assertIn("BS Computer Science", rendered.chunks[0].text)
        self.assertEqual(
            rendered.citation_url, reverse("website:program-detail", kwargs={"code": "BSCS"})
        )

    def test_render_scholarship_includes_description_and_eligibility(self):
        scholarship = Scholarship.objects.create(
            name="Need-Based Grant",
            description="Covers full tuition.",
            amount="100000.00",
            eligibility_criteria="Household income below threshold.",
        )
        rendered = services.render_scholarship(scholarship=scholarship)

        self.assertIn("Covers full tuition.", rendered.chunks[0].text)
        self.assertIn("Household income below threshold.", rendered.chunks[0].text)
        self.assertEqual(rendered.citation_url, reverse("website:scholarship-list"))


class ListCatalogSourcesTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=self.department, code="BSCS", name="BS Computer Science"
        )

    def test_filters_out_past_deadlines(self):
        AdmissionDeadline.objects.create(
            program=self.program, label="Past", date=TODAY - timedelta(days=1)
        )
        upcoming = AdmissionDeadline.objects.create(
            program=self.program, label="Upcoming", date=TODAY + timedelta(days=1)
        )

        sources = services.list_catalog_sources()
        deadline_sources = [s for s in sources if isinstance(s.source, AdmissionDeadline)]

        self.assertEqual([s.source for s in deadline_sources], [upcoming])

    def test_filters_out_inactive_scholarships(self):
        Scholarship.objects.create(name="Inactive", description="x", is_active=False)
        active = Scholarship.objects.create(name="Active", description="x", is_active=True)

        sources = services.list_catalog_sources()
        scholarship_sources = [s for s in sources if isinstance(s.source, Scholarship)]

        self.assertEqual([s.source for s in scholarship_sources], [active])


class SyncCatalogDocumentsTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=self.department, code="BSCS", name="BS Computer Science"
        )
        self.scholarship = Scholarship.objects.create(
            name="Need-Based Grant", description="Covers full tuition.", is_active=True
        )

    def test_creates_ready_documents_with_source_key_and_embeddings(self):
        result = services.sync_catalog_documents()

        self.assertEqual(result.synced, 2)  # the program + the scholarship
        self.assertEqual(result.removed, 0)
        document = Document.objects.get(source_object_id=self.program.pk)
        self.assertEqual(document.status, Document.Status.READY)
        self.assertEqual(document.visibility, Document.Visibility.PUBLIC)
        self.assertTrue(document.content_hash)
        self.assertEqual(document.source_url, reverse("website:program-detail", kwargs={"code": "BSCS"}))
        chunk = document.chunks.get()
        self.assertEqual(len(chunk.embedding), 768)
        self.assertEqual(chunk.visibility, Document.Visibility.PUBLIC)

    def test_rerun_without_changes_skips_reembedding(self):
        services.sync_catalog_documents()
        document = Document.objects.get(source_object_id=self.program.pk)
        original_chunk_id = document.chunks.get().id

        result = services.sync_catalog_documents()

        self.assertEqual(result.synced, 0)
        document.refresh_from_db()
        self.assertEqual(document.chunks.get().id, original_chunk_id)

    def test_changed_source_is_reembedded_in_place(self):
        services.sync_catalog_documents()
        document_id = Document.objects.get(source_object_id=self.scholarship.pk).id

        self.scholarship.description = "Now covers tuition and housing."
        self.scholarship.save()
        result = services.sync_catalog_documents()

        self.assertEqual(result.synced, 1)
        document = Document.objects.get(pk=document_id)
        self.assertIn("Now covers tuition and housing.", document.chunks.get().content)
        # Updated in place, not duplicated.
        self.assertEqual(Document.objects.filter(source_object_id=self.scholarship.pk).count(), 1)

    def test_management_command_reports_synced_count(self):
        out = StringIO()
        call_command("sync_catalog_documents", stdout=out)
        self.assertIn("Synced 2 catalog document(s)", out.getvalue())

    def test_retries_past_a_rate_limit_error_then_succeeds(self):
        from apps.assistant.clients.embeddings import StubEmbeddingClient

        class RateLimitedThenOk(StubEmbeddingClient):
            def __init__(self):
                super().__init__()
                self.calls = 0

            def embed_documents(self, texts):
                self.calls += 1
                if self.calls == 1:
                    error = Exception("429 RESOURCE_EXHAUSTED")
                    error.code = 429
                    raise error
                return super().embed_documents(texts)

        fake_client = RateLimitedThenOk()
        with patch(
            "apps.assistant.services.catalog.clients.get_embedding_client", return_value=fake_client
        ):
            result = services.sync_catalog_documents()

        self.assertEqual(result.synced, 2)
        self.assertEqual(fake_client.calls, 2)

    def test_non_rate_limit_error_is_not_retried(self):
        from apps.assistant.clients.embeddings import StubEmbeddingClient

        class AlwaysBroken(StubEmbeddingClient):
            def embed_documents(self, texts):
                raise ValueError("boom")

        with patch(
            "apps.assistant.services.catalog.clients.get_embedding_client",
            return_value=AlwaysBroken(),
        ):
            with self.assertRaises(ValueError):
                services.sync_catalog_documents()

    def test_orphan_cleanup_removes_document_whose_source_no_longer_exists(self):
        services.sync_catalog_documents()
        self.assertTrue(Document.objects.filter(source_object_id=self.scholarship.pk).exists())

        # Deleted with signals suppressed - simulates a bulk/backfill delete,
        # or data that predates the signals existing - so the Document is
        # left behind as an orphan for the batch pass to find.
        with services.suppress_catalog_signals():
            self.scholarship.delete()

        result = services.sync_catalog_documents()

        self.assertEqual(result.removed, 1)
        self.assertFalse(Document.objects.filter(source_object_id=self.scholarship.pk).exists())
        # The program's document is untouched - only the orphan is removed.
        self.assertTrue(Document.objects.filter(source_object_id=self.program.pk).exists())


class FeeChangePropagationTests(TestCase):
    """Exercises the batch/backfill sync path (as opposed to the signal path
    covered by CatalogSignalTests below): confirms that re-running
    sync_catalog_documents after an edit reaches the assistant's answer
    prompt in place, rather than leaving stale content sitting alongside the
    new figure. Useful e.g. after a bulk edit made with catalog signals
    suppressed."""

    def setUp(self):
        department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=department, code="BSCS", name="BS Computer Science"
        )
        self.fee_structure = FeeStructure.objects.create(
            program=self.program, semester=1, amount="85000.00"
        )

    @patch("apps.assistant.services.answering.clients.get_llm_client")
    def test_updated_fee_amount_is_reflected_after_resync(self, get_llm_client):
        mock_llm = MagicMock()
        mock_llm.generate.return_value = LLMResponse(text="answer")
        get_llm_client.return_value = mock_llm

        services.sync_catalog_documents()

        self.fee_structure.amount = "95000.00"
        self.fee_structure.save()
        result = services.sync_catalog_documents()
        self.assertEqual(result.synced, 1)

        services.answer_question(question="What is the BS Computer Science semester 1 fee?")

        prompt_sent = mock_llm.generate.call_args.kwargs["prompt"]
        self.assertIn("95000.00", prompt_sent)
        self.assertNotIn("85000.00", prompt_sent)


class CatalogSignalTests(TestCase):
    """Confirms the post_save/post_delete signals (apps.assistant.signals)
    keep the assistant's knowledge in sync immediately, with no manual
    sync_catalog_documents() call anywhere in these tests. Each write is
    wrapped in captureOnCommitCallbacks(execute=True) to actually run the
    transaction.on_commit-deferred sync within the test - without it, Django
    TestCase rolls back rather than commits, so on_commit callbacks (correctly)
    never fire; that's what keeps ordinary fixture setup elsewhere in the
    suite from triggering real embedding calls as a side effect."""

    def setUp(self):
        self.department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=self.department, code="BSCS", name="BS Computer Science"
        )

    def test_editing_a_fee_reflects_immediately_with_no_manual_sync(self):
        with self.captureOnCommitCallbacks(execute=True):
            fee_structure = FeeStructure.objects.create(
                program=self.program, semester=1, amount="85000.00"
            )

        with self.captureOnCommitCallbacks(execute=True):
            fee_structure.amount = "95000.00"
            fee_structure.save()

        rendered = services.render_fee_structure(fee_structure=fee_structure)
        answer = services.answer_question(question=rendered.chunks[0].text)

        self.assertTrue(answer.grounded)
        self.assertIn("95000.00", answer.text)
        self.assertNotIn("85000.00", answer.text)

    def test_editing_a_requirement_reflects_immediately_with_no_manual_sync(self):
        with self.captureOnCommitCallbacks(execute=True):
            requirement = AdmissionRequirement.objects.create(
                program=self.program, title="Transcript", description="Submit official transcripts."
            )

        with self.captureOnCommitCallbacks(execute=True):
            requirement.description = "Submit notarized transcripts."
            requirement.save()

        document = Document.objects.get(source_object_id=self.program.pk)
        chunk = document.chunks.get()
        self.assertIn("Submit notarized transcripts.", chunk.content)
        self.assertNotIn("Submit official transcripts.", chunk.content)

    def test_deleting_a_requirement_removes_it_from_the_program_immediately(self):
        with self.captureOnCommitCallbacks(execute=True):
            requirement = AdmissionRequirement.objects.create(
                program=self.program, title="Transcript", description="Submit official transcripts."
            )

        with self.captureOnCommitCallbacks(execute=True):
            requirement.delete()

        document = Document.objects.get(source_object_id=self.program.pk)
        self.assertNotIn("Transcript", document.chunks.get().content)

    def test_deleting_a_scholarship_removes_it_from_answers_immediately(self):
        with self.captureOnCommitCallbacks(execute=True):
            scholarship = Scholarship.objects.create(
                name="Need-Based Grant", description="Covers full tuition.", is_active=True
            )
        rendered = services.render_scholarship(scholarship=scholarship)
        query_text = rendered.chunks[0].text

        answer_before = services.answer_question(question=query_text)
        self.assertTrue(answer_before.grounded)

        with self.captureOnCommitCallbacks(execute=True):
            scholarship.delete()

        self.assertFalse(Document.objects.filter(source_object_id=scholarship.pk).exists())
        answer_after = services.answer_question(question=query_text)
        self.assertFalse(answer_after.grounded)
        self.assertEqual(answer_after.text, I_DONT_KNOW)
