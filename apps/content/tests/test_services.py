from django.test import TestCase
from django.utils import timezone

from apps.content import services
from apps.content.models import Announcement, ContactMessage, NewsPost, Page


class AnnouncementServiceTests(TestCase):
    def test_create_announcement_defaults_to_public_audience(self):
        announcement = services.create_announcement(
            title="Campus Reopening", body="Details.", publish_at=timezone.now()
        )
        self.assertEqual(announcement.audience, Announcement.Audience.PUBLIC)
        self.assertTrue(Announcement.objects.filter(id=announcement.id).exists())

    def test_update_announcement(self):
        announcement = services.create_announcement(
            title="Campus Reopening", body="Details.", publish_at=timezone.now()
        )
        updated = services.update_announcement(announcement=announcement, title="Updated Title")
        self.assertEqual(updated.title, "Updated Title")
        announcement.refresh_from_db()
        self.assertEqual(announcement.title, "Updated Title")

    def test_delete_announcement(self):
        announcement = services.create_announcement(
            title="Campus Reopening", body="Details.", publish_at=timezone.now()
        )
        services.delete_announcement(announcement=announcement)
        self.assertFalse(Announcement.objects.filter(id=announcement.id).exists())


class NewsPostServiceTests(TestCase):
    def test_create_news_post(self):
        news_post = services.create_news_post(
            title="New Library Wing",
            slug="new-library-wing",
            body="Opening next month.",
            publish_at=timezone.now(),
        )
        self.assertTrue(NewsPost.objects.filter(id=news_post.id).exists())

    def test_update_news_post(self):
        news_post = services.create_news_post(
            title="New Library Wing",
            slug="new-library-wing",
            body="Opening next month.",
            publish_at=timezone.now(),
        )
        updated = services.update_news_post(news_post=news_post, summary="Now open early.")
        self.assertEqual(updated.summary, "Now open early.")

    def test_delete_news_post(self):
        news_post = services.create_news_post(
            title="New Library Wing",
            slug="new-library-wing",
            body="Opening next month.",
            publish_at=timezone.now(),
        )
        services.delete_news_post(news_post=news_post)
        self.assertFalse(NewsPost.objects.filter(id=news_post.id).exists())


class PageServiceTests(TestCase):
    def test_create_page(self):
        page = services.create_page(slug="about", title="About Us", body="We are a university.")
        self.assertTrue(Page.objects.filter(id=page.id).exists())

    def test_update_page(self):
        page = services.create_page(slug="about", title="About Us", body="We are a university.")
        updated = services.update_page(page=page, body="Updated body.")
        self.assertEqual(updated.body, "Updated body.")

    def test_delete_page(self):
        page = services.create_page(slug="about", title="About Us", body="We are a university.")
        services.delete_page(page=page)
        self.assertFalse(Page.objects.filter(id=page.id).exists())


class ContactMessageServiceTests(TestCase):
    def test_submit_contact_message(self):
        message = services.submit_contact_message(
            name="Jane Doe", email="jane@example.com", subject="Question", message="Hi there."
        )
        self.assertTrue(ContactMessage.objects.filter(id=message.id).exists())

    def test_delete_contact_message(self):
        message = services.submit_contact_message(
            name="Jane Doe", email="jane@example.com", subject="Question", message="Hi there."
        )
        services.delete_contact_message(contact_message=message)
        self.assertFalse(ContactMessage.objects.filter(id=message.id).exists())
