from django.test import TestCase, override_settings

from apps.assistant.checks import check_embedding_dimension_matches_column


class EmbeddingDimensionCheckTests(TestCase):
    def test_no_errors_when_setting_matches_the_migrated_column(self):
        errors = check_embedding_dimension_matches_column(app_configs=None)
        self.assertEqual(errors, [])

    @override_settings(ASSISTANT_EMBEDDING_DIM=999)
    def test_errors_when_setting_drifts_from_the_migrated_column(self):
        errors = check_embedding_dimension_matches_column(app_configs=None)

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "assistant.E001")
        self.assertIn("999", errors[0].msg)
        self.assertIn("768", errors[0].msg)
