from django.db import models

from apps.core.models import BaseModel


class Announcement(BaseModel):
    class Audience(models.TextChoices):
        PUBLIC = "public", "Public"
        STUDENT = "student", "Student"

    title = models.CharField(max_length=200)
    body = models.TextField()
    audience = models.CharField(max_length=20, choices=Audience.choices, default=Audience.PUBLIC)
    publish_at = models.DateTimeField()

    class Meta(BaseModel.Meta):
        ordering = ["-publish_at"]

    def __str__(self) -> str:
        return self.title


class NewsPost(BaseModel):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    summary = models.CharField(max_length=300, blank=True, default="")
    body = models.TextField()
    image = models.ImageField(upload_to="news/", blank=True)
    publish_at = models.DateTimeField()

    class Meta(BaseModel.Meta):
        ordering = ["-publish_at"]

    def __str__(self) -> str:
        return self.title


class Page(BaseModel):
    slug = models.SlugField(max_length=100, unique=True)
    title = models.CharField(max_length=200)
    body = models.TextField()

    def __str__(self) -> str:
        return self.slug


class ContactMessage(BaseModel):
    name = models.CharField(max_length=150)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()

    def __str__(self) -> str:
        return f"{self.name} <{self.email}>: {self.subject}"


class HeroSlide(BaseModel):
    image = models.ImageField(upload_to="hero_slides/")
    headline = models.CharField(max_length=200)
    subtext = models.CharField(max_length=300, blank=True, default="")
    cta_label = models.CharField(max_length=80, blank=True, default="")
    cta_url = models.CharField(max_length=300, blank=True, default="")
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        ordering = ["order", "-created_at"]

    def __str__(self) -> str:
        return self.headline
