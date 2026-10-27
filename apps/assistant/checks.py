from django.conf import settings
from django.core.checks import Error, register


@register("assistant_embedding")
def check_embedding_dimension_matches_column(app_configs, **kwargs):
    from django.db import DatabaseError, connection

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT atttypmod FROM pg_attribute "
                "WHERE attrelid = 'assistant_documentchunk'::regclass AND attname = 'embedding'"
            )
            row = cursor.fetchone()
    except DatabaseError:
        # DB unreachable or not yet migrated (e.g. before the first `migrate`) -
        # this check is opportunistic drift detection, not a hard requirement.
        return []

    if not row or row[0] <= 0:
        return []

    column_dim = row[0]
    if column_dim != settings.ASSISTANT_EMBEDDING_DIM:
        return [
            Error(
                f"ASSISTANT_EMBEDDING_DIM={settings.ASSISTANT_EMBEDDING_DIM} does not match "
                f"the assistant_documentchunk.embedding column width ({column_dim}). Changing "
                "this setting requires a migration to alter the column and re-ingesting all "
                "documents - it cannot just be changed in the environment.",
                id="assistant.E001",
            )
        ]
    return []
