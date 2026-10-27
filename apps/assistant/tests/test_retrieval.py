from django.test import TestCase, override_settings

from apps.assistant.clients.embeddings import StubEmbeddingClient
from apps.assistant.models import Document, DocumentChunk
from apps.assistant.services.retrieval import retrieve

embed = StubEmbeddingClient().embed_query


def _make_ready_chunk(*, content):
    document = Document.objects.create(title="Handbook", status=Document.Status.READY)
    return DocumentChunk.objects.create(
        document=document,
        ordinal=0,
        content=content,
        embedding=embed(content),
        visibility=Document.Visibility.PUBLIC,
    )


class RetrieveMaxDistanceTests(TestCase):
    def test_settings_max_distance_excludes_a_dissimilar_chunk(self):
        _make_ready_chunk(content="The library opens at 8am.")

        with override_settings(ASSISTANT_MAX_DISTANCE=0.0):
            # A near-zero floor should exclude anything but an exact embedding match.
            results = retrieve(query="A totally unrelated question about something else.")

        self.assertEqual(results, [])

    def test_exact_match_survives_the_default_distance_floor(self):
        chunk = _make_ready_chunk(content="The library opens at 8am.")

        results = retrieve(query=chunk.content)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].chunk_id, chunk.id)


class RetrieveDimensionMismatchTests(TestCase):
    def test_embedding_dimension_mismatch_degrades_to_no_results_instead_of_crashing(self):
        _make_ready_chunk(content="The library opens at 8am.")

        with override_settings(ASSISTANT_EMBEDDING_DIM=300):
            # The stored chunk is 768-dim (this test's default); querying with a
            # differently-configured dimension must not raise a DB error.
            results = retrieve(query="What time does the library open?")

        self.assertEqual(results, [])
