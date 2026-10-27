import io
import threading
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.assistant import clients, selectors
from apps.assistant.models import Document, DocumentChunk


def _reject_catalog_synced(*, document: Document) -> None:
    """Catalog-synced documents (see apps.assistant.services.catalog) are
    regenerated automatically from their source record and owned exclusively
    by that sync process's upsert key - reindexing or deleting one directly
    would fight the next sync. Enforced here, not just in the admin, so
    every caller (management commands, the assistant API, a shell session)
    is protected, not just the Django admin UI."""
    if document.source_content_type_id is not None:
        raise PermissionDenied(
            f"Document {document.pk!r} is synced from a catalog record and can't be "
            "reindexed or deleted directly - edit the source record instead."
        )


def extract_text(*, document: Document) -> str:
    if not document.file:
        raise ValueError("Document has no file to extract text from.")

    name = document.file.name.lower()
    document.file.open("rb")
    try:
        raw = document.file.read()
    finally:
        document.file.close()

    if name.endswith(".pdf"):
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(raw))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if name.endswith(".docx"):
        import docx

        doc = docx.Document(io.BytesIO(raw))
        return "\n".join(paragraph.text for paragraph in doc.paragraphs)

    return raw.decode("utf-8", errors="ignore")


def chunk_text(*, text: str, target_tokens: int = 500, overlap_tokens: int = 50) -> list[str]:
    """Splits text into overlapping chunks, approximating tokens by whitespace-
    separated words."""
    words = text.split()
    if not words:
        return []

    step = max(target_tokens - overlap_tokens, 1)
    chunks = []
    for start in range(0, len(words), step):
        chunk_words = words[start : start + target_tokens]
        chunks.append(" ".join(chunk_words))
        if start + target_tokens >= len(words):
            break
    return chunks


def ingest_document(*, document: Document) -> Document:
    document.status = Document.Status.PROCESSING
    document.save(update_fields=["status", "updated_at"])

    try:
        text = extract_text(document=document)
        texts = chunk_text(
            text=text,
            target_tokens=settings.ASSISTANT_CHUNK_TOKENS,
            overlap_tokens=settings.ASSISTANT_CHUNK_OVERLAP_TOKENS,
        )
        if not texts:
            raise ValueError("No extractable text in document.")

        embeddings = clients.get_embedding_client().embed_documents(texts)
        with transaction.atomic():
            document.chunks.all().delete()
            DocumentChunk.objects.bulk_create(
                DocumentChunk(
                    document=document,
                    ordinal=ordinal,
                    content=chunk,
                    token_count=len(chunk.split()),
                    embedding=embedding,
                    visibility=document.visibility,
                )
                for ordinal, (chunk, embedding) in enumerate(zip(texts, embeddings))
            )
            document.status = Document.Status.READY
            document.error = ""
            document.save(update_fields=["status", "error", "updated_at"])
    except Exception as exc:
        document.status = Document.Status.FAILED
        document.error = str(exc)
        document.save(update_fields=["status", "error", "updated_at"])

    return document


def queue_ingestion(*, document: Document) -> None:
    def _run() -> None:
        ingest_document(document=document)

    if settings.ASSISTANT_INGEST_SYNC:
        transaction.on_commit(_run)
    else:
        transaction.on_commit(lambda: threading.Thread(target=_run, daemon=True).start())


@transaction.atomic
def create_document(
    *,
    title: str,
    file=None,
    visibility: str = Document.Visibility.PUBLIC,
) -> Document:
    document = Document.objects.create(title=title, file=file, visibility=visibility)
    queue_ingestion(document=document)
    return document


@transaction.atomic
def reindex_document(*, document: Document) -> Document:
    _reject_catalog_synced(document=document)
    document.status = Document.Status.PENDING
    document.error = ""
    document.save(update_fields=["status", "error", "updated_at"])
    queue_ingestion(document=document)
    return document


@transaction.atomic
def delete_document(*, document: Document) -> None:
    _reject_catalog_synced(document=document)
    document.delete()


@transaction.atomic
def recover_stuck_documents(*, timeout_minutes: int = 30) -> int:
    """Marks documents left in PROCESSING past the timeout as FAILED so they
    show up for an admin to reindex. Ingestion runs on a fire-and-forget
    background thread with no supervisor, so a worker restart/crash mid-job
    would otherwise leave the document stuck at PROCESSING forever. Intended
    to be run periodically (e.g. a cron job invoking the
    recover_stuck_ingestions management command)."""
    cutoff = timezone.now() - timedelta(minutes=timeout_minutes)
    return selectors.list_stuck_documents(cutoff=cutoff).update(
        status=Document.Status.FAILED,
        error="Ingestion did not complete (worker restarted or crashed); reindex to retry.",
        updated_at=timezone.now(),
    )
