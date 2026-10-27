from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from pgvector.django import HnswIndex, VectorField

from apps.core.models import BaseModel

DOCUMENT_ALLOWED_EXTENSIONS = ["pdf", "docx", "txt"]


def validate_document_file_size(file) -> None:
    """Caps uploads (settings.ASSISTANT_MAX_UPLOAD_SIZE_MB) - extract_text
    reads the whole file into memory and hands it to pypdf/python-docx, so an
    unbounded upload is a memory-exhaustion DoS vector, not just a storage
    concern."""
    max_bytes = settings.ASSISTANT_MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file.size > max_bytes:
        raise ValidationError(
            f"File is too large ({file.size / (1024 * 1024):.1f} MB) - the limit is "
            f"{settings.ASSISTANT_MAX_UPLOAD_SIZE_MB} MB."
        )


class Document(BaseModel):
    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    title = models.CharField(max_length=255)
    file = models.FileField(
        upload_to="assistant/documents/",
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=DOCUMENT_ALLOWED_EXTENSIONS),
            validate_document_file_size,
        ],
    )
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.PUBLIC
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    error = models.TextField(blank=True, default="")

    # Set only for documents rendered from a database record (see
    # services.catalog) rather than uploaded as a file. Together they're the
    # stable upsert key that lets a re-run update a record's document in
    # place instead of duplicating it; left null for uploaded documents,
    # which have no source record to key on.
    source_content_type = models.ForeignKey(
        ContentType, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    source_object_id = models.PositiveIntegerField(null=True, blank=True)
    # Hash of the last-rendered content for a catalog-sourced document, so a
    # re-run can tell whether the source record actually changed before
    # paying for re-embedding.
    content_hash = models.CharField(max_length=64, blank=True, default="")
    # Where a user can open the source record itself, e.g. a program detail
    # page - surfaced as the answer's citation instead of a non-clickable
    # document title.
    source_url = models.CharField(max_length=500, blank=True, default="")

    class Meta(BaseModel.Meta):
        unique_together = [("source_content_type", "source_object_id")]

    def __str__(self) -> str:
        return self.title


class DocumentChunk(BaseModel):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="chunks")
    ordinal = models.PositiveIntegerField()
    content = models.TextField()
    token_count = models.PositiveIntegerField(default=0)
    embedding = VectorField(dimensions=settings.ASSISTANT_EMBEDDING_DIM)
    # Denormalized from document so the ANN query can filter without a join.
    visibility = models.CharField(max_length=20, choices=Document.Visibility.choices)

    class Meta(BaseModel.Meta):
        unique_together = ("document", "ordinal")
        indexes = [
            HnswIndex(
                name="chunk_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
            models.Index(fields=["visibility"]),
        ]

    def __str__(self) -> str:
        return f"{self.document_id}#{self.ordinal}"
