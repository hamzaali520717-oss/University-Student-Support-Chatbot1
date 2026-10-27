import logging
from dataclasses import dataclass

from django.conf import settings
from django.db import DataError

from apps.assistant import clients, selectors

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: int
    document_id: int
    document_title: str
    content: str
    distance: float


def retrieve(*, query: str, limit: int | None = None) -> list[RetrievedChunk]:
    """Searches the public knowledge base only. Student-specific data is never
    embedded; it is fetched live by services.context."""
    embedding = clients.get_embedding_client().embed_query(query)
    try:
        chunks = selectors.search_chunks(
            embedding=embedding,
            limit=limit or settings.ASSISTANT_RETRIEVAL_LIMIT,
            max_distance=settings.ASSISTANT_MAX_DISTANCE,
        )
    except DataError:
        # Query embedding width doesn't match the stored column (e.g.
        # ASSISTANT_EMBEDDING_DIM was changed without a migration + full
        # re-ingestion) - degrade to "no public KB results" instead of a 500.
        logger.exception("Vector search failed, likely an embedding dimension mismatch.")
        return []
    return [
        RetrievedChunk(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            document_title=chunk.document.title,
            content=chunk.content,
            distance=chunk.distance,
        )
        for chunk in chunks
    ]
