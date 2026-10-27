from django.urls import path

from apps.website import views

app_name = "website"

urlpatterns = [
    path("", views.home, name="home"),
    path("programs/", views.program_list, name="program-list"),
    path("programs/<str:code>/", views.program_detail, name="program-detail"),
    path("scholarships/", views.scholarship_list, name="scholarship-list"),
    path("announcements/", views.announcement_list, name="announcement-list"),
    path("news/", views.news_list, name="news-list"),
    path("news/<slug:slug>/", views.news_detail, name="news-detail"),
    path("contact/", views.contact, name="contact"),
    path("pages/<slug:slug>/", views.page_detail, name="page-detail"),
]
