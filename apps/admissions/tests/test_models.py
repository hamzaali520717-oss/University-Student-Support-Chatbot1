from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.academics.models import Department, Program
from apps.admissions.models import AdmissionDeadline, AdmissionRequirement, Scholarship


class AdmissionsUniqueConstraintTests(TestCase):
    def setUp(self):
        department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=department, code="CS", name="Computer Science"
        )

    def test_requirement_unique_per_program_title(self):
        AdmissionRequirement.objects.create(
            program=self.program, title="Minimum CGPA", description="At least 3.0/4.0"
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            AdmissionRequirement.objects.create(
                program=self.program, title="Minimum CGPA", description="Different text"
            )

    def test_deadline_unique_per_program_label_date(self):
        AdmissionDeadline.objects.create(
            program=self.program, label="Fall Application Deadline", date="2026-08-01"
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            AdmissionDeadline.objects.create(
                program=self.program, label="Fall Application Deadline", date="2026-08-01"
            )

    def test_scholarship_unique_name(self):
        Scholarship.objects.create(name="Merit Scholarship", description="Top scorers")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Scholarship.objects.create(name="Merit Scholarship", description="Duplicate")
