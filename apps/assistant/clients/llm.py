from dataclasses import dataclass
from typing import Protocol

from django.conf import settings


@dataclass(frozen=True)
class LLMResponse:
    text: str


class LLMClient(Protocol):
    def generate(self, *, system: str, prompt: str) -> LLMResponse: ...


class NonTrainingUnavailable(RuntimeError):
    """Raised when student data must not be sent because no LLM client verified
    safe for non-training use (settings.ASSISTANT_LLM_CLIENT_PRIVATE) is configured."""


class GeminiLLMClient:
    """Default LLM client, using Gemini 2.5 Flash. Only ever selected for
    allow_training=True calls by clients.get_llm_client() - see NonTrainingUnavailable."""

    def __init__(self) -> None:
        from google import genai

        self._model = settings.ASSISTANT_LLM_MODEL
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)

    def generate(self, *, system: str, prompt: str) -> LLMResponse:
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config={"system_instruction": system},
        )
        # The Gemini SDK returns text=None (not an exception) when a response has
        # no candidates or content parts (e.g. safety-blocked) - normalize to "".
        return LLMResponse(text=response.text or "")


class StubLLMClient:
    """Offline LLM client for tests: echoes the prompt so assertions can inspect
    exactly what context/instructions it was given. Never sends data anywhere,
    so it's always safe to use on the non-training path too.

    Set `decline=True` (constructor kwarg, or flip the attribute after
    construction) to make generate() return the honest-fallback sentence
    instead of echoing - an echo can never equal that sentence, so this is
    what end-to-end tests use to exercise the LLM-decline path deterministically."""

    def __init__(self, *, decline: bool = False) -> None:
        self.calls: list[dict] = []
        self.decline = decline

    def generate(self, *, system: str, prompt: str) -> LLMResponse:
        self.calls.append({"system": system, "prompt": prompt})
        if self.decline:
            # Local import: services.answering imports this package (clients)
            # at module load time, so importing I_DONT_KNOW back at module
            # scope here would be circular - deferring the import until
            # generate() actually runs avoids that entirely.
            from apps.assistant.services.answering import I_DONT_KNOW

            return LLMResponse(text=I_DONT_KNOW)
        return LLMResponse(text=f"[stub answer]\n{prompt}")
