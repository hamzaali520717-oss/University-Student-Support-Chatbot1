from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.academics.models import Department, Program
from apps.accounts.models import StudentProfile, User
from apps.finance.models import FeeStatus, FeeStructure


class FinanceUniqueConstraintTests(TestCase):
    def setUp(self):
        department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=department, code="CS", name="Computer Science"
        )
        user = User.objects.create_user(username="stu", password="pw")
        self.student = StudentProfile.objects.create(
            user=user, registration_no="REG-1", program=self.program
        )

    def test_fee_structure_unique_per_program_semester(self):
        FeeStructure.objects.create(program=self.program, semester=1, amount="50000.00")
        with self.assertRaises(IntegrityError), transaction.atomic():
            FeeStructure.objects.create(program=self.program, semester=1, amount="60000.00")

    def test_fee_status_unique_per_student_semester(self):
        FeeStatus.objects.create(student=self.student, semester=1, amount_due="50000.00")
        with self.assertRaises(IntegrityError), transaction.atomic():
            FeeStatus.objects.create(student=self.student, semester=1, amount_due="60000.00")
