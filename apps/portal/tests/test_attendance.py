from django.urls import reverse

from apps.academics.models import Attendance, Enrollment
from apps.accounts.models import StudentProfile, User
from apps.portal.tests.base import PortalTestCase


class AttendanceViewTests(PortalTestCase):
    def test_no_cross_student_leakage(self):
        other_user = User.objects.create_user(username="student2", password="pw", role=User.Role.STUDENT)
        other_student = StudentProfile.objects.create(
            user=other_user, registration_no="REG-2", program=self.program
        )
        my_enrollment = Enrollment.objects.create(student=self.student, subject=self.subject)
        other_enrollment = Enrollment.objects.create(student=other_student, subject=self.subject)
        Attendance.objects.create(
            enrollment=my_enrollment, date="2026-01-01", status=Attendance.Status.PRESENT
        )
        Attendance.objects.create(
            enrollment=other_enrollment, date="2026-01-01", status=Attendance.Status.PRESENT
        )

        self.login_student()
        response = self.client.get(reverse("portal:attendance"))
        self.assertEqual(len(response.context["attendance_records"]), 1)

    def test_subject_filter(self):
        enrollment = Enrollment.objects.create(student=self.student, subject=self.subject)
        other_subject = self.make_subject(code="CS102")
        other_enrollment = Enrollment.objects.create(student=self.student, subject=other_subject)
        Attendance.objects.create(
            enrollment=enrollment, date="2026-01-01", status=Attendance.Status.PRESENT
        )
        Attendance.objects.create(
            enrollment=other_enrollment, date="2026-01-02", status=Attendance.Status.PRESENT
        )

        self.login_student()
        response = self.client.get(reverse("portal:attendance"), {"subject": self.subject.id})
        self.assertEqual(len(response.context["attendance_records"]), 1)

    def test_non_numeric_subject_param_does_not_500(self):
        self.login_student()
        response = self.client.get(reverse("portal:attendance"), {"subject": "abc"})
        self.assertEqual(response.status_code, 200)
