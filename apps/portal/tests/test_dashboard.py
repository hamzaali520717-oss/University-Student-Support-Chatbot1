import datetime

from django.urls import reverse
from django.utils import timezone

from apps.academics.models import Enrollment
from apps.content.models import Announcement
from apps.finance.models import FeeStatus
from apps.portal.tests.base import PortalTestCase


class DashboardAccessTests(PortalTestCase):
    def test_anonymous_redirects_to_login(self):
        response = self.client.get(reverse("portal:dashboard"))
        self.assertRedirects(
            response, f"{reverse('portal:login')}?next={reverse('portal:dashboard')}"
        )

    def test_admin_gets_403(self):
        self.login_admin()
        response = self.client.get(reverse("portal:dashboard"))
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "This portal is for students", status_code=403)

    def test_role_student_without_profile_gets_403_not_500(self):
        # role=STUDENT is the User model's own default (e.g. what
        # createsuperuser produces without going through register_student) -
        # student_required must reject this cleanly, not crash downstream.
        self.login_profileless_student()
        response = self.client.get(reverse("portal:dashboard"))
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "This portal is for students", status_code=403)


class DashboardAggregatesTests(PortalTestCase):
    def test_enrollment_count_and_announcements(self):
        Enrollment.objects.create(student=self.student, subject=self.subject)
        now = timezone.now()
        Announcement.objects.create(
            title="Public notice",
            body="body",
            audience=Announcement.Audience.PUBLIC,
            publish_at=now - datetime.timedelta(days=1),
        )
        Announcement.objects.create(
            title="Student notice",
            body="body",
            audience=Announcement.Audience.STUDENT,
            publish_at=now - datetime.timedelta(days=1),
        )

        self.login_student()
        response = self.client.get(reverse("portal:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["enrollment_count"], 1)
        self.assertContains(response, "Public notice")
        self.assertContains(response, "Student notice")

    def test_attendance_ring_below_threshold_reads_attention(self):
        enrollment = Enrollment.objects.create(student=self.student, subject=self.subject)
        self.seed_attendance(enrollment, present_count=37, total_count=50)

        self.login_student()
        response = self.client.get(reverse("portal:dashboard"))
        self.assertEqual(response.context["attendance"]["rate"], 74)
        self.assertEqual(response.context["attendance"]["status"], "attention")

    def test_attendance_ring_at_or_above_threshold_reads_good(self):
        enrollment = Enrollment.objects.create(student=self.student, subject=self.subject)
        self.seed_attendance(enrollment, present_count=38, total_count=50)

        self.login_student()
        response = self.client.get(reverse("portal:dashboard"))
        self.assertEqual(response.context["attendance"]["rate"], 76)
        self.assertEqual(response.context["attendance"]["status"], "good")

    def test_attendance_ring_empty_state(self):
        self.login_student()
        response = self.client.get(reverse("portal:dashboard"))
        self.assertFalse(response.context["attendance"]["has_data"])

    def test_fee_progress_picks_highest_semester_and_flips_status(self):
        FeeStatus.objects.create(
            student=self.student,
            semester=1,
            amount_due="10000.00",
            amount_paid="10000.00",
            status=FeeStatus.Status.PAID,
        )
        FeeStatus.objects.create(
            student=self.student,
            semester=2,
            amount_due="20000.00",
            amount_paid="5000.00",
            status=FeeStatus.Status.PARTIAL,
        )

        self.login_student()
        response = self.client.get(reverse("portal:dashboard"))
        fee_context = response.context["fee"]
        self.assertEqual(fee_context["fee_status"].semester, 2)
        self.assertEqual(fee_context["percent_paid"], 25)
        self.assertEqual(fee_context["status"], "attention")

    def test_fee_progress_paid_reads_good(self):
        FeeStatus.objects.create(
            student=self.student,
            semester=1,
            amount_due="10000.00",
            amount_paid="10000.00",
            status=FeeStatus.Status.PAID,
        )

        self.login_student()
        response = self.client.get(reverse("portal:dashboard"))
        self.assertEqual(response.context["fee"]["status"], "good")

    def test_fee_progress_empty_state(self):
        self.login_student()
        response = self.client.get(reverse("portal:dashboard"))
        self.assertFalse(response.context["fee"]["has_data"])

    def test_fee_progress_bar_has_progressbar_role_and_aria_values(self):
        FeeStatus.objects.create(
            student=self.student,
            semester=1,
            amount_due="10000.00",
            amount_paid="2500.00",
            status=FeeStatus.Status.PARTIAL,
        )
        self.login_student()
        response = self.client.get(reverse("portal:dashboard"))
        self.assertContains(response, 'role="progressbar"')
        self.assertContains(response, 'aria-valuenow="25"')
        self.assertContains(response, 'aria-valuemin="0"')
        self.assertContains(response, 'aria-valuemax="100"')

    def test_announcement_titles_nest_under_the_section_heading(self):
        # Recent Announcements / Ask the Campus Assistant are h2 - individual
        # announcement titles must not also be h2 (sibling collision), so
        # a screen-reader user browsing by heading level sees them nested.
        Announcement.objects.create(
            title="Midterm schedule posted",
            body="body",
            audience=Announcement.Audience.PUBLIC,
            publish_at=timezone.now() - datetime.timedelta(days=1),
        )
        self.login_student()
        response = self.client.get(reverse("portal:dashboard"))
        self.assertNotContains(response, ">Midterm schedule posted</h2>")
        self.assertContains(response, "Midterm schedule posted</h3>")
