from django.urls import reverse

from apps.accounts.models import StudentProfile, User
from apps.finance.models import FeeStatus
from apps.portal.tests.base import PortalTestCase


class FeesViewTests(PortalTestCase):
    def test_only_own_fee_statuses(self):
        other_user = User.objects.create_user(username="student2", password="pw", role=User.Role.STUDENT)
        other_student = StudentProfile.objects.create(
            user=other_user, registration_no="REG-2", program=self.program
        )
        FeeStatus.objects.create(
            student=self.student, semester=1, amount_due="50000.00", amount_paid="20000.00"
        )
        FeeStatus.objects.create(student=other_student, semester=1, amount_due="50000.00")

        self.login_student()
        response = self.client.get(reverse("portal:fees"))
        self.assertEqual(len(response.context["fee_statuses"]), 1)

    def test_amounts_render_through_pkr_filter(self):
        FeeStatus.objects.create(
            student=self.student, semester=1, amount_due="50000.00", amount_paid="20000.00"
        )
        self.login_student()
        response = self.client.get(reverse("portal:fees"))
        self.assertContains(response, "PKR 20,000")
        self.assertContains(response, "PKR 50,000")

    def test_no_payment_action_exposed(self):
        FeeStatus.objects.create(student=self.student, semester=1, amount_due="50000.00")
        self.login_student()
        response = self.client.get(reverse("portal:fees"))
        # The only <form> on any portal page is the shared logout form in
        # portal/base.html's nav - assert there's no second (payment) form.
        self.assertContains(response, "<form", count=1)
