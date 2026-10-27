from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.academics.models import Attendance, Course, Department, Enrollment, Program, Subject
from apps.academics.services import enroll_student, record_attendance
from apps.accounts.models import StudentProfile, User


class EnrollStudentTests(TestCase):
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

    def test_enroll_student_creates_enrollment(self):
        enrollment = enroll_student(student=self.student, subject=self.subject)
        self.assertEqual(enrollment.student, self.student)
        self.assertEqual(enrollment.subject, self.subject)

    def test_enroll_student_duplicate_rejected(self):
        enroll_student(student=self.student, subject=self.subject)
        with self.assertRaises(ValidationError):
            enroll_student(student=self.student, subject=self.subject)
        self.assertEqual(
            Enrollment.objects.filter(student=self.student, subject=self.subject).count(), 1
        )

    def test_enroll_student_race_condition_raises_validation_error_not_integrity_error(self):
        # Simulates two near-simultaneous enroll requests: a row already
        # exists (the "other" request won), but this call's .exists() check
        # is forced to miss it (the race window) so .create() hits the real
        # DB unique constraint - the service must convert that IntegrityError
        # into the same ValidationError a caught-early duplicate raises,
        # not let it propagate raw.
        Enrollment.objects.create(student=self.student, subject=self.subject)
        with patch("apps.academics.services.Enrollment.objects.filter") as mock_filter:
            mock_filter.return_value.exists.return_value = False
            with self.assertRaises(ValidationError):
                enroll_student(student=self.student, subject=self.subject)
        self.assertEqual(
            Enrollment.objects.filter(student=self.student, subject=self.subject).count(), 1
        )


class RecordAttendanceTests(TestCase):
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

    def test_record_attendance_creates_record(self):
        attendance = record_attendance(
            enrollment=self.enrollment, date="2026-07-01", status=Attendance.Status.PRESENT
        )
        self.assertEqual(attendance.status, Attendance.Status.PRESENT)

    def test_record_attendance_updates_existing_record_for_same_date(self):
        record_attendance(
            enrollment=self.enrollment, date="2026-07-01", status=Attendance.Status.PRESENT
        )
        record_attendance(
            enrollment=self.enrollment, date="2026-07-01", status=Attendance.Status.ABSENT
        )
        self.assertEqual(
            Attendance.objects.filter(enrollment=self.enrollment, date="2026-07-01").count(), 1
        )
        attendance = Attendance.objects.get(enrollment=self.enrollment, date="2026-07-01")
        self.assertEqual(attendance.status, Attendance.Status.ABSENT)
