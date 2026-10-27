from django.urls import path

from apps.portal import views

app_name = "portal"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.dashboard, name="dashboard"),
    path("enrollments/", views.enrollments, name="enrollments"),
    path("attendance/", views.attendance, name="attendance"),
    path("semester-plan/", views.semester_plan, name="semester-plan"),
    path("fees/", views.fees, name="fees"),
    path("announcements/", views.announcements, name="announcements"),
    path("ask/", views.ask, name="ask"),
]
