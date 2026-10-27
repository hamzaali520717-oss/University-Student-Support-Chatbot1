import datetime
import io

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageDraw

from apps.content.models import Announcement, HeroSlide, NewsPost, Page
from apps.content.services import create_announcement, create_news_post, create_page

# Brand palette (must match tailwind.config.js / static/src/styles.css).
_BRAND_700 = (18, 48, 42)
_BRAND_500 = (29, 78, 66)
_ACCENT_500 = (217, 122, 60)
_ACCENT_700 = (156, 74, 31)


def _generate_placeholder_image(*, base_color: tuple, accent_color: tuple) -> ContentFile:
    """Draw a simple brand-colored abstract composition as a stand-in for real
    campus photography (no photo assets are available to source here)."""
    width, height = 1600, 900
    image = Image.new("RGB", (width, height), color=base_color)
    draw = ImageDraw.Draw(image)
    draw.ellipse((width * 0.55, -height * 0.3, width * 1.2, height * 0.8), fill=accent_color)
    draw.polygon(
        [(0, height), (width * 0.4, height), (width * 0.15, height * 0.5), (0, height * 0.65)],
        fill=tuple(min(c + 20, 255) for c in base_color),
    )
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return ContentFile(buffer.getvalue())


class Command(BaseCommand):
    help = "Seed sample pages, announcements (public and student), and news posts. Safe to re-run."

    @transaction.atomic
    def handle(self, *args, **options):
        now = timezone.now()

        page_defs = [
            ("about", "About the University", "We are a public university committed to teaching and research."),
            ("contact", "Contact Us", "Reach the registrar's office at registrar@example.edu."),
        ]
        for slug, title, body in page_defs:
            if not Page.objects.filter(slug=slug).exists():
                create_page(slug=slug, title=title, body=body)

        announcement_defs = [
            (
                "Campus Reopens for Fall Semester",
                "The campus reopens for the Fall 2026 semester on August 15.",
                Announcement.Audience.PUBLIC,
                now - datetime.timedelta(days=2),
            ),
            (
                "New Admissions Portal Live",
                "Prospective students can now apply online through the new admissions portal.",
                Announcement.Audience.PUBLIC,
                now - datetime.timedelta(days=5),
            ),
            (
                "Fall 2026 Exam Schedule Posted",
                "Final exam timetables for all programs are now available on the student portal.",
                Announcement.Audience.STUDENT,
                now - datetime.timedelta(days=1),
            ),
            (
                "Library Extended Hours During Finals",
                "The main library will stay open until midnight during finals week.",
                Announcement.Audience.STUDENT,
                now - datetime.timedelta(hours=6),
            ),
        ]
        for title, body, audience, publish_at in announcement_defs:
            if not Announcement.objects.filter(title=title).exists():
                create_announcement(title=title, body=body, audience=audience, publish_at=publish_at)

        news_defs = [
            (
                "New Library Wing Opens",
                "new-library-wing-opens",
                "A new three-story library wing opened this week, adding 500 study seats.",
                "New library wing adds 500 study seats.",
                now - datetime.timedelta(days=10),
                _BRAND_500,
                _ACCENT_500,
            ),
            (
                "University Ranks in Top 10 Nationally",
                "university-ranks-top-10-nationally",
                "The university climbed to the top 10 in this year's national rankings.",
                "University climbs to top 10 nationally.",
                now - datetime.timedelta(days=20),
                _ACCENT_700,
                _BRAND_700,
            ),
        ]
        for title, slug, body, summary, publish_at, base_color, accent_color in news_defs:
            post = NewsPost.objects.filter(slug=slug).first()
            if post is None:
                post = create_news_post(
                    title=title, slug=slug, body=body, summary=summary, publish_at=publish_at
                )
            if not post.image:
                image_file = _generate_placeholder_image(base_color=base_color, accent_color=accent_color)
                post.image.save(f"{slug}.jpg", image_file, save=True)

        hero_slide_defs = [
            (
                "Excellence in Education Since Day One",
                "Rigorous programs, dedicated faculty, and a community built around discovery.",
                "Explore Programs",
                "/programs/",
                _BRAND_500,
                _ACCENT_500,
            ),
            (
                "Shape Your Future With Us",
                "Applications for the next intake are open — find the program that fits your ambitions.",
                "View Admissions",
                "/programs/",
                _BRAND_700,
                _ACCENT_700,
            ),
            (
                "A Campus Built for Discovery",
                "State-of-the-art labs, libraries, and studios designed for hands-on learning.",
                "Read Latest News",
                "/news/",
                _ACCENT_700,
                _BRAND_500,
            ),
            (
                "Scholarships That Open Doors",
                "Merit and need-based scholarships help talented students go further.",
                "See Scholarships",
                "/scholarships/",
                _BRAND_500,
                _BRAND_700,
            ),
        ]
        for index, (headline, subtext, cta_label, cta_url, base_color, accent_color) in enumerate(
            hero_slide_defs
        ):
            if HeroSlide.objects.filter(headline=headline).exists():
                continue
            slide = HeroSlide(
                headline=headline,
                subtext=subtext,
                cta_label=cta_label,
                cta_url=cta_url,
                order=index,
            )
            image_file = _generate_placeholder_image(base_color=base_color, accent_color=accent_color)
            slide.image.save(f"slide-{index + 1}.jpg", image_file, save=False)
            slide.save()

        self.stdout.write(self.style.SUCCESS("Seeded content data."))
