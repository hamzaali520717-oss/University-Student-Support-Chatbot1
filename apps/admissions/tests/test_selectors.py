import datetime

from django.test import TestCase
from django.utils import timezone

from apps.academics.models import Department, Program
from apps.admissions import selectors
from apps.admissions.models import AdmissionDeadline, AdmissionRequirement, Scholarship


class RequirementSelectorTests(TestCase):
    def setUp(self):
        department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.cs = Program.objects.create(department=department, code="CS", name="Computer Science")
        self.se = Program.objects.create(department=department, code="SE", name="Software Engineering")
        self.cs_requirement = AdmissionRequirement.objects.create(
            program=self.cs, title="Minimum CGPA", description="At least 3.0/4.0"
        )
        self.se_requirement = AdmissionRequirement.objects.create(
            program=self.se, title="Portfolio", description="Submit a coding portfolio"
        )

    def test_list_requirements_unfiltered_returns_all(self):
        self.assertEqual(selectors.list_requirements().count(), 2)

    def test_list_requirements_filtered_by_program(self):
        result = selectors.list_requirements(program_code="CS")
        self.assertEqual(list(result), [self.cs_requirement])


class DeadlineSelectorTests(TestCase):
    def setUp(self):
        department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=department, code="CS", name="Computer Science"
        )
        self.today = timezone.localdate()
        self.past_deadline = AdmissionDeadline.objects.create(
            program=self.program, label="Past Deadline", date=self.today - datetime.timedelta(days=10)
        )
        self.upcoming_deadline = AdmissionDeadline.objects.create(
            program=self.program, label="Upcoming Deadline", date=self.today + datetime.timedelta(days=10)
        )

    def test_list_deadlines_returns_all(self):
        self.assertEqual(selectors.list_deadlines().count(), 2)

    def test_list_upcoming_deadlines_excludes_past(self):
        result = selectors.list_upcoming_deadlines()
        self.assertEqual(list(result), [self.upcoming_deadline])


class ScholarshipSelectorTests(TestCase):
    def setUp(self):
        self.active = Scholarship.objects.create(
            name="Merit Scholarship", description="Top scorers", is_active=True
        )
        self.inactive = Scholarship.objects.create(
            name="Need-Based Grant", description="Discontinued", is_active=False
        )

    def test_list_scholarships_returns_all(self):
        self.assertEqual(selectors.list_scholarships().count(), 2)

    def test_list_active_scholarships_excludes_inactive(self):
        result = selectors.list_active_scholarships()
        self.assertEqual(list(result), [self.active])
