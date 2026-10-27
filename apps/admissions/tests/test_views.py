import datetime

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.academics.models import Department, Program
from apps.accounts.models import User
from apps.admissions.models import AdmissionDeadline, AdmissionRequirement, Scholarship


class PublicReadTests(APITestCase):
    def setUp(self):
        department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=department, code="CS", name="Computer Science"
        )
        self.requirement = AdmissionRequirement.objects.create(
            program=self.program, title="Minimum CGPA", description="At least 3.0/4.0"
        )
        self.today = timezone.localdate()
        self.upcoming_deadline = AdmissionDeadline.objects.create(
            program=self.program, label="Upcoming Deadline", date=self.today + datetime.timedelta(days=10)
        )
        AdmissionDeadline.objects.create(
            program=self.program, label="Past Deadline", date=self.today - datetime.timedelta(days=10)
        )
        self.active_scholarship = Scholarship.objects.create(
            name="Merit Scholarship", description="Top scorers", is_active=True
        )
        Scholarship.objects.create(
            name="Discontinued Grant", description="No longer offered", is_active=False
        )

    def test_requirements_reachable_unauthenticated(self):
        response = self.client.get(reverse("requirement-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_deadlines_reachable_unauthenticated_and_only_upcoming(self):
        response = self.client.get(reverse("deadline-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["label"], self.upcoming_deadline.label)

    def test_scholarships_reachable_unauthenticated_and_only_active(self):
        response = self.client.get(reverse("scholarship-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], self.active_scholarship.name)

    def test_anonymous_cannot_create_requirement(self):
        response = self.client.post(
            reverse("requirement-list"),
            {"program": self.program.code, "title": "Interview", "description": "Pass an interview"},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_student_cannot_create_scholarship(self):
        student = User.objects.create_user(username="stu", password="pw", role=User.Role.STUDENT)
        self.client.force_authenticate(user=student)
        response = self.client.post(
            reverse("scholarship-list"), {"name": "New Scholarship", "description": "desc"}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminWriteTests(APITestCase):
    def setUp(self):
        department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=department, code="CS", name="Computer Science"
        )
        self.admin = User.objects.create_user(username="admin", password="pw", role=User.Role.ADMIN)
        self.client.force_authenticate(user=self.admin)

    def test_admin_can_create_requirement(self):
        response = self.client.post(
            reverse("requirement-list"),
            {"program": self.program.code, "title": "Interview", "description": "Pass an interview"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(AdmissionRequirement.objects.filter(title="Interview").exists())

    def test_admin_can_update_and_delete_requirement(self):
        requirement = AdmissionRequirement.objects.create(
            program=self.program, title="Minimum CGPA", description="At least 3.0/4.0"
        )
        url = reverse("requirement-detail", args=[requirement.id])
        response = self.client.patch(url, {"description": "At least 3.3/4.0"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        requirement.refresh_from_db()
        self.assertEqual(requirement.description, "At least 3.3/4.0")

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(AdmissionRequirement.objects.filter(id=requirement.id).exists())

    def test_admin_can_create_deadline(self):
        response = self.client.post(
            reverse("deadline-list"),
            {"program": self.program.code, "label": "Fall Deadline", "date": "2026-08-01"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(AdmissionDeadline.objects.filter(label="Fall Deadline").exists())

    def test_admin_can_create_and_deactivate_scholarship(self):
        response = self.client.post(
            reverse("scholarship-list"),
            {"name": "New Scholarship", "description": "desc", "amount": "10000.00"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        scholarship = Scholarship.objects.get(name="New Scholarship")

        url = reverse("scholarship-detail", args=[scholarship.id])
        response = self.client.patch(url, {"is_active": False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        scholarship.refresh_from_db()
        self.assertFalse(scholarship.is_active)
