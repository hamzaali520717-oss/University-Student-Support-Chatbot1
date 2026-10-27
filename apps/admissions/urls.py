from django.urls import path

from apps.admissions.views import (
    AdmissionDeadlineDetailView,
    AdmissionDeadlineListCreateView,
    AdmissionRequirementDetailView,
    AdmissionRequirementListCreateView,
    ScholarshipDetailView,
    ScholarshipListCreateView,
)

urlpatterns = [
    path(
        "requirements/",
        AdmissionRequirementListCreateView.as_view(),
        name="requirement-list",
    ),
    path(
        "requirements/<int:pk>/",
        AdmissionRequirementDetailView.as_view(),
        name="requirement-detail",
    ),
    path(
        "deadlines/",
        AdmissionDeadlineListCreateView.as_view(),
        name="deadline-list",
    ),
    path(
        "deadlines/<int:pk>/",
        AdmissionDeadlineDetailView.as_view(),
        name="deadline-detail",
    ),
    path(
        "scholarships/",
        ScholarshipListCreateView.as_view(),
        name="scholarship-list",
    ),
    path(
        "scholarships/<int:pk>/",
        ScholarshipDetailView.as_view(),
        name="scholarship-detail",
    ),
]
