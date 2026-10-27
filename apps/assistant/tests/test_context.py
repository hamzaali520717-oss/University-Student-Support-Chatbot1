from django.test import TestCase

from apps.academics.models import Attendance, Course, Department, Enrollment, Program, Subject
from apps.accounts.models import StudentProfile, User
from apps.assistant import services
from apps.finance.models import FeeStatus


class BuildStudentContextTests(TestCase):
    def setUp(self):
        department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        program = Program.objects.create(department=department, code="CS", name="Computer Science")
        course = Course.objects.create(department=department, code="CS101", title="Intro to CS")
        subject = Subject.objects.create(program=program, course=course, semester=1, credit_hours=3)

        user_a = User.objects.create_user(username="stu-a", password="pw")
        self.student_a = StudentProfile.objects.create(
            user=user_a, registration_no="REG-A", program=program
        )
        enrollment_a = Enrollment.objects.create(student=self.student_a, subject=subject)
        Attendance.objects.create(enrollment=enrollment_a, date="2026-01-05", status="present")
        FeeStatus.objects.create(student=self.student_a, semester=1, amount_due="50000.00")

        user_b = User.objects.create_user(username="stu-b", password="pw")
        self.student_b = StudentProfile.objects.create(
            user=user_b, registration_no="REG-B", program=program
        )
        enrollment_b = Enrollment.objects.create(student=self.student_b, subject=subject)
        Attendance.objects.create(enrollment=enrollment_b, date="2026-01-05", status="absent")
        FeeStatus.objects.create(student=self.student_b, semester=1, amount_due="99999.00")

    def test_context_includes_own_records(self):
        context = services.build_student_context(student=self.student_a)
        self.assertIn("REG-A", context.text)
        self.assertIn("CS101", context.text)
        self.assertIn("50000.00", context.text)

    def test_context_never_includes_another_students_records(self):
        context = services.build_student_context(student=self.student_a)
        self.assertNotIn("REG-B", context.text)
        self.assertNotIn("99999.00", context.text)

    def test_context_is_symmetric_for_the_other_student(self):
        context = services.build_student_context(student=self.student_b)
        self.assertIn("REG-B", context.text)
        self.assertNotIn("REG-A", context.text)
        self.assertNotIn("50000.00", context.text)
