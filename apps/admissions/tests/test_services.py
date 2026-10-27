import datetime

from django.test import TestCase

from apps.academics.models import Department, Program
from apps.admissions import services
from apps.admissions.models import AdmissionDeadline, AdmissionRequirement, Scholarship


class RequirementServiceTests(TestCase):
    def setUp(self):
        department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=department, code="CS", name="Computer Science"
        )

    def test_create_requirement(self):
        requirement = services.create_requirement(
            program=self.program, title="Minimum CGPA", description="At least 3.0/4.0"
        )
        self.assertEqual(requirement.program, self.program)
        self.assertTrue(AdmissionRequirement.objects.filter(id=requirement.id).exists())

    def test_update_requirement(self):
        requirement = services.create_requirement(
            program=self.program, title="Minimum CGPA", description="At least 3.0/4.0"
        )
        updated = services.update_requirement(requirement=requirement, description="At least 3.3/4.0")
        self.assertEqual(updated.description, "At least 3.3/4.0")
        requirement.refresh_from_db()
        self.assertEqual(requirement.description, "At least 3.3/4.0")

    def test_delete_requirement(self):
        requirement = services.create_requirement(
            program=self.program, title="Minimum CGPA", description="At least 3.0/4.0"
        )
        services.delete_requirement(requirement=requirement)
        self.assertFalse(AdmissionRequirement.objects.filter(id=requirement.id).exists())


class DeadlineServiceTests(TestCase):
    def setUp(self):
        department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=department, code="CS", name="Computer Science"
        )

    def test_create_deadline(self):
        deadline = services.create_deadline(
            program=self.program, label="Fall Deadline", date=datetime.date(2026, 8, 1)
        )
        self.assertTrue(AdmissionDeadline.objects.filter(id=deadline.id).exists())

    def test_update_deadline(self):
        deadline = services.create_deadline(
            program=self.program, label="Fall Deadline", date=datetime.date(2026, 8, 1)
        )
        updated = services.update_deadline(deadline=deadline, date=datetime.date(2026, 8, 15))
        self.assertEqual(updated.date, datetime.date(2026, 8, 15))

    def test_delete_deadline(self):
        deadline = services.create_deadline(
            program=self.program, label="Fall Deadline", date=datetime.date(2026, 8, 1)
        )
        services.delete_deadline(deadline=deadline)
        self.assertFalse(AdmissionDeadline.objects.filter(id=deadline.id).exists())


class ScholarshipServiceTests(TestCase):
    def test_create_scholarship(self):
        scholarship = services.create_scholarship(
            name="Merit Scholarship", description="Top scorers", amount=50000
        )
        self.assertTrue(Scholarship.objects.filter(id=scholarship.id).exists())

    def test_update_scholarship(self):
        scholarship = services.create_scholarship(name="Merit Scholarship", description="Top scorers")
        updated = services.update_scholarship(scholarship=scholarship, is_active=False)
        self.assertFalse(updated.is_active)

    def test_delete_scholarship(self):
        scholarship = services.create_scholarship(name="Merit Scholarship", description="Top scorers")
        services.delete_scholarship(scholarship=scholarship)
        self.assertFalse(Scholarship.objects.filter(id=scholarship.id).exists())
