import hashlib
from typing import Protocol

from django.conf import settings


class EmbeddingClient(Protocol):
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class _BaseEmbeddingClient:
    """Both embed_documents and embed_query just forward to _embed; concrete
    clients only need to set self.dimensions and implement _embed."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        raise NotImplementedError


class GeminiEmbeddingClient(_BaseEmbeddingClient):
    """Default embedding client, using Google's gemini-embedding-001 model."""

    def __init__(self) -> None:
        from google import genai

        self.dimensions = settings.ASSISTANT_EMBEDDING_DIM
        self._model = settings.ASSISTANT_EMBEDDING_MODEL
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)

    def _embed(self, text: str) -> list[float]:
        response = self._client.models.embed_content(
            model=self._model,
            contents=text,
            config={"output_dimensionality": self.dimensions},
        )
        return list(response.embeddings[0].values)


class StubEmbeddingClient(_BaseEmbeddingClient):
    """Deterministic, offline embedding client for tests and dev without an API key."""

    def __init__(self) -> None:
        self.dimensions = settings.ASSISTANT_EMBEDDING_DIM

    def _embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        raw = [digest[i % len(digest)] for i in range(self.dimensions)]
        norm = sum(v * v for v in raw) ** 0.5 or 1.0
        return [v / norm for v in raw]
