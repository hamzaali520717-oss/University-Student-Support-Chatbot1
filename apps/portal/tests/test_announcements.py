import datetime

from django.urls import reverse
from django.utils import timezone

from apps.content.models import Announcement
from apps.portal.tests.base import PortalTestCase


class AnnouncementsViewTests(PortalTestCase):
    def test_shows_public_and_student_audiences_excludes_unpublished(self):
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
        Announcement.objects.create(
            title="Future notice",
            body="body",
            audience=Announcement.Audience.STUDENT,
            publish_at=now + datetime.timedelta(days=1),
        )

        self.login_student()
        response = self.client.get(reverse("portal:announcements"))
        self.assertContains(response, "Public notice")
        self.assertContains(response, "Student notice")
        self.assertNotContains(response, "Future notice")
