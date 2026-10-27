import datetime
from unittest.mock import patch

from django.test import Client
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape

from apps.academics.models import Enrollment, SemesterPlan
from apps.admissions.models import AdmissionDeadline
from apps.assistant.services.answering import I_DONT_KNOW, Answer
from apps.finance.models import FeeStatus
from apps.portal.tests.base import PortalTestCase


class AskViewAccessTests(PortalTestCase):
    def test_anonymous_post_redirects_to_login_no_llm_call(self):
        with patch("apps.portal.views.answering.answer_question") as mock_answer:
            response = self.client.post(reverse("portal:ask"), {"question": "hello"})
        self.assertRedirects(response, f"{reverse('portal:login')}?next={reverse('portal:ask')}")
        mock_answer.assert_not_called()

    def test_admin_post_gets_403(self):
        self.login_admin()
        with patch("apps.portal.views.answering.answer_question") as mock_answer:
            response = self.client.post(reverse("portal:ask"), {"question": "hello"})
        self.assertEqual(response.status_code, 403)
        mock_answer.assert_not_called()

    def test_get_is_rejected(self):
        self.login_student()
        response = self.client.get(reverse("portal:ask"))
        self.assertEqual(response.status_code, 405)

    def test_blank_question_rejected_without_llm_call(self):
        self.login_student()
        with patch("apps.portal.views.answering.answer_question") as mock_answer:
            response = self.client.post(reverse("portal:ask"), {"question": "   "})
        self.assertEqual(response.status_code, 200)
        mock_answer.assert_not_called()

    def test_too_long_question_rejected_without_llm_call(self):
        self.login_student()
        with patch("apps.portal.views.answering.answer_question") as mock_answer:
            response = self.client.post(reverse("portal:ask"), {"question": "a" * 2001})
        self.assertEqual(response.status_code, 200)
        mock_answer.assert_not_called()

    def test_post_without_csrf_token_is_rejected(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.login(username="student1", password="pw")
        response = csrf_client.post(reverse("portal:ask"), {"question": "hello"})
        self.assertEqual(response.status_code, 403)


class AskViewRouterSafetyTests(PortalTestCase):
    """The core safety requirement: a personal question must never reach the
    LLM client, and even a router miss must never send the student's identity
    into the general RAG path (see apps/portal/views.py::ask)."""

    def setUp(self):
        super().setUp()
        self.login_student()

    def _ask_with_mocked_llm(self, question: str):
        with patch("apps.portal.views.answering.answer_question") as mock_answer:
            response = self.client.post(reverse("portal:ask"), {"question": question})
        return response, mock_answer

    def test_fee_question_never_calls_llm(self):
        FeeStatus.objects.create(
            student=self.student,
            semester=1,
            amount_due="50000.00",
            amount_paid="20000.00",
            status=FeeStatus.Status.PARTIAL,
        )
        response, mock_answer = self._ask_with_mocked_llm("What's my fee balance?")
        self.assertContains(response, "30,000")
        mock_answer.assert_not_called()

    def test_attendance_question_never_calls_llm(self):
        enrollment = Enrollment.objects.create(student=self.student, subject=self.subject)
        self.seed_attendance(enrollment, present_count=9, total_count=10)
        response, mock_answer = self._ask_with_mocked_llm("How many classes have I missed?")
        self.assertContains(response, "9 of 10")
        mock_answer.assert_not_called()

    def test_enrollments_question_never_calls_llm(self):
        Enrollment.objects.create(student=self.student, subject=self.subject)
        response, mock_answer = self._ask_with_mocked_llm("What am I enrolled in?")
        self.assertContains(response, "CS101")
        mock_answer.assert_not_called()

    def test_semester_plan_question_never_calls_llm(self):
        plan = SemesterPlan.objects.create(student=self.student, semester=1)
        plan.subjects.add(self.subject)
        response, mock_answer = self._ask_with_mocked_llm("What's my semester plan?")
        self.assertContains(response, "CS101")
        mock_answer.assert_not_called()

    def test_deadline_question_never_calls_llm(self):
        AdmissionDeadline.objects.create(
            program=self.program,
            label="Fall Closing",
            date=timezone.localdate() + datetime.timedelta(days=5),
        )
        response, mock_answer = self._ask_with_mocked_llm("When's the next deadline?")
        self.assertContains(response, "Fall Closing")
        mock_answer.assert_not_called()

    def test_program_subjects_question_never_calls_llm(self):
        response, mock_answer = self._ask_with_mocked_llm("What subjects are in my program?")
        self.assertContains(response, "CS101")
        mock_answer.assert_not_called()

    def test_program_question_never_calls_llm(self):
        response, mock_answer = self._ask_with_mocked_llm("What's my program?")
        self.assertContains(response, "Computer Science")
        mock_answer.assert_not_called()

    def test_department_question_never_calls_llm(self):
        response, mock_answer = self._ask_with_mocked_llm("Who's my department?")
        self.assertContains(response, "Computer Science Department")
        mock_answer.assert_not_called()

    def test_registration_no_question_never_calls_llm(self):
        response, mock_answer = self._ask_with_mocked_llm("What's my registration number?")
        self.assertContains(response, "REG-1")
        mock_answer.assert_not_called()

    def test_current_semester_question_never_calls_llm(self):
        Enrollment.objects.create(student=self.student, subject=self.subject)
        response, mock_answer = self._ask_with_mocked_llm("What semester am I in?")
        self.assertContains(response, "semester 1")
        mock_answer.assert_not_called()

    def test_general_question_routes_to_rag_with_student_and_no_personal_context(self):
        # Not personal in nature - the LLM call is still scoped to this
        # student's session (for the non-training client gate), but
        # include_personal_context is False so no student record is injected.
        with patch("apps.portal.views.answering.answer_question") as mock_answer:
            mock_answer.return_value = Answer(
                text="We offer many programs.", sources=[], grounded=True
            )
            response = self.client.post(
                reverse("portal:ask"), {"question": "What programs does the university offer?"}
            )
        mock_answer.assert_called_once_with(
            question="What programs does the university offer?",
            student=self.student,
            include_personal_context=False,
        )
        self.assertContains(response, "We offer many programs.")

    def test_personal_but_router_missed_question_still_gets_personal_context(self):
        # "Which scholarships am I eligible for?" doesn't match any of the
        # specific template buckets in apps/portal/intents.py (no selector
        # can answer eligibility directly), but it IS personal ("I") - it
        # must still reach answer_question with include_personal_context=True,
        # not be silently treated as generic.
        with patch("apps.portal.views.answering.answer_question") as mock_answer:
            mock_answer.return_value = Answer(
                text="Based on your program, you may qualify for the CS Merit Award.",
                sources=[],
                grounded=True,
            )
            response = self.client.post(
                reverse("portal:ask"), {"question": "Which scholarships am I eligible for?"}
            )
        mock_answer.assert_called_once_with(
            question="Which scholarships am I eligible for?",
            student=self.student,
            include_personal_context=True,
        )
        self.assertContains(response, "CS Merit Award")

    def test_answer_fragment_has_visually_hidden_speaker_labels(self):
        # Question/answer are only distinguished by CSS alignment/color -
        # a screen-reader user needs a textual cue to tell them apart.
        FeeStatus.objects.create(
            student=self.student, semester=1, amount_due="50000.00", amount_paid="50000.00"
        )
        response, _ = self._ask_with_mocked_llm("What's my fee balance?")
        self.assertContains(response, '<span class="sr-only">You asked: </span>')
        self.assertContains(response, '<span class="sr-only">Assistant: </span>')

    def test_off_topic_question_gets_honest_fallback(self):
        # Not personal in nature (see is_personal_question) and no documents
        # are seeded, so this hits the deterministic pre-LLM early return in
        # answer_question - no LLM client is even constructed.
        response = self.client.post(
            reverse("portal:ask"), {"question": "What's the weather like today?"}
        )
        self.assertEqual(response.status_code, 200)
        # Not html=True: I_DONT_KNOW now sits as inline tail text next to a
        # sibling <span> (the sr-only speaker label) rather than being a
        # paragraph's sole content, which Django's html-tree containment
        # check doesn't reliably match - compare the escaped text directly.
        self.assertContains(response, escape(I_DONT_KNOW))

    def test_personal_but_ungrounded_question_declines_via_the_llm(self):
        # "What's my favorite color?" IS personal (router miss, but matches
        # is_personal_question), so it reaches the real LLM with the
        # student's record attached - but nothing in that record answers it.
        # A real model is expected to decline per SYSTEM_PROMPT; this proves
        # that decline is correctly surfaced as the honest fallback rather
        # than a fabricated answer, using a stub scripted to decline (an
        # echoing stub could never produce this case - see StubLLMClient).
        from apps.assistant.clients.llm import StubLLMClient

        with patch(
            "apps.assistant.clients.get_llm_client", return_value=StubLLMClient(decline=True)
        ):
            response = self.client.post(
                reverse("portal:ask"), {"question": "What's my favorite color?"}
            )
        self.assertEqual(response.status_code, 200)
        # Not html=True: I_DONT_KNOW now sits as inline tail text next to a
        # sibling <span> (the sr-only speaker label) rather than being a
        # paragraph's sole content, which Django's html-tree containment
        # check doesn't reliably match - compare the escaped text directly.
        self.assertContains(response, escape(I_DONT_KNOW))
