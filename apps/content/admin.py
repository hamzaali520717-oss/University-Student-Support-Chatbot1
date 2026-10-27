from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from apps.content.models import Announcement, ContactMessage, HeroSlide, NewsPost, Page


def _thumbnail(image, *, width: int = 96, height: int = 48) -> str:
    if not image:
        return ""
    return format_html(
        '<img src="{}" style="height:{}px;width:{}px;object-fit:cover;border-radius:4px;" />',
        image.url,
        height,
        width,
    )


@admin.register(HeroSlide)
class HeroSlideAdmin(ModelAdmin):
    list_display = ["thumbnail", "headline", "order", "is_active"]
    list_editable = ["order", "is_active"]
    ordering = ["order"]

    @admin.display(description="Image")
    def thumbnail(self, obj: HeroSlide) -> str:
        return _thumbnail(obj.image)


@admin.register(NewsPost)
class NewsPostAdmin(ModelAdmin):
    list_display = ["thumbnail", "title", "publish_at"]
    search_fields = ["title"]
    ordering = ["-publish_at"]

    @admin.display(description="Image")
    def thumbnail(self, obj: NewsPost) -> str:
        return _thumbnail(obj.image)


@admin.register(Announcement)
class AnnouncementAdmin(ModelAdmin):
    list_display = ["title", "audience", "publish_at"]
    list_filter = ["audience"]
    search_fields = ["title"]
    date_hierarchy = "publish_at"
    ordering = ["-publish_at"]


@admin.register(Page)
class PageAdmin(ModelAdmin):
    list_display = ["slug", "title"]
    search_fields = ["slug", "title"]
    ordering = ["slug"]


@admin.register(ContactMessage)
class ContactMessageAdmin(ModelAdmin):
    list_display = ["name", "email", "subject", "created_at"]
    search_fields = ["name", "email", "subject"]
    ordering = ["-created_at"]

    def has_add_permission(self, request):
        return False
