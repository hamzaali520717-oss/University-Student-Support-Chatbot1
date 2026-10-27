from django.conf import settings
from django.utils.module_loading import import_string

from apps.assistant.clients.embeddings import EmbeddingClient
from apps.assistant.clients.llm import LLMClient, NonTrainingUnavailable


def get_embedding_client() -> EmbeddingClient:
    return import_string(settings.ASSISTANT_EMBEDDING_CLIENT)()


def get_llm_client(*, allow_training: bool = True) -> LLMClient:
    """The `allow_training` flag IS the routing decision: it selects which
    configured client class handles the call, rather than being passed through
    to a client that may silently ignore it. When a student's own data is in
    the prompt (allow_training=False), only a client explicitly configured via
    ASSISTANT_LLM_CLIENT_PRIVATE may be used. Google's standard Gemini API key
    tier does not guarantee prompts are excluded from training, so unless an
    operator has attested to a verified non-training deployment by setting
    that variable, this fails closed rather than silently sending student data
    through the default (training-eligible) client."""
    if allow_training:
        path = settings.ASSISTANT_LLM_CLIENT
    else:
        path = settings.ASSISTANT_LLM_CLIENT_PRIVATE
        if not path:
            raise NonTrainingUnavailable(
                "No LLM client is configured for non-training use "
                "(set ASSISTANT_LLM_CLIENT_PRIVATE to a client verified safe for "
                "this purpose); refusing to send student data to the default client."
            )
    return import_string(path)()
