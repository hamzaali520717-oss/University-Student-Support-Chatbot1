import datetime

from django.db import transaction

from apps.content.models import Announcement, ContactMessage, NewsPost, Page


@transaction.atomic
def create_announcement(
    *,
    title: str,
    body: str,
    publish_at: datetime.datetime,
    audience: str = Announcement.Audience.PUBLIC,
) -> Announcement:
    return Announcement.objects.create(
        title=title, body=body, audience=audience, publish_at=publish_at
    )


@transaction.atomic
def update_announcement(*, announcement: Announcement, **fields) -> Announcement:
    for field, value in fields.items():
        setattr(announcement, field, value)
    announcement.save(update_fields=[*fields.keys(), "updated_at"])
    return announcement


@transaction.atomic
def delete_announcement(*, announcement: Announcement) -> None:
    announcement.delete()


@transaction.atomic
def create_news_post(
    *,
    title: str,
    slug: str,
    body: str,
    publish_at: datetime.datetime,
    summary: str = "",
) -> NewsPost:
    return NewsPost.objects.create(
        title=title, slug=slug, summary=summary, body=body, publish_at=publish_at
    )


@transaction.atomic
def update_news_post(*, news_post: NewsPost, **fields) -> NewsPost:
    for field, value in fields.items():
        setattr(news_post, field, value)
    news_post.save(update_fields=[*fields.keys(), "updated_at"])
    return news_post


@transaction.atomic
def delete_news_post(*, news_post: NewsPost) -> None:
    news_post.delete()


@transaction.atomic
def create_page(*, slug: str, title: str, body: str) -> Page:
    return Page.objects.create(slug=slug, title=title, body=body)


@transaction.atomic
def update_page(*, page: Page, **fields) -> Page:
    for field, value in fields.items():
        setattr(page, field, value)
    page.save(update_fields=[*fields.keys(), "updated_at"])
    return page


@transaction.atomic
def delete_page(*, page: Page) -> None:
    page.delete()


@transaction.atomic
def submit_contact_message(*, name: str, email: str, subject: str, message: str) -> ContactMessage:
    return ContactMessage.objects.create(name=name, email=email, subject=subject, message=message)


@transaction.atomic
def delete_contact_message(*, contact_message: ContactMessage) -> None:
    contact_message.delete()
