from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.content.models import NewsPost, Page


class ContentUniqueConstraintTests(TestCase):
    def test_news_post_slug_unique(self):
        NewsPost.objects.create(
            title="New Library Wing", slug="new-library-wing", body="Opening soon.",
            publish_at=timezone.now(),
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            NewsPost.objects.create(
                title="Different Title", slug="new-library-wing", body="Duplicate slug.",
                publish_at=timezone.now(),
            )

    def test_page_slug_unique(self):
        Page.objects.create(slug="about", title="About Us", body="We are a university.")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Page.objects.create(slug="about", title="Duplicate", body="Duplicate slug.")
