from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.academics.models import Attendance, Course, Department, Enrollment, Program, Subject
from apps.accounts.models import StudentProfile, User


class PublicCatalogTests(APITestCase):
    def setUp(self):
        self.department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=self.department, code="CS", name="Computer Science"
        )
        self.course = Course.objects.create(
            department=self.department, code="CS101", title="Intro to Programming"
        )
        Subject.objects.create(program=self.program, course=self.course, semester=1, credit_hours=3)

    def test_programs_reachable_unauthenticated(self):
        response = self.client.get(reverse("program-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_courses_reachable_unauthenticated(self):
        response = self.client.get(reverse("course-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_subjects_reachable_unauthenticated(self):
        response = self.client.get(reverse("subject-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_subjects_filtered_by_unknown_program_returns_empty(self):
        response = self.client.get(reverse("subject-list"), {"program": "SE"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)


class StudentScopedAccessTests(APITestCase):
    def setUp(self):
        self.department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=self.department, code="CS", name="Computer Science"
        )

    def test_my_enrollments_rejects_anonymous(self):
        response = self.client.get(reverse("my-enrollments"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_my_enrollments_rejects_admin(self):
        admin = User.objects.create_user(username="adm", password="pw", role=User.Role.ADMIN)
        self.client.force_authenticate(user=admin)
        response = self.client.get(reverse("my-enrollments"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class MyEnrollmentTests(APITestCase):
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
        self.client.force_authenticate(user=user)

    def test_enroll_success(self):
        response = self.client.post(reverse("my-enrollments"), {"subject": self.subject.id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Enrollment.objects.filter(student=self.student, subject=self.subject).exists()
        )

    def test_enroll_duplicate_rejected(self):
        self.client.post(reverse("my-enrollments"), {"subject": self.subject.id})
        response = self.client.post(reverse("my-enrollments"), {"subject": self.subject.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            Enrollment.objects.filter(student=self.student, subject=self.subject).count(), 1
        )

    def test_list_returns_only_own_enrollments(self):
        other_user = User.objects.create_user(username="other", password="pw")
        other_student = StudentProfile.objects.create(
            user=other_user, registration_no="REG-2", program=self.program
        )
        Enrollment.objects.create(student=other_student, subject=self.subject)
        Enrollment.objects.create(student=self.student, subject=self.subject)

        response = self.client.get(reverse("my-enrollments"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)


class MyAttendanceAndPlanScopingTests(APITestCase):
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
        other_user = User.objects.create_user(username="other", password="pw")
        self.other_student = StudentProfile.objects.create(
            user=other_user, registration_no="REG-2", program=self.program
        )

        self.enrollment = Enrollment.objects.create(student=self.student, subject=self.subject)
        other_enrollment = Enrollment.objects.create(student=self.other_student, subject=self.subject)
        Attendance.objects.create(enrollment=self.enrollment, date="2026-07-01")
        Attendance.objects.create(enrollment=other_enrollment, date="2026-07-01")

        self.client.force_authenticate(user=user)

    def test_my_attendance_does_not_leak_other_students(self):
        response = self.client.get(reverse("my-attendance"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_my_plan_does_not_leak_other_students(self):
        self.student.semester_plans.create(semester=1)
        self.other_student.semester_plans.create(semester=1)

        response = self.client.get(reverse("my-plan"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
