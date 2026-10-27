from django.urls import reverse

from apps.academics.models import SemesterPlan
from apps.accounts.models import StudentProfile, User
from apps.portal.tests.base import PortalTestCase


class SemesterPlanViewTests(PortalTestCase):
    def test_only_own_plans_with_subjects_prefetched(self):
        other_user = User.objects.create_user(username="student2", password="pw", role=User.Role.STUDENT)
        other_student = StudentProfile.objects.create(
            user=other_user, registration_no="REG-2", program=self.program
        )

        plan = SemesterPlan.objects.create(student=self.student, semester=1)
        plan.subjects.add(self.subject)
        SemesterPlan.objects.create(student=other_student, semester=1)

        self.login_student()
        response = self.client.get(reverse("portal:semester-plan"))
        self.assertEqual(len(response.context["plans"]), 1)
        self.assertContains(response, "CS101")
