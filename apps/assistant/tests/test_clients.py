from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.assistant import clients
from apps.assistant.clients.embeddings import StubEmbeddingClient
from apps.assistant.clients.llm import GeminiLLMClient, NonTrainingUnavailable, StubLLMClient
from apps.assistant.services.answering import I_DONT_KNOW


class StubEmbeddingClientTests(TestCase):
    def setUp(self):
        self.client = StubEmbeddingClient()

    def test_embedding_has_configured_dimensions(self):
        vector = self.client.embed_query("hello world")
        self.assertEqual(len(vector), self.client.dimensions)

    def test_same_text_produces_identical_embedding(self):
        first = self.client.embed_query("the library opens at 8am")
        second = self.client.embed_query("the library opens at 8am")
        self.assertEqual(first, second)

    def test_different_text_produces_different_embedding(self):
        first = self.client.embed_query("the library opens at 8am")
        second = self.client.embed_query("tuition is due on the 1st")
        self.assertNotEqual(first, second)

    def test_embed_documents_matches_embed_query_per_text(self):
        texts = ["alpha", "beta"]
        documents = self.client.embed_documents(texts)
        self.assertEqual(documents[0], self.client.embed_query("alpha"))
        self.assertEqual(documents[1], self.client.embed_query("beta"))


class StubLLMClientTests(TestCase):
    def test_generate_records_call_and_echoes_prompt(self):
        client = StubLLMClient()
        response = client.generate(system="be helpful", prompt="What are the library hours?")
        self.assertIn("What are the library hours?", response.text)
        self.assertEqual(len(client.calls), 1)

    def test_decline_mode_returns_the_honest_fallback_instead_of_echoing(self):
        # An echoing stub can never equal the decline sentence, so it can
        # never exercise apps.assistant.services.answering._declined() end to
        # end - decline mode exists so real (non-mocked) pipeline tests can.
        client = StubLLMClient(decline=True)
        response = client.generate(system="be helpful", prompt="What is my favorite color?")
        self.assertEqual(response.text, I_DONT_KNOW)
        self.assertEqual(len(client.calls), 1)


class GetLlmClientRoutingTests(TestCase):
    """allow_training must be a real routing decision, not a value threaded
    through and ignored - see clients.get_llm_client."""

    @override_settings(
        ASSISTANT_LLM_CLIENT="apps.assistant.clients.llm.StubLLMClient",
        ASSISTANT_LLM_CLIENT_PRIVATE="apps.assistant.clients.llm.StubLLMClient",
    )
    def test_allow_training_true_uses_the_public_client(self):
        client = clients.get_llm_client(allow_training=True)
        self.assertIsInstance(client, StubLLMClient)

    @override_settings(
        ASSISTANT_LLM_CLIENT="apps.assistant.clients.llm.StubLLMClient",
        ASSISTANT_LLM_CLIENT_PRIVATE="apps.assistant.clients.llm.StubLLMClient",
    )
    def test_allow_training_false_uses_the_configured_private_client(self):
        client = clients.get_llm_client(allow_training=False)
        self.assertIsInstance(client, StubLLMClient)

    @override_settings(ASSISTANT_LLM_CLIENT_PRIVATE="")
    def test_allow_training_false_fails_closed_when_no_private_client_configured(self):
        with self.assertRaises(NonTrainingUnavailable):
            clients.get_llm_client(allow_training=False)


class GeminiLLMClientNoneTextTests(TestCase):
    @patch("google.genai.Client")
    def test_none_response_text_is_normalized_to_empty_string(self, mock_client_cls):
        # The Gemini SDK returns text=None (not an exception) when a response
        # has no candidates/content parts, e.g. a safety-blocked reply.
        mock_response = MagicMock()
        mock_response.text = None
        mock_client_cls.return_value.models.generate_content.return_value = mock_response

        result = GeminiLLMClient().generate(system="s", prompt="p")

        self.assertEqual(result.text, "")
