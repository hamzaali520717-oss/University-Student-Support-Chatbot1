import tempfile

from .base import *  # noqa: F401,F403

DEBUG = False

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

MEDIA_ROOT = tempfile.mkdtemp(prefix="university-portal-test-media-")

# Offline, deterministic clients so RAG tests run without network calls or cost.
ASSISTANT_EMBEDDING_CLIENT = "apps.assistant.clients.embeddings.StubEmbeddingClient"
ASSISTANT_LLM_CLIENT = "apps.assistant.clients.llm.StubLLMClient"
# The stub never sends data anywhere, so it's also safe on the non-training path.
ASSISTANT_LLM_CLIENT_PRIVATE = "apps.assistant.clients.llm.StubLLMClient"
ASSISTANT_INGEST_SYNC = True
# No real backoff/rate-limiting to wait out against the stub client.
ASSISTANT_CATALOG_BATCH_DELAY_SECONDS = 0
ASSISTANT_CATALOG_RETRY_BASE_DELAY = 0
