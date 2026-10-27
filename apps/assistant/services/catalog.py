import hashlib
import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.urls import reverse

from apps.academics import selectors as academics_selectors
from apps.admissions import selectors as admissions_selectors
from apps.admissions.models import AdmissionDeadline, Scholarship
from apps.academics.models import Program
from apps.assistant import clients
from apps.assistant.models import Document, DocumentChunk
from apps.finance import selectors as finance_selectors
from apps.finance.models import FeeStructure

_signal_state = threading.local()


@contextmanager
def suppress_catalog_signals():
    """Suppresses the post_save/post_delete-triggered single-record sync (see
    apps.assistant.signals) for the duration of the block. Use around bulk
    data loads - a seed command or backfill script that writes many catalog
    rows in one go - so each row doesn't schedule its own embedding call;
    follow up with an explicit sync_catalog_documents() call instead."""
    previous = getattr(_signal_state, "suppressed", False)
    _signal_state.suppressed = True
    try:
        yield
    finally:
        _signal_state.suppressed = previous


def catalog_signals_suppressed() -> bool:
    return getattr(_signal_state, "suppressed", False)


@dataclass(frozen=True)
class RenderedChunk:
    ordinal: int
    text: str


@dataclass(frozen=True)
class RenderedSource:
    """One database record rendered into the coherent natural-language
    chunk(s) that will become a single Document's DocumentChunks."""

    source: models.Model
    title: str
    citation_url: str
    chunks: list[RenderedChunk]


def render_program(*, program: Program) -> RenderedSource:
    """Folds a program's subjects and admission requirements into one
    rendered source. Kept as a single chunk unless the combined text would
    exceed the standard chunk size, in which case curriculum and admission
    requirements split into two chunks along their natural seam."""
    overview_lines = [
        f"{program.name} ({program.code}) is offered by the {program.department.name} department."
    ]
    subjects_by_semester: dict[int, list] = defaultdict(list)
    for subject in academics_selectors.list_subjects(program_code=program.code):
        subjects_by_semester[subject.semester].append(subject)
    if subjects_by_semester:
        overview_lines.append("Subjects offered by semester:")
        for semester in sorted(subjects_by_semester):
            listing = ", ".join(
                f"{subject.course.title} ({subject.course.code}, {subject.credit_hours} credit hours)"
                for subject in subjects_by_semester[semester]
            )
            overview_lines.append(f"- Semester {semester}: {listing}")
    else:
        overview_lines.append("No subjects are on record for this program yet.")
    overview_text = "\n".join(overview_lines)

    requirements = list(admissions_selectors.list_requirements(program_code=program.code))
    requirements_text = ""
    if requirements:
        requirement_lines = [f"Admission requirements for {program.name} ({program.code}):"]
        requirement_lines += [f"- {r.title}: {r.description}" for r in requirements]
        requirements_text = "\n".join(requirement_lines)

    if not requirements_text:
        chunks = [RenderedChunk(ordinal=0, text=overview_text)]
    else:
        combined_words = len(overview_text.split()) + len(requirements_text.split())
        if combined_words <= settings.ASSISTANT_CHUNK_TOKENS:
            chunks = [RenderedChunk(ordinal=0, text=f"{overview_text}\n\n{requirements_text}")]
        else:
            chunks = [
                RenderedChunk(ordinal=0, text=overview_text),
                RenderedChunk(ordinal=1, text=requirements_text),
            ]

    return RenderedSource(
        source=program,
        title=f"{program.name} ({program.code}) program overview",
        citation_url=reverse("website:program-detail", kwargs={"code": program.code}),
        chunks=chunks,
    )


def render_fee_structure(*, fee_structure: FeeStructure) -> RenderedSource:
    program = fee_structure.program
    lines = [
        f"The tuition fee for {program.name} ({program.code}), semester "
        f"{fee_structure.semester}, is {fee_structure.amount}."
    ]
    if fee_structure.breakdown:
        parts = ", ".join(f"{key}: {value}" for key, value in fee_structure.breakdown.items())
        lines.append(f"Breakdown: {parts}.")
    return RenderedSource(
        source=fee_structure,
        title=f"{program.name} semester {fee_structure.semester} fee structure",
        citation_url=reverse("website:program-detail", kwargs={"code": program.code}),
        chunks=[RenderedChunk(ordinal=0, text="\n".join(lines))],
    )


def render_admission_deadline(*, deadline: AdmissionDeadline) -> RenderedSource:
    program = deadline.program
    text = (
        f"The {deadline.label} deadline for {program.name} ({program.code}) admissions "
        f"is {deadline.date:%B %d, %Y}."
    )
    return RenderedSource(
        source=deadline,
        title=f"{program.name} admission deadline: {deadline.label}",
        citation_url=reverse("website:program-detail", kwargs={"code": program.code}),
        chunks=[RenderedChunk(ordinal=0, text=text)],
    )


def render_scholarship(*, scholarship: Scholarship) -> RenderedSource:
    lines = [f"{scholarship.name} scholarship: {scholarship.description}"]
    if scholarship.amount is not None:
        lines.append(f"Amount: {scholarship.amount}.")
    if scholarship.eligibility_criteria:
        lines.append(f"Eligibility: {scholarship.eligibility_criteria}")
    return RenderedSource(
        source=scholarship,
        title=f"{scholarship.name} scholarship",
        citation_url=reverse("website:scholarship-list"),
        chunks=[RenderedChunk(ordinal=0, text="\n".join(lines))],
    )


_RENDERERS = {
    Program: lambda obj: render_program(program=obj),
    FeeStructure: lambda obj: render_fee_structure(fee_structure=obj),
    AdmissionDeadline: lambda obj: render_admission_deadline(deadline=obj),
    Scholarship: lambda obj: render_scholarship(scholarship=obj),
}


def render_source(*, source: models.Model) -> RenderedSource:
    return _RENDERERS[type(source)](source)


def list_catalog_sources() -> list[RenderedSource]:
    """Every public catalog record worth making answerable, already filtered
    to active/upcoming - programs and fee structures have no such flag so all
    of them are included."""
    sources = [render_program(program=program) for program in academics_selectors.list_programs()]
    sources += [
        render_fee_structure(fee_structure=fee_structure)
        for fee_structure in finance_selectors.list_fee_structures()
    ]
    sources += [
        render_admission_deadline(deadline=deadline)
        for deadline in admissions_selectors.list_upcoming_deadlines()
    ]
    sources += [
        render_scholarship(scholarship=scholarship)
        for scholarship in admissions_selectors.list_active_scholarships()
    ]
    return sources


def _content_hash(*, chunks: list[RenderedChunk]) -> str:
    joined = "\x00".join(chunk.text for chunk in chunks)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _batch_sources(
    pending: list[tuple[RenderedSource, str]], batch_size: int
):
    """Groups whole sources into batches capped at batch_size chunks each,
    never splitting one source's chunks across two embedding calls - so a
    batch can be embedded and written to the database as one unit."""
    batch: list[tuple[RenderedSource, str]] = []
    batch_chunk_count = 0
    for item in pending:
        rendered, _ = item
        if batch and batch_chunk_count + len(rendered.chunks) > batch_size:
            yield batch
            batch, batch_chunk_count = [], 0
        batch.append(item)
        batch_chunk_count += len(rendered.chunks)
    if batch:
        yield batch


def _is_rate_limit_error(exc: Exception) -> bool:
    """Best-effort detection across embedding client implementations: checks
    a numeric code/status_code attribute (the google-genai SDK's ClientError
    exposes `.code`), falling back to sniffing the message for Google's 429 /
    RESOURCE_EXHAUSTED markers."""
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if code == 429:
        return True
    message = str(exc)
    return "429" in message or "RESOURCE_EXHAUSTED" in message


def _embed_with_backoff(*, client, texts: list[str]) -> list[list[float]]:
    max_retries = settings.ASSISTANT_CATALOG_MAX_RETRIES
    base_delay = settings.ASSISTANT_CATALOG_RETRY_BASE_DELAY
    for attempt in range(max_retries + 1):
        try:
            return client.embed_documents(texts)
        except Exception as exc:
            if not _is_rate_limit_error(exc) or attempt == max_retries:
                raise
            time.sleep(base_delay * (2**attempt))


@transaction.atomic
def _upsert_document(
    *, rendered: RenderedSource, content_hash: str, embeddings: list[list[float]]
) -> Document:
    content_type = ContentType.objects.get_for_model(type(rendered.source))
    document, _ = Document.objects.get_or_create(
        source_content_type=content_type,
        source_object_id=rendered.source.pk,
        defaults={"title": rendered.title, "visibility": Document.Visibility.PUBLIC},
    )
    document.title = rendered.title
    document.content_hash = content_hash
    document.source_url = rendered.citation_url
    document.status = Document.Status.READY
    document.error = ""
    document.save()

    document.chunks.all().delete()
    DocumentChunk.objects.bulk_create(
        DocumentChunk(
            document=document,
            ordinal=chunk.ordinal,
            content=chunk.text,
            token_count=len(chunk.text.split()),
            embedding=embedding,
            visibility=Document.Visibility.PUBLIC,
        )
        for chunk, embedding in zip(rendered.chunks, embeddings)
    )
    return document


def sync_source(*, source: models.Model) -> Document:
    """Renders and (re-)embeds a single catalog record in place - the
    signal-driven counterpart to sync_catalog_documents' batch pass (see
    apps.assistant.signals). Skips the embedding call if the rendered content
    is unchanged, since a save() can fire without the rendered fields
    actually changing."""
    rendered = render_source(source=source)
    content_hash = _content_hash(chunks=rendered.chunks)
    content_type = ContentType.objects.get_for_model(type(source))
    existing = Document.objects.filter(
        source_content_type=content_type, source_object_id=source.pk
    ).first()
    if existing and existing.content_hash == content_hash and existing.status == Document.Status.READY:
        return existing

    client = clients.get_embedding_client()
    embeddings = _embed_with_backoff(client=client, texts=[chunk.text for chunk in rendered.chunks])
    return _upsert_document(rendered=rendered, content_hash=content_hash, embeddings=embeddings)


def delete_synced_document(*, content_type_id: int, object_id: int) -> None:
    """Removes the Document (and its chunks, via cascade) synced from a
    catalog record identified by its (content_type, object_id) key - the
    signal-driven counterpart for deletions. Takes the raw key rather than a
    live model instance: Django clears instance.pk immediately after
    delete() returns, before a transaction.on_commit-deferred callback would
    run, so the key must be captured eagerly at signal-fire time instead."""
    Document.objects.filter(
        source_content_type_id=content_type_id, source_object_id=object_id
    ).delete()


@dataclass(frozen=True)
class CatalogSyncResult:
    synced: int
    removed: int


def sync_catalog_documents() -> CatalogSyncResult:
    """Renders the public catalog (programs with their subjects and admission
    requirements, fee structures, upcoming admission deadlines, active
    scholarships) into Document/DocumentChunk rows and embeds them, upserting
    by (content_type, object_id) so re-runs update a changed record in place
    instead of duplicating it. Sources whose rendered content hasn't changed
    since the last run are skipped before any embedding call is made, so a
    repeat run only pays for what actually changed. Also removes any
    previously-synced Document whose source row no longer exists (e.g.
    deleted while catalog signals were suppressed, or before signals
    existed), so deleted records don't linger in the assistant's knowledge
    base forever - day-to-day, apps.assistant.signals keeps this in sync
    immediately per edit/delete; this pass is the batch/backfill/cleanup
    path."""
    sources = list_catalog_sources()

    existing_by_key = {
        (doc.source_content_type_id, doc.source_object_id): doc
        for doc in Document.objects.filter(source_content_type__isnull=False)
    }

    pending: list[tuple[RenderedSource, str]] = []
    current_keys: set[tuple[int, int]] = set()
    for rendered in sources:
        content_type_id = ContentType.objects.get_for_model(type(rendered.source)).id
        current_keys.add((content_type_id, rendered.source.pk))
        content_hash = _content_hash(chunks=rendered.chunks)
        existing = existing_by_key.get((content_type_id, rendered.source.pk))
        if existing and existing.content_hash == content_hash and existing.status == Document.Status.READY:
            continue
        pending.append((rendered, content_hash))

    client = clients.get_embedding_client()
    synced = 0
    batches = list(_batch_sources(pending, settings.ASSISTANT_CATALOG_BATCH_SIZE))
    for i, batch in enumerate(batches):
        texts = [chunk.text for rendered, _ in batch for chunk in rendered.chunks]
        embeddings = _embed_with_backoff(client=client, texts=texts)

        offset = 0
        for rendered, content_hash in batch:
            count = len(rendered.chunks)
            _upsert_document(
                rendered=rendered,
                content_hash=content_hash,
                embeddings=embeddings[offset : offset + count],
            )
            offset += count
            synced += 1

        if i + 1 < len(batches) and settings.ASSISTANT_CATALOG_BATCH_DELAY_SECONDS:
            time.sleep(settings.ASSISTANT_CATALOG_BATCH_DELAY_SECONDS)

    orphaned_ids = [doc.id for key, doc in existing_by_key.items() if key not in current_keys]
    if orphaned_ids:
        Document.objects.filter(id__in=orphaned_ids).delete()

    return CatalogSyncResult(synced=synced, removed=len(orphaned_ids))
