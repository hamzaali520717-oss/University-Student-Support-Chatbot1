from django.urls import path

from apps.content.views import (
    AnnouncementAdminDetailView,
    AnnouncementAdminListCreateView,
    AnnouncementListView,
    ContactMessageAdminDetailView,
    ContactMessageAdminListView,
    ContactMessageCreateView,
    MyAnnouncementListView,
    NewsPostAdminDetailView,
    NewsPostAdminListCreateView,
    NewsPostDetailView,
    NewsPostListView,
    PageAdminDetailView,
    PageAdminListCreateView,
    PageDetailView,
)

urlpatterns = [
    path("announcements/", AnnouncementListView.as_view(), name="announcement-list"),
    path("me/announcements/", MyAnnouncementListView.as_view(), name="my-announcement-list"),
    path("news/", NewsPostListView.as_view(), name="news-list"),
    path("news/<slug:slug>/", NewsPostDetailView.as_view(), name="news-detail"),
    path("pages/<slug:slug>/", PageDetailView.as_view(), name="page-detail"),
    path("contact/", ContactMessageCreateView.as_view(), name="contact-create"),
    path(
        "admin/announcements/",
        AnnouncementAdminListCreateView.as_view(),
        name="announcement-admin-list",
    ),
    path(
        "admin/announcements/<int:pk>/",
        AnnouncementAdminDetailView.as_view(),
        name="announcement-admin-detail",
    ),
    path("admin/news/", NewsPostAdminListCreateView.as_view(), name="news-admin-list"),
    path("admin/news/<int:pk>/", NewsPostAdminDetailView.as_view(), name="news-admin-detail"),
    path("admin/pages/", PageAdminListCreateView.as_view(), name="page-admin-list"),
    path("admin/pages/<int:pk>/", PageAdminDetailView.as_view(), name="page-admin-detail"),
    path(
        "admin/contact-messages/",
        ContactMessageAdminListView.as_view(),
        name="contact-admin-list",
    ),
    path(
        "admin/contact-messages/<int:pk>/",
        ContactMessageAdminDetailView.as_view(),
        name="contact-admin-detail",
    ),
]
