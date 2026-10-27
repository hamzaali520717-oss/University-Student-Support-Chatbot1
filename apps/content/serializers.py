from rest_framework import serializers

from apps.content.models import Announcement, ContactMessage, NewsPost, Page


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = ["id", "title", "body", "audience", "publish_at", "created_at"]
        read_only_fields = ["id", "created_at"]


class NewsPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsPost
        fields = ["id", "title", "slug", "summary", "body", "image", "publish_at", "created_at"]
        read_only_fields = ["id", "created_at"]


class PageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = ["id", "slug", "title", "body", "created_at"]
        read_only_fields = ["id", "created_at"]


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ["id", "name", "email", "subject", "message", "created_at"]
        read_only_fields = ["id", "created_at"]
