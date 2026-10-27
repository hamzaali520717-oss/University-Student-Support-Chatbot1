from django.test import TestCase

from apps.academics.models import Department, Program
from apps.accounts.models import StudentProfile, User
from apps.finance import services
from apps.finance.models import FeeStatus, FeeStructure


class FeeStructureServiceTests(TestCase):
    def setUp(self):
        department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=department, code="CS", name="Computer Science"
        )

    def test_create_fee_structure(self):
        structure = services.create_fee_structure(program=self.program, semester=1, amount="50000.00")
        self.assertTrue(FeeStructure.objects.filter(id=structure.id).exists())

    def test_update_fee_structure(self):
        structure = services.create_fee_structure(program=self.program, semester=1, amount="50000.00")
        updated = services.update_fee_structure(fee_structure=structure, amount="55000.00")
        self.assertEqual(str(updated.amount), "55000.00")

    def test_delete_fee_structure(self):
        structure = services.create_fee_structure(program=self.program, semester=1, amount="50000.00")
        services.delete_fee_structure(fee_structure=structure)
        self.assertFalse(FeeStructure.objects.filter(id=structure.id).exists())


class FeeStatusServiceTests(TestCase):
    def setUp(self):
        department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=department, code="CS", name="Computer Science"
        )
        user = User.objects.create_user(username="stu", password="pw")
        self.student = StudentProfile.objects.create(
            user=user, registration_no="REG-1", program=self.program
        )

    def test_create_fee_status_defaults_to_unpaid(self):
        fee_status = services.create_fee_status(
            student=self.student, semester=1, amount_due="50000.00"
        )
        self.assertEqual(fee_status.status, FeeStatus.Status.UNPAID)

    def test_record_partial_payment_sets_partial_status(self):
        fee_status = services.create_fee_status(
            student=self.student, semester=1, amount_due="50000.00"
        )
        updated = services.record_payment(fee_status=fee_status, amount="20000.00")
        self.assertEqual(str(updated.amount_paid), "20000.00")
        self.assertEqual(updated.status, FeeStatus.Status.PARTIAL)

    def test_record_full_payment_sets_paid_status(self):
        fee_status = services.create_fee_status(
            student=self.student, semester=1, amount_due="50000.00"
        )
        updated = services.record_payment(fee_status=fee_status, amount="50000.00")
        self.assertEqual(updated.status, FeeStatus.Status.PAID)

    def test_record_payment_accumulates_across_calls(self):
        fee_status = services.create_fee_status(
            student=self.student, semester=1, amount_due="50000.00"
        )
        services.record_payment(fee_status=fee_status, amount="20000.00")
        updated = services.record_payment(fee_status=fee_status, amount="30000.00")
        self.assertEqual(str(updated.amount_paid), "50000.00")
        self.assertEqual(updated.status, FeeStatus.Status.PAID)

    def test_update_fee_status_generic_fields(self):
        fee_status = services.create_fee_status(
            student=self.student, semester=1, amount_due="50000.00"
        )
        updated = services.update_fee_status(fee_status=fee_status, amount_due="60000.00")
        self.assertEqual(str(updated.amount_due), "60000.00")
