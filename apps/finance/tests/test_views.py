from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.academics.models import Department, Program
from apps.accounts.models import StudentProfile, User
from apps.finance.models import FeeStatus, FeeStructure


class PublicFeeStructureTests(APITestCase):
    def setUp(self):
        department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=department, code="CS", name="Computer Science"
        )
        self.structure = FeeStructure.objects.create(
            program=self.program, semester=1, amount="50000.00"
        )

    def test_structures_reachable_unauthenticated(self):
        response = self.client.get(reverse("structure-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_structures_filtered_by_program(self):
        response = self.client.get(reverse("structure-list"), {"program": "SE"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)

    def test_anonymous_cannot_create_structure(self):
        response = self.client.post(
            reverse("structure-list"), {"program": "CS", "semester": 2, "amount": "51000.00"}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_student_cannot_create_structure(self):
        user = User.objects.create_user(username="stu", password="pw", role=User.Role.STUDENT)
        self.client.force_authenticate(user=user)
        response = self.client.post(
            reverse("structure-list"), {"program": "CS", "semester": 2, "amount": "51000.00"}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_and_update_structure(self):
        admin = User.objects.create_user(username="admin", password="pw", role=User.Role.ADMIN)
        self.client.force_authenticate(user=admin)
        response = self.client.post(
            reverse("structure-list"), {"program": "CS", "semester": 2, "amount": "51000.00"}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        url = reverse("structure-detail", args=[self.structure.id])
        response = self.client.patch(url, {"amount": "52000.00"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.structure.refresh_from_db()
        self.assertEqual(str(self.structure.amount), "52000.00")


class MyFeeStatusScopingTests(APITestCase):
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
        self.fee_a = FeeStatus.objects.create(
            student=self.student_a, semester=1, amount_due="50000.00"
        )
        self.fee_b = FeeStatus.objects.create(
            student=self.student_b, semester=1, amount_due="50000.00"
        )

    def test_my_fees_rejects_anonymous(self):
        response = self.client.get(reverse("my-fees"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_my_fees_list_does_not_leak_other_students(self):
        self.client.force_authenticate(user=self.student_a.user)
        response = self.client.get(reverse("my-fees"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.fee_a.id)

    def test_student_a_can_read_own_fee_detail(self):
        self.client.force_authenticate(user=self.student_a.user)
        response = self.client.get(reverse("my-fee-detail", args=[self.fee_a.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.fee_a.id)

    def test_student_a_cannot_read_student_b_fee_detail(self):
        self.client.force_authenticate(user=self.student_a.user)
        response = self.client.get(reverse("my-fee-detail", args=[self.fee_b.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_cannot_use_student_scoped_endpoint(self):
        admin = User.objects.create_user(username="admin", password="pw", role=User.Role.ADMIN)
        self.client.force_authenticate(user=admin)
        response = self.client.get(reverse("my-fees"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminFeeStatusTests(APITestCase):
    def setUp(self):
        department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=department, code="CS", name="Computer Science"
        )
        user = User.objects.create_user(username="stu", password="pw")
        self.student = StudentProfile.objects.create(
            user=user, registration_no="REG-1", program=self.program
        )
        self.admin = User.objects.create_user(username="admin", password="pw", role=User.Role.ADMIN)
        self.client.force_authenticate(user=self.admin)

    def test_anonymous_and_student_cannot_list_all_statuses(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("status-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(user=self.student.user)
        response = self.client.get(reverse("status-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_fee_status(self):
        response = self.client.post(
            reverse("status-list"),
            {"student": "REG-1", "semester": 1, "amount_due": "50000.00"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(FeeStatus.objects.filter(student=self.student, semester=1).exists())

    def test_admin_can_record_payment(self):
        fee_status = FeeStatus.objects.create(
            student=self.student, semester=1, amount_due="50000.00"
        )
        url = reverse("status-record-payment", args=[fee_status.id])
        response = self.client.post(url, {"amount": "50000.00"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        fee_status.refresh_from_db()
        self.assertEqual(fee_status.status, FeeStatus.Status.PAID)
        self.assertEqual(str(fee_status.amount_paid), "50000.00")

    def test_student_cannot_record_payment(self):
        fee_status = FeeStatus.objects.create(
            student=self.student, semester=1, amount_due="50000.00"
        )
        self.client.force_authenticate(user=self.student.user)
        url = reverse("status-record-payment", args=[fee_status.id])
        response = self.client.post(url, {"amount": "10000.00"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
