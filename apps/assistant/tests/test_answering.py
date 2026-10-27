from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.academics.models import Department, Program
from apps.accounts.models import StudentProfile, User
from apps.assistant import services
from apps.assistant.clients.embeddings import StubEmbeddingClient
from apps.assistant.clients.llm import LLMResponse
from apps.assistant.models import Document, DocumentChunk
from apps.assistant.services.answering import I_DONT_KNOW, PERSONAL_DATA_UNAVAILABLE
from apps.assistant.services.retrieval import RetrievedChunk

embed = StubEmbeddingClient().embed_query


def _make_ready_chunk(*, content, title="Handbook"):
    document = Document.objects.create(title=title, status=Document.Status.READY)
    return DocumentChunk.objects.create(
        document=document,
        ordinal=0,
        content=content,
        embedding=embed(content),
        visibility=Document.Visibility.PUBLIC,
    )


class AnswerQuestionTests(TestCase):
    def setUp(self):
        department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=department, code="CS", name="Computer Science"
        )
        user_a = User.objects.create_user(username="stu-a", password="pw")
        self.student_a = StudentProfile.objects.create(
            user=user_a, registration_no="REG-A", program=self.program
        )
        user_b = User.objects.create_user(username="stu-b", password="pw")
        self.student_b = StudentProfile.objects.create(
            user=user_b, registration_no="REG-B", program=self.program
        )

    @patch("apps.assistant.services.answering.clients.get_llm_client")
    def test_no_context_returns_i_dont_know_without_calling_llm(self, get_llm_client):
        mock_llm = MagicMock()
        get_llm_client.return_value = mock_llm

        answer = services.answer_question(question="Where is Atlantis?")

        self.assertEqual(answer.text, I_DONT_KNOW)
        self.assertFalse(answer.grounded)
        self.assertEqual(answer.sources, [])
        mock_llm.generate.assert_not_called()

    def test_grounded_answer_cites_matching_public_document(self):
        chunk = _make_ready_chunk(
            content="The library opens at 8am and closes at 10pm.", title="Library Hours"
        )
        answer = services.answer_question(question="The library opens at 8am and closes at 10pm.")

        self.assertTrue(answer.grounded)
        self.assertIn("The library opens at 8am and closes at 10pm.", answer.text)
        self.assertEqual(len(answer.sources), 1)
        self.assertEqual(answer.sources[0].document_id, chunk.document_id)
        self.assertEqual(answer.sources[0].title, "Library Hours")

    @patch("apps.assistant.services.answering.clients.get_llm_client")
    @patch("apps.assistant.services.answering.retrieve")
    def test_llm_declining_despite_retrieved_chunks_is_not_grounded(self, mock_retrieve, get_llm_client):
        # Even a chunk that passed the distance floor may not actually answer
        # the question; the LLM is instructed to say "I don't know" in that
        # case (secondary guard), and that reply must not be reported as
        # grounded or cite sources.
        mock_retrieve.return_value = [
            RetrievedChunk(
                chunk_id=1,
                document_id=1,
                document_title="Library Hours",
                content="The library opens at 8am and closes at 10pm.",
                distance=0.39,
            )
        ]
        mock_llm = MagicMock()
        mock_llm.generate.return_value = LLMResponse(text=I_DONT_KNOW)
        get_llm_client.return_value = mock_llm

        answer = services.answer_question(question="What is the capital of France?")

        self.assertEqual(answer.text, I_DONT_KNOW)
        self.assertFalse(answer.grounded)
        self.assertEqual(answer.sources, [])

    @patch("apps.assistant.services.answering.clients.get_llm_client")
    def test_llm_reply_wrapped_in_quotes_is_still_treated_as_a_decline(self, get_llm_client):
        # The system prompt tells the model to reply with I_DONT_KNOW verbatim
        # and no quote marks, but a model could still wrap it in quotes -
        # the comparison must tolerate that rather than treat it as grounded.
        chunk = _make_ready_chunk(content="The library opens at 8am and closes at 10pm.")
        mock_llm = MagicMock()
        mock_llm.generate.return_value = LLMResponse(text=f'"{I_DONT_KNOW}"')
        get_llm_client.return_value = mock_llm

        answer = services.answer_question(question=chunk.content)

        self.assertEqual(answer.text, I_DONT_KNOW)
        self.assertFalse(answer.grounded)
        self.assertEqual(answer.sources, [])

    @patch("apps.assistant.services.answering.clients.get_llm_client")
    def test_blank_llm_reply_is_treated_as_a_decline(self, get_llm_client):
        # GeminiLLMClient normalizes a safety-blocked/no-candidate response to
        # an empty string rather than None; that must also count as a decline.
        chunk = _make_ready_chunk(content="The library opens at 8am and closes at 10pm.")
        mock_llm = MagicMock()
        mock_llm.generate.return_value = LLMResponse(text="")
        get_llm_client.return_value = mock_llm

        answer = services.answer_question(question=chunk.content)

        self.assertEqual(answer.text, I_DONT_KNOW)
        self.assertFalse(answer.grounded)
        self.assertEqual(answer.sources, [])

    @patch("apps.assistant.services.answering.clients.get_llm_client")
    def test_anonymous_question_allows_training(self, get_llm_client):
        _make_ready_chunk(content="Tuition is due on the 1st of each month.")
        mock_llm = MagicMock()
        mock_llm.generate.return_value = LLMResponse(text="answer")
        get_llm_client.return_value = mock_llm

        services.answer_question(question="Tuition is due on the 1st of each month.")

        self.assertTrue(get_llm_client.call_args.kwargs["allow_training"])

    @patch("apps.assistant.services.answering.clients.get_llm_client")
    def test_student_question_never_allows_training(self, get_llm_client):
        mock_llm = MagicMock()
        mock_llm.generate.return_value = LLMResponse(text="answer")
        get_llm_client.return_value = mock_llm

        services.answer_question(
            question="What are my fees?", student=self.student_a, include_personal_context=True
        )

        self.assertFalse(get_llm_client.call_args.kwargs["allow_training"])

    @patch("apps.assistant.services.answering.clients.get_llm_client")
    def test_student_attached_but_not_a_personal_question_still_allows_training(
        self, get_llm_client
    ):
        # allow_training tracks whether personal data will actually be in the
        # prompt, not whether a session happens to be attached - a logged-in
        # student asking something with no personal data in it (e.g. "what
        # programs do you offer?") is exactly as safe to send to the free
        # client as an anonymous question, and must use it identically in dev
        # and prod rather than depending on ASSISTANT_LLM_CLIENT_PRIVATE being
        # configured for every authenticated user's every question.
        _make_ready_chunk(content="The library opens at 8am and closes at 10pm.")
        mock_llm = MagicMock()
        mock_llm.generate.return_value = LLMResponse(text="answer")
        get_llm_client.return_value = mock_llm

        services.answer_question(
            question="The library opens at 8am and closes at 10pm.",
            student=self.student_a,
            include_personal_context=False,
        )

        self.assertTrue(get_llm_client.call_args.kwargs["allow_training"])

    @patch("apps.assistant.services.answering.clients.get_llm_client")
    def test_personal_context_injection_is_the_moment_training_becomes_disallowed(
        self, get_llm_client
    ):
        # The instant include_personal_context actually causes personal data
        # to be attached (student present too), the non-training client
        # becomes required - this is the flip side of the free-client test
        # above, isolating personal-context injection as the one thing that
        # changes allow_training.
        mock_llm = MagicMock()
        mock_llm.generate.return_value = LLMResponse(text="answer")
        get_llm_client.return_value = mock_llm

        services.answer_question(
            question="What is my registration number?",
            student=self.student_a,
            include_personal_context=True,
        )

        self.assertFalse(get_llm_client.call_args.kwargs["allow_training"])

    @override_settings(ASSISTANT_LLM_CLIENT_PRIVATE="")
    def test_student_question_fails_closed_without_a_verified_non_training_client(self):
        answer = services.answer_question(
            question="What are my fees?", student=self.student_a, include_personal_context=True
        )

        self.assertFalse(answer.grounded)
        self.assertEqual(answer.sources, [])
        self.assertEqual(answer.text, PERSONAL_DATA_UNAVAILABLE)

    @patch("apps.assistant.services.answering.clients.get_llm_client")
    def test_student_question_only_ever_includes_own_records(self, get_llm_client):
        mock_llm = MagicMock()
        mock_llm.generate.return_value = LLMResponse(text="answer")
        get_llm_client.return_value = mock_llm

        services.answer_question(
            question="What is my registration number?",
            student=self.student_a,
            include_personal_context=True,
        )

        prompt_sent = mock_llm.generate.call_args.kwargs["prompt"]
        self.assertIn("REG-A", prompt_sent)
        self.assertNotIn("REG-B", prompt_sent)

    @patch("apps.assistant.services.answering.clients.get_llm_client")
    def test_personal_context_not_injected_without_the_explicit_flag(self, get_llm_client):
        # An attached StudentProfile is not, by itself, grounding: without
        # include_personal_context=True, build_student_context must never be
        # built or sent, even for a question with no public-KB match.
        mock_llm = MagicMock()
        mock_llm.generate.return_value = LLMResponse(text="answer")
        get_llm_client.return_value = mock_llm

        answer = services.answer_question(
            question="What is my registration number?",
            student=self.student_a,
            include_personal_context=False,
        )

        self.assertEqual(answer.text, I_DONT_KNOW)
        self.assertFalse(answer.grounded)
        mock_llm.generate.assert_not_called()

    def test_personal_flavored_question_from_anonymous_user_still_gets_honest_fallback(self):
        # include_personal_context can be True (the question is phrased in
        # the first person) while student is None (nobody is logged in) - an
        # attached StudentProfile is required, not just the wording, for the
        # deterministic fallback to be skipped.
        answer = services.answer_question(
            question="What is my registration number?",
            student=None,
            include_personal_context=True,
        )

        self.assertEqual(answer.text, I_DONT_KNOW)
        self.assertFalse(answer.grounded)


class IsPersonalQuestionTests(TestCase):
    def test_first_person_pronouns_are_detected(self):
        for question in [
            "What is my registration number?",
            "Am I eligible for a scholarship?",
            "Can I apply for financial aid?",
            "Where do I submit my thesis?",
        ]:
            with self.subTest(question=question):
                self.assertTrue(services.is_personal_question(question))

    def test_third_party_or_general_questions_are_not_personal(self):
        for question in [
            "What programs does the university offer?",
            "What are the library hours?",
            "When is the admissions deadline?",
        ]:
            with self.subTest(question=question):
                self.assertFalse(services.is_personal_question(question))
