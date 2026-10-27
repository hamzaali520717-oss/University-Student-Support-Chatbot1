import datetime

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import Course, Department, Program, Subject
from apps.admissions.models import AdmissionDeadline, AdmissionRequirement, Scholarship
from apps.content.models import Announcement, NewsPost, Page
from apps.finance.models import FeeStructure


class HomeViewTests(TestCase):
    def test_renders_with_no_data(self):
        response = self.client.get(reverse("website:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Excellence in Education Since Day One")

    def test_renders_featured_programs_and_stats(self):
        department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        Program.objects.create(department=department, code="CS", name="Computer Science")
        Scholarship.objects.create(name="Merit Award", description="Top scorers", is_active=True)

        response = self.client.get(reverse("website:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Computer Science")
        self.assertContains(response, "Active Scholarships")


class ProgramViewTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=self.department, code="CS", name="Computer Science"
        )
        AdmissionRequirement.objects.create(
            program=self.program, title="Minimum CGPA", description="At least 3.0/4.0"
        )
        AdmissionDeadline.objects.create(
            program=self.program,
            label="Fall Intake",
            date=timezone.localdate() + datetime.timedelta(days=30),
        )
        FeeStructure.objects.create(program=self.program, semester=1, amount="1000.00")

    def test_program_list_renders(self):
        response = self.client.get(reverse("website:program-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Computer Science")

    def test_program_list_renders_department_filter_chip(self):
        response = self.client.get(reverse("website:program-list"))
        self.assertContains(response, 'data-filter-chip')
        self.assertContains(response, f'data-department="{self.department.code}"')
        self.assertContains(response, self.department.name)

    def test_program_list_shows_curriculum_meta(self):
        course = Course.objects.create(department=self.department, code="CS101", title="Intro")
        Subject.objects.create(program=self.program, course=course, semester=1, credit_hours=3)
        Subject.objects.create(program=self.program, course=course, semester=2, credit_hours=4)

        response = self.client.get(reverse("website:program-list"))

        self.assertContains(response, "2 courses")
        self.assertContains(response, "7 credit hrs")

    def test_program_detail_renders_related_data(self):
        response = self.client.get(reverse("website:program-detail", kwargs={"code": "CS"}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Minimum CGPA")
        self.assertContains(response, "Fall Intake")

    def test_program_detail_404_for_unknown_code(self):
        response = self.client.get(reverse("website:program-detail", kwargs={"code": "NOPE"}))
        self.assertEqual(response.status_code, 404)


class ProgramListEmptyStateTests(TestCase):
    def test_empty_state_when_no_programs(self):
        response = self.client.get(reverse("website:program-list"))
        self.assertContains(response, "No programs are published yet.")


class ScholarshipViewTests(TestCase):
    def test_lists_only_active_scholarships(self):
        Scholarship.objects.create(name="Active Award", description="desc", is_active=True)
        Scholarship.objects.create(name="Retired Award", description="desc", is_active=False)

        response = self.client.get(reverse("website:scholarship-list"))

        self.assertContains(response, "Active Award")
        self.assertNotContains(response, "Retired Award")

    def test_amount_rendered_as_localized_pkr(self):
        Scholarship.objects.create(
            name="Merit Award", description="desc", amount="50000.00", is_active=True
        )
        response = self.client.get(reverse("website:scholarship-list"))
        self.assertContains(response, "PKR 50,000")
        self.assertNotContains(response, "50000.00")

    def test_short_eligibility_rendered_as_pill(self):
        Scholarship.objects.create(
            name="Merit Award",
            description="desc",
            eligibility_criteria="GPA 3.5+",
            is_active=True,
        )
        response = self.client.get(reverse("website:scholarship-list"))
        self.assertContains(response, "badge-accent")
        self.assertContains(response, "GPA 3.5+")

    def test_long_eligibility_rendered_as_sentence_not_pill(self):
        long_text = "Applicants must maintain a minimum GPA of 3.5 and demonstrate documented financial need."
        Scholarship.objects.create(
            name="Need-Based Award", description="desc", eligibility_criteria=long_text, is_active=True
        )
        response = self.client.get(reverse("website:scholarship-list"))
        self.assertContains(response, f"Eligibility: {long_text}")
        self.assertNotContains(response, "badge-accent")

    def test_empty_state_when_no_active_scholarships(self):
        response = self.client.get(reverse("website:scholarship-list"))
        self.assertContains(response, "No active scholarships right now")


class AnnouncementViewTests(TestCase):
    def test_lists_public_announcements_only(self):
        now = timezone.now()
        Announcement.objects.create(
            title="Public Notice",
            body="body",
            audience=Announcement.Audience.PUBLIC,
            publish_at=now - datetime.timedelta(days=1),
        )
        Announcement.objects.create(
            title="Student Only Notice",
            body="body",
            audience=Announcement.Audience.STUDENT,
            publish_at=now - datetime.timedelta(days=1),
        )

        response = self.client.get(reverse("website:announcement-list"))

        self.assertContains(response, "Public Notice")
        self.assertNotContains(response, "Student Only Notice")

    def test_empty_state_when_no_announcements(self):
        response = self.client.get(reverse("website:announcement-list"))
        self.assertContains(response, "No announcements right now.")


class NewsViewTests(TestCase):
    def setUp(self):
        self.post = NewsPost.objects.create(
            title="New Library Wing",
            slug="new-library-wing",
            body="Opening next month.",
            publish_at=timezone.now() - datetime.timedelta(days=1),
        )

    def test_news_list_renders(self):
        response = self.client.get(reverse("website:news-list"))
        self.assertContains(response, "New Library Wing")

    def test_news_detail_renders(self):
        response = self.client.get(reverse("website:news-detail", kwargs={"slug": "new-library-wing"}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Opening next month.")

    def test_news_detail_404_for_unknown_slug(self):
        response = self.client.get(reverse("website:news-detail", kwargs={"slug": "missing"}))
        self.assertEqual(response.status_code, 404)

    def test_news_list_falls_back_to_icon_when_no_image(self):
        response = self.client.get(reverse("website:news-list"))
        self.assertNotContains(response, "<img")

    def test_news_list_renders_lead_image_when_present(self):
        self.post.image = SimpleUploadedFile("lead.jpg", b"fake-image-bytes", content_type="image/jpeg")
        self.post.save(update_fields=["image"])

        response = self.client.get(reverse("website:news-list"))

        self.assertContains(response, "<img")
        self.assertContains(response, self.post.image.url)

    def test_news_detail_renders_image_when_present(self):
        self.post.image = SimpleUploadedFile("lead.jpg", b"fake-image-bytes", content_type="image/jpeg")
        self.post.save(update_fields=["image"])

        response = self.client.get(reverse("website:news-detail", kwargs={"slug": "new-library-wing"}))

        self.assertContains(response, self.post.image.url)


class NewsListEmptyStateTests(TestCase):
    def test_empty_state_when_no_news(self):
        response = self.client.get(reverse("website:news-list"))
        self.assertContains(response, "No news posts yet.")


class PageViewTests(TestCase):
    def test_page_detail_renders(self):
        Page.objects.create(slug="about", title="About Us", body="We are a university.")
        response = self.client.get(reverse("website:page-detail", kwargs={"slug": "about"}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "We are a university.")

    def test_page_detail_404_for_unknown_slug(self):
        response = self.client.get(reverse("website:page-detail", kwargs={"slug": "missing"}))
        self.assertEqual(response.status_code, 404)


class ContactViewTests(TestCase):
    def test_renders_with_page_content(self):
        Page.objects.create(slug="contact", title="Contact", body="Reach the registrar office.")
        response = self.client.get(reverse("website:contact"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reach the registrar office.")

    def test_renders_without_page_content(self):
        response = self.client.get(reverse("website:contact"))
        self.assertEqual(response.status_code, 200)
