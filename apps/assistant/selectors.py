from datetime import datetime

from django.db.models import QuerySet
from pgvector.django import CosineDistance

from apps.accounts import selectors as accounts_selectors
from apps.accounts.models import StudentProfile, User
from apps.assistant.models import Document, DocumentChunk


def list_documents() -> QuerySet[Document]:
    return Document.objects.all().order_by("-created_at")


def get_document(*, pk: int) -> Document:
    return Document.objects.get(pk=pk)


def get_asking_student(*, user: User) -> StudentProfile | None:
    """The StudentProfile for the requesting user, or None for anonymous
    requests, admins, or any other non-student user."""
    if not user or not user.is_authenticated:
        return None
    _, profile = accounts_selectors.get_current_user_profile(user=user)
    return profile if isinstance(profile, StudentProfile) else None


def list_stuck_documents(*, cutoff: datetime) -> QuerySet[Document]:
    """Documents still marked PROCESSING past `cutoff` - almost always a worker
    that died or was restarted mid-ingestion rather than a slow job."""
    return Document.objects.filter(status=Document.Status.PROCESSING, updated_at__lt=cutoff)


def search_chunks(
    *, embedding: list[float], limit: int = 6, max_distance: float | None = None
) -> list[DocumentChunk]:
    """ANN search over the public knowledge base only. Anonymous and student
    questions alike search the same public chunks; a student's own records are
    fetched live (see services.context) and never stored as vectors."""
    queryset = (
        DocumentChunk.objects.filter(
            visibility=Document.Visibility.PUBLIC,
            document__status=Document.Status.READY,
        )
        .select_related("document")
        .annotate(distance=CosineDistance("embedding", embedding))
        .order_by("distance")
    )
    if max_distance is not None:
        queryset = queryset.filter(distance__lte=max_distance)
    return list(queryset[:limit])
