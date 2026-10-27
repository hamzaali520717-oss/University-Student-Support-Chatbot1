from django.apps import AppConfig


class AssistantConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.assistant"
    label = "assistant"

    def ready(self) -> None:
        from apps.assistant import checks  # noqa: F401
        from apps.assistant import signals  # noqa: F401
