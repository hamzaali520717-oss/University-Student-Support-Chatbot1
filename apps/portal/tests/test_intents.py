import datetime

from django.test import SimpleTestCase
from django.utils import timezone

from apps.academics.models import Enrollment, SemesterPlan
from apps.admissions.models import AdmissionDeadline
from apps.finance.models import FeeStatus
from apps.portal import intents
from apps.portal.tests.base import PortalTestCase


class DetectIntentTests(SimpleTestCase):
    def test_fees_keyword(self):
        self.assertEqual(intents.detect_intent("What's my fee balance?"), "fees")

    def test_attendance_keyword(self):
        self.assertEqual(intents.detect_intent("How many classes did I miss?"), "attendance")

    def test_enrollments_keyword(self):
        self.assertEqual(intents.detect_intent("What am I enrolled in?"), "enrollments")

    def test_semester_plan_keyword(self):
        self.assertEqual(intents.detect_intent("What's my semester plan?"), "semester_plan")

    def test_deadline_keyword(self):
        self.assertEqual(intents.detect_intent("When's the next deadline?"), "deadline")

    def test_general_question_returns_none(self):
        self.assertIsNone(intents.detect_intent("What programs does the university offer?"))

    def test_program_subjects_keyword(self):
        self.assertEqual(
            intents.detect_intent("What subjects are in my program?"), "program_subjects"
        )

    def test_program_subjects_not_confused_with_enrollments_or_program(self):
        # Shares vocabulary ("my program", "subjects") with both buckets but
        # must resolve to the more specific program_subjects intent.
        for question in [
            "What courses are in my program?",
            "What's the curriculum for my program?",
        ]:
            with self.subTest(question=question):
                self.assertEqual(intents.detect_intent(question), "program_subjects")

    def test_program_keyword(self):
        self.assertEqual(intents.detect_intent("What's my program?"), "program")

    def test_department_keyword(self):
        self.assertEqual(intents.detect_intent("Who's my department?"), "department")

    def test_registration_no_keyword(self):
        self.assertEqual(
            intents.detect_intent("What's my registration number?"), "registration_no"
        )

    def test_current_semester_keyword(self):
        self.assertEqual(intents.detect_intent("What semester am I in?"), "current_semester")

    def test_scholarship_eligibility_has_no_matching_intent(self):
        # Personal in wording (is_personal_question would catch "I"), but no
        # selector can answer it directly - this must fall through to the
        # general RAG path, not a template, which is correct and expected.
        self.assertIsNone(intents.detect_intent("Which scholarships am I eligible for?"))


class AnswerPersonalIntentTests(PortalTestCase):
    def test_fees_empty_state(self):
        answer = intents.answer_personal_intent(intent="fees", student=self.student)
        self.assertIn("don't have any fee records", answer.text)
        self.assertEqual(answer.sources, [])
        self.assertTrue(answer.grounded)

    def test_fees_outstanding_balance(self):
        FeeStatus.objects.create(
            student=self.student,
            semester=1,
            amount_due="50000.00",
            amount_paid="20000.00",
            status=FeeStatus.Status.PARTIAL,
        )
        answer = intents.answer_personal_intent(intent="fees", student=self.student)
        self.assertIn("30,000", answer.text)

    def test_fees_all_paid(self):
        FeeStatus.objects.create(
            student=self.student,
            semester=1,
            amount_due="50000.00",
            amount_paid="50000.00",
            status=FeeStatus.Status.PAID,
        )
        answer = intents.answer_personal_intent(intent="fees", student=self.student)
        self.assertIn("no outstanding fees", answer.text)

    def test_attendance_empty_state(self):
        answer = intents.answer_personal_intent(intent="attendance", student=self.student)
        self.assertIn("don't have any attendance records", answer.text)

    def test_attendance_rate(self):
        enrollment = Enrollment.objects.create(student=self.student, subject=self.subject)
        self.seed_attendance(enrollment, present_count=9, total_count=10)
        answer = intents.answer_personal_intent(intent="attendance", student=self.student)
        self.assertIn("9 of 10", answer.text)
        self.assertIn("90%", answer.text)

    def test_enrollments_empty_state(self):
        answer = intents.answer_personal_intent(intent="enrollments", student=self.student)
        self.assertIn("not enrolled", answer.text)

    def test_enrollments_lists_subjects(self):
        Enrollment.objects.create(student=self.student, subject=self.subject)
        answer = intents.answer_personal_intent(intent="enrollments", student=self.student)
        self.assertIn("CS101", answer.text)

    def test_semester_plan_empty_state(self):
        answer = intents.answer_personal_intent(intent="semester_plan", student=self.student)
        self.assertIn("don't have a semester plan", answer.text)

    def test_semester_plan_lists_subjects(self):
        plan = SemesterPlan.objects.create(student=self.student, semester=1)
        plan.subjects.add(self.subject)
        answer = intents.answer_personal_intent(intent="semester_plan", student=self.student)
        self.assertIn("CS101", answer.text)

    def test_deadline_empty_state(self):
        answer = intents.answer_personal_intent(intent="deadline", student=self.student)
        self.assertIn("no upcoming deadlines", answer.text)

    def test_deadline_returns_nearest(self):
        AdmissionDeadline.objects.create(
            program=self.program,
            label="Fall Closing",
            date=timezone.localdate() + datetime.timedelta(days=10),
        )
        answer = intents.answer_personal_intent(intent="deadline", student=self.student)
        self.assertIn("Fall Closing", answer.text)

    def test_program_subjects_empty_state(self):
        # self.program has no Subjects beyond self.subject seeded by
        # PortalTestCase - use a fresh program with none at all.
        from apps.academics.models import Department, Program

        department = Department.objects.create(code="EE-DEPT", name="Electrical Engineering Dept")
        program = Program.objects.create(
            department=department, code="EE", name="Electrical Engineering"
        )
        self.student.program = program
        self.student.save()

        answer = intents.answer_personal_intent(intent="program_subjects", student=self.student)
        self.assertIn("No subjects are on record", answer.text)

    def test_program_subjects_lists_curriculum(self):
        answer = intents.answer_personal_intent(intent="program_subjects", student=self.student)
        self.assertIn("CS101", answer.text)
        self.assertIn("Computer Science", answer.text)

    def test_program_answer(self):
        answer = intents.answer_personal_intent(intent="program", student=self.student)
        self.assertIn("Computer Science", answer.text)
        self.assertIn("CS", answer.text)

    def test_department_answer(self):
        answer = intents.answer_personal_intent(intent="department", student=self.student)
        self.assertIn("Computer Science Department", answer.text)

    def test_registration_no_answer(self):
        answer = intents.answer_personal_intent(intent="registration_no", student=self.student)
        self.assertIn("REG-1", answer.text)

    def test_current_semester_empty_state(self):
        answer = intents.answer_personal_intent(intent="current_semester", student=self.student)
        self.assertIn("don't have any enrollments yet", answer.text)

    def test_current_semester_from_highest_enrollment(self):
        other_subject = self.make_subject(code="CS201", semester=3)
        Enrollment.objects.create(student=self.student, subject=self.subject)
        Enrollment.objects.create(student=self.student, subject=other_subject)

        answer = intents.answer_personal_intent(intent="current_semester", student=self.student)
        self.assertIn("semester 3", answer.text)
