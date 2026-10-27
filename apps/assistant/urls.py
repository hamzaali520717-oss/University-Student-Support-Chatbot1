from django.urls import path

from apps.assistant.views import (
    AskView,
    DocumentDetailView,
    DocumentListCreateView,
    ReindexDocumentView,
)

urlpatterns = [
    path("documents/", DocumentListCreateView.as_view(), name="document-list"),
    path("documents/<int:pk>/", DocumentDetailView.as_view(), name="document-detail"),
    path("documents/<int:pk>/reindex/", ReindexDocumentView.as_view(), name="document-reindex"),
    path("ask/", AskView.as_view(), name="ask"),
]
