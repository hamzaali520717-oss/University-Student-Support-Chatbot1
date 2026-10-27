from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.academics.models import (
    Attendance,
    Course,
    Department,
    Enrollment,
    Program,
    SemesterPlan,
    Subject,
)
from apps.accounts.models import StudentProfile, User


class AcademicsUniqueConstraintTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=self.department, code="CS", name="Computer Science"
        )
        self.course = Course.objects.create(
            department=self.department, code="CS101", title="Intro to Programming"
        )
        self.subject = Subject.objects.create(
            program=self.program, course=self.course, semester=1, credit_hours=3
        )
        user = User.objects.create_user(username="stu", password="pw")
        self.student = StudentProfile.objects.create(
            user=user, registration_no="REG-1", program=self.program
        )
        self.enrollment = Enrollment.objects.create(student=self.student, subject=self.subject)

    def test_subject_unique_per_program_course_semester(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Subject.objects.create(
                program=self.program, course=self.course, semester=1, credit_hours=4
            )

    def test_enrollment_unique_per_student_subject(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Enrollment.objects.create(student=self.student, subject=self.subject)

    def test_semester_plan_unique_per_student_semester(self):
        SemesterPlan.objects.create(student=self.student, semester=1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            SemesterPlan.objects.create(student=self.student, semester=1)

    def test_attendance_unique_per_enrollment_date(self):
        Attendance.objects.create(enrollment=self.enrollment, date="2026-07-01")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Attendance.objects.create(enrollment=self.enrollment, date="2026-07-01")
