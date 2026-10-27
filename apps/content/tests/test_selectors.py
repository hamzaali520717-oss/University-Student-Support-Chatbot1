import datetime

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from apps.content import selectors
from apps.content.models import Announcement, ContactMessage, HeroSlide, NewsPost, Page


class AnnouncementSelectorTests(TestCase):
    def setUp(self):
        now = timezone.now()
        self.published_public = Announcement.objects.create(
            title="Campus Reopening",
            body="Campus reopens Monday.",
            audience=Announcement.Audience.PUBLIC,
            publish_at=now - datetime.timedelta(days=1),
        )
        self.published_student = Announcement.objects.create(
            title="Exam Schedule",
            body="Finals start next week.",
            audience=Announcement.Audience.STUDENT,
            publish_at=now - datetime.timedelta(days=1),
        )
        self.unpublished_public = Announcement.objects.create(
            title="Future Notice",
            body="Not yet visible.",
            audience=Announcement.Audience.PUBLIC,
            publish_at=now + datetime.timedelta(days=1),
        )

    def test_list_announcements_returns_all(self):
        self.assertEqual(selectors.list_announcements().count(), 3)

    def test_list_published_announcements_public_excludes_student_and_future(self):
        result = selectors.list_published_announcements(audiences=[Announcement.Audience.PUBLIC])
        self.assertEqual(list(result), [self.published_public])

    def test_list_published_announcements_includes_student_audience(self):
        result = selectors.list_published_announcements(
            audiences=[Announcement.Audience.PUBLIC, Announcement.Audience.STUDENT]
        )
        self.assertEqual(set(result), {self.published_public, self.published_student})


class NewsPostSelectorTests(TestCase):
    def setUp(self):
        now = timezone.now()
        self.published = NewsPost.objects.create(
            title="New Library Wing",
            slug="new-library-wing",
            body="Opening next month.",
            publish_at=now - datetime.timedelta(days=1),
        )
        self.unpublished = NewsPost.objects.create(
            title="Draft Announcement",
            slug="draft-announcement",
            body="Not yet live.",
            publish_at=now + datetime.timedelta(days=1),
        )

    def test_list_news_returns_all(self):
        self.assertEqual(selectors.list_news().count(), 2)

    def test_list_published_news_excludes_future(self):
        result = selectors.list_published_news()
        self.assertEqual(list(result), [self.published])


class PageSelectorTests(TestCase):
    def test_list_pages_returns_all(self):
        Page.objects.create(slug="about", title="About Us", body="We are a university.")
        Page.objects.create(slug="contact", title="Contact", body="Reach us here.")
        self.assertEqual(selectors.list_pages().count(), 2)

    def test_get_page_by_slug_returns_matching_page(self):
        Page.objects.create(slug="about", title="About Us", body="We are a university.")
        contact_page = Page.objects.create(slug="contact", title="Contact", body="Reach us here.")
        self.assertEqual(selectors.get_page_by_slug(slug="contact"), contact_page)

    def test_get_page_by_slug_returns_none_when_missing(self):
        self.assertIsNone(selectors.get_page_by_slug(slug="missing"))


class ContactMessageSelectorTests(TestCase):
    def test_list_contact_messages_returns_all(self):
        ContactMessage.objects.create(
            name="Jane Doe", email="jane@example.com", subject="Question", message="Hi there."
        )
        self.assertEqual(selectors.list_contact_messages().count(), 1)


def _fake_image(name: str) -> SimpleUploadedFile:
    return SimpleUploadedFile(name, b"fake-image-bytes", content_type="image/jpeg")


class HeroSlideSelectorTests(TestCase):
    def setUp(self):
        self.active_first = HeroSlide.objects.create(
            image=_fake_image("slide-1.jpg"), headline="First", order=0, is_active=True
        )
        self.active_second = HeroSlide.objects.create(
            image=_fake_image("slide-2.jpg"), headline="Second", order=1, is_active=True
        )
        self.inactive = HeroSlide.objects.create(
            image=_fake_image("slide-3.jpg"), headline="Inactive", order=2, is_active=False
        )

    def test_list_active_hero_slides_excludes_inactive(self):
        result = selectors.list_active_hero_slides()
        self.assertEqual(list(result), [self.active_first, self.active_second])

    def test_list_active_hero_slides_orders_by_order_field(self):
        self.active_first.order = 5
        self.active_first.save(update_fields=["order"])
        result = selectors.list_active_hero_slides()
        self.assertEqual(list(result), [self.active_second, self.active_first])
