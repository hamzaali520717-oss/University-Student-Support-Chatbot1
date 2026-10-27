from django.db.models import QuerySet
from django.utils import timezone

from apps.content.models import Announcement, ContactMessage, HeroSlide, NewsPost, Page


def list_announcements() -> QuerySet[Announcement]:
    return Announcement.objects.all()


def list_published_announcements(*, audiences: list[str]) -> QuerySet[Announcement]:
    return list_announcements().filter(publish_at__lte=timezone.now(), audience__in=audiences)


def list_news() -> QuerySet[NewsPost]:
    return NewsPost.objects.all()


def list_published_news() -> QuerySet[NewsPost]:
    return list_news().filter(publish_at__lte=timezone.now())


def list_pages() -> QuerySet[Page]:
    return Page.objects.all()


def get_page_by_slug(*, slug: str) -> Page | None:
    return list_pages().filter(slug=slug).first()


def list_contact_messages() -> QuerySet[ContactMessage]:
    return ContactMessage.objects.all()


def list_active_hero_slides() -> QuerySet[HeroSlide]:
    return HeroSlide.objects.filter(is_active=True).order_by("order")
