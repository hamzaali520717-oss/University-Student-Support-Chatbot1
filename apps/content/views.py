from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.serializers import BaseSerializer
from rest_framework.throttling import ScopedRateThrottle

from apps.content import selectors, services
from apps.content.models import Announcement
from apps.content.serializers import (
    AnnouncementSerializer,
    ContactMessageSerializer,
    NewsPostSerializer,
    PageSerializer,
)
from apps.core.permissions import IsAdminStaff, IsStudent


class AnnouncementListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = AnnouncementSerializer

    def get_queryset(self):
        return selectors.list_published_announcements(audiences=[Announcement.Audience.PUBLIC])


class MyAnnouncementListView(generics.ListAPIView):
    permission_classes = [IsStudent]
    serializer_class = AnnouncementSerializer

    def get_queryset(self):
        return selectors.list_published_announcements(
            audiences=[Announcement.Audience.PUBLIC, Announcement.Audience.STUDENT]
        )


class AnnouncementAdminListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdminStaff]
    serializer_class = AnnouncementSerializer
    queryset = selectors.list_announcements()

    def perform_create(self, serializer: BaseSerializer) -> None:
        serializer.instance = services.create_announcement(**serializer.validated_data)


class AnnouncementAdminDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminStaff]
    serializer_class = AnnouncementSerializer
    queryset = selectors.list_announcements()

    def perform_update(self, serializer: BaseSerializer) -> None:
        serializer.instance = services.update_announcement(
            announcement=serializer.instance, **serializer.validated_data
        )

    def perform_destroy(self, instance) -> None:
        services.delete_announcement(announcement=instance)


class NewsPostListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = NewsPostSerializer

    def get_queryset(self):
        return selectors.list_published_news()


class NewsPostDetailView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = NewsPostSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return selectors.list_published_news()


class NewsPostAdminListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdminStaff]
    serializer_class = NewsPostSerializer
    queryset = selectors.list_news()

    def perform_create(self, serializer: BaseSerializer) -> None:
        serializer.instance = services.create_news_post(**serializer.validated_data)


class NewsPostAdminDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminStaff]
    serializer_class = NewsPostSerializer
    queryset = selectors.list_news()

    def perform_update(self, serializer: BaseSerializer) -> None:
        serializer.instance = services.update_news_post(
            news_post=serializer.instance, **serializer.validated_data
        )

    def perform_destroy(self, instance) -> None:
        services.delete_news_post(news_post=instance)


class PageDetailView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = PageSerializer
    lookup_field = "slug"
    queryset = selectors.list_pages()


class PageAdminListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdminStaff]
    serializer_class = PageSerializer
    queryset = selectors.list_pages()

    def perform_create(self, serializer: BaseSerializer) -> None:
        serializer.instance = services.create_page(**serializer.validated_data)


class PageAdminDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminStaff]
    serializer_class = PageSerializer
    queryset = selectors.list_pages()

    def perform_update(self, serializer: BaseSerializer) -> None:
        serializer.instance = services.update_page(page=serializer.instance, **serializer.validated_data)

    def perform_destroy(self, instance) -> None:
        services.delete_page(page=instance)


class ContactMessageCreateView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "contact"
    serializer_class = ContactMessageSerializer

    def perform_create(self, serializer: BaseSerializer) -> None:
        serializer.instance = services.submit_contact_message(**serializer.validated_data)


class ContactMessageAdminListView(generics.ListAPIView):
    permission_classes = [IsAdminStaff]
    serializer_class = ContactMessageSerializer
    queryset = selectors.list_contact_messages()


class ContactMessageAdminDetailView(generics.RetrieveDestroyAPIView):
    permission_classes = [IsAdminStaff]
    serializer_class = ContactMessageSerializer
    queryset = selectors.list_contact_messages()

    def perform_destroy(self, instance) -> None:
        services.delete_contact_message(contact_message=instance)
