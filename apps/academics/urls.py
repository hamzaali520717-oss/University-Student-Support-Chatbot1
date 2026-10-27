from django.urls import path

from apps.academics.views import (
    CourseListView,
    MyAttendanceListView,
    MyEnrollmentListCreateView,
    MySemesterPlanListView,
    ProgramListView,
    SubjectListView,
)

urlpatterns = [
    path("programs/", ProgramListView.as_view(), name="program-list"),
    path("courses/", CourseListView.as_view(), name="course-list"),
    path("subjects/", SubjectListView.as_view(), name="subject-list"),
    path("me/enrollments/", MyEnrollmentListCreateView.as_view(), name="my-enrollments"),
    path("me/attendance/", MyAttendanceListView.as_view(), name="my-attendance"),
    path("me/plan/", MySemesterPlanListView.as_view(), name="my-plan"),
]
