from decimal import Decimal

from django.test import TestCase

from apps.academics.models import Department, Program
from apps.accounts.models import StudentProfile, User
from apps.finance import selectors
from apps.finance.models import FeeStatus, FeeStructure


class FeeStructureSelectorTests(TestCase):
    def setUp(self):
        department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.cs = Program.objects.create(department=department, code="CS", name="Computer Science")
        self.se = Program.objects.create(department=department, code="SE", name="Software Engineering")
        self.cs_structure = FeeStructure.objects.create(program=self.cs, semester=1, amount="50000.00")
        self.se_structure = FeeStructure.objects.create(program=self.se, semester=1, amount="45000.00")

    def test_list_fee_structures_unfiltered_returns_all(self):
        self.assertEqual(selectors.list_fee_structures().count(), 2)

    def test_list_fee_structures_filtered_by_program(self):
        result = selectors.list_fee_structures(program_code="CS")
        self.assertEqual(list(result), [self.cs_structure])


class FeeStatusSelectorTests(TestCase):
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

    def test_list_student_fee_statuses_returns_only_that_students_records(self):
        result = selectors.list_student_fee_statuses(student=self.student_a)
        self.assertEqual(list(result), [self.fee_a])

    def test_list_fee_statuses_returns_all_for_admin(self):
        self.assertEqual(selectors.list_fee_statuses().count(), 2)


class FeeStatusMathTests(TestCase):
    def setUp(self):
        department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=department, code="CS", name="Computer Science"
        )
        user = User.objects.create_user(username="stu", password="pw")
        self.student = StudentProfile.objects.create(
            user=user, registration_no="REG-1", program=self.program
        )

    def test_fee_status_outstanding_computes_due_minus_paid(self):
        FeeStatus.objects.create(
            student=self.student, semester=1, amount_due="50000.00", amount_paid="20000.00"
        )
        # Re-fetch rather than use the .create() return value directly: a
        # DecimalField assigned a raw string via .create() keeps that string
        # in memory until reloaded from the DB, which is how every real
        # caller of this function (selector-returned querysets) gets it.
        fee_status = FeeStatus.objects.get(student=self.student, semester=1)
        self.assertEqual(selectors.fee_status_outstanding(fee_status), Decimal("30000.00"))

    def test_is_fee_status_settled_true_only_when_paid(self):
        paid = FeeStatus.objects.create(
            student=self.student,
            semester=1,
            amount_due="50000.00",
            amount_paid="50000.00",
            status=FeeStatus.Status.PAID,
        )
        partial = FeeStatus.objects.create(
            student=self.student,
            semester=2,
            amount_due="50000.00",
            amount_paid="20000.00",
            status=FeeStatus.Status.PARTIAL,
        )
        self.assertTrue(selectors.is_fee_status_settled(paid))
        self.assertFalse(selectors.is_fee_status_settled(partial))
