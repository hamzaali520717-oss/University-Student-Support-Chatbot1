import datetime

from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.content.models import Announcement, ContactMessage, NewsPost, Page


class PublicReadTests(APITestCase):
    def setUp(self):
        now = timezone.now()
        self.published_public = Announcement.objects.create(
            title="Campus Reopening", body="Details.",
            audience=Announcement.Audience.PUBLIC, publish_at=now - datetime.timedelta(days=1),
        )
        Announcement.objects.create(
            title="Exam Schedule", body="Details.",
            audience=Announcement.Audience.STUDENT, publish_at=now - datetime.timedelta(days=1),
        )
        Announcement.objects.create(
            title="Future Notice", body="Details.",
            audience=Announcement.Audience.PUBLIC, publish_at=now + datetime.timedelta(days=1),
        )
        self.published_news = NewsPost.objects.create(
            title="New Library Wing", slug="new-library-wing", body="Opening soon.",
            publish_at=now - datetime.timedelta(days=1),
        )
        NewsPost.objects.create(
            title="Draft Post", slug="draft-post", body="Not live yet.",
            publish_at=now + datetime.timedelta(days=1),
        )
        self.page = Page.objects.create(slug="about", title="About Us", body="We are a university.")

    def test_public_announcement_list_only_public_and_published(self):
        response = self.client.get(reverse("announcement-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["title"], self.published_public.title)

    def test_public_news_list_only_published(self):
        response = self.client.get(reverse("news-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["slug"], self.published_news.slug)

    def test_public_news_detail_by_slug(self):
        response = self.client.get(reverse("news-detail", args=[self.published_news.slug]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], self.published_news.title)

    def test_unpublished_news_detail_not_found(self):
        response = self.client.get(reverse("news-detail", args=["draft-post"]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_public_page_detail_by_slug(self):
        response = self.client.get(reverse("page-detail", args=[self.page.slug]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], self.page.title)

    def test_public_contact_submit(self):
        response = self.client.post(
            reverse("contact-create"),
            {"name": "Jane Doe", "email": "jane@example.com", "subject": "Question", "message": "Hi there."},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(ContactMessage.objects.filter(email="jane@example.com").exists())

    def test_anonymous_cannot_reach_admin_announcements(self):
        response = self.client.get(reverse("announcement-admin-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class StudentScopedAnnouncementTests(APITestCase):
    def setUp(self):
        now = timezone.now()
        self.public_announcement = Announcement.objects.create(
            title="Campus Reopening", body="Details.",
            audience=Announcement.Audience.PUBLIC, publish_at=now - datetime.timedelta(days=1),
        )
        self.student_announcement = Announcement.objects.create(
            title="Exam Schedule", body="Details.",
            audience=Announcement.Audience.STUDENT, publish_at=now - datetime.timedelta(days=1),
        )

    def test_anonymous_cannot_reach_my_announcements(self):
        response = self.client.get(reverse("my-announcement-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_student_sees_public_and_student_announcements(self):
        student = User.objects.create_user(username="stu", password="pw", role=User.Role.STUDENT)
        self.client.force_authenticate(user=student)
        response = self.client.get(reverse("my-announcement-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = {item["title"] for item in response.data["results"]}
        self.assertEqual(titles, {self.public_announcement.title, self.student_announcement.title})


class ContactThrottleTests(APITestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_contact_submit_is_rate_limited_per_ip(self):
        payload = {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "subject": "Question",
            "message": "Hi there.",
        }
        for _ in range(5):
            response = self.client.post(reverse("contact-create"), payload)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(reverse("contact-create"), payload)
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class AdminWriteTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="pw", role=User.Role.ADMIN)
        self.client.force_authenticate(user=self.admin)

    def test_admin_can_create_announcement(self):
        response = self.client.post(
            reverse("announcement-admin-list"),
            {
                "title": "New Notice",
                "body": "Details.",
                "audience": Announcement.Audience.STUDENT,
                "publish_at": timezone.now().isoformat(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Announcement.objects.filter(title="New Notice").exists())

    def test_admin_can_update_and_delete_announcement(self):
        announcement = Announcement.objects.create(
            title="Campus Reopening", body="Details.", publish_at=timezone.now()
        )
        url = reverse("announcement-admin-detail", args=[announcement.id])
        response = self.client.patch(url, {"title": "Updated"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        announcement.refresh_from_db()
        self.assertEqual(announcement.title, "Updated")

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Announcement.objects.filter(id=announcement.id).exists())

    def test_admin_can_create_news_post(self):
        response = self.client.post(
            reverse("news-admin-list"),
            {
                "title": "New Library Wing",
                "slug": "new-library-wing",
                "body": "Opening soon.",
                "publish_at": timezone.now().isoformat(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(NewsPost.objects.filter(slug="new-library-wing").exists())

    def test_admin_can_create_and_update_page(self):
        response = self.client.post(
            reverse("page-admin-list"), {"slug": "about", "title": "About Us", "body": "We are a university."}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        page = Page.objects.get(slug="about")

        url = reverse("page-admin-detail", args=[page.id])
        response = self.client.patch(url, {"body": "Updated body."})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        page.refresh_from_db()
        self.assertEqual(page.body, "Updated body.")

    def test_admin_can_list_and_delete_contact_message(self):
        message = ContactMessage.objects.create(
            name="Jane Doe", email="jane@example.com", subject="Question", message="Hi there."
        )
        response = self.client.get(reverse("contact-admin-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

        url = reverse("contact-admin-detail", args=[message.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ContactMessage.objects.filter(id=message.id).exists())

    def test_student_cannot_create_page(self):
        student = User.objects.create_user(username="stu", password="pw", role=User.Role.STUDENT)
        self.client.force_authenticate(user=student)
        response = self.client.post(
            reverse("page-admin-list"), {"slug": "about", "title": "About Us", "body": "Body."}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
