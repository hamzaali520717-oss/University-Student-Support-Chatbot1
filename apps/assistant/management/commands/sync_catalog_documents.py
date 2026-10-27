from django.core.management.base import BaseCommand

from apps.assistant import services


class Command(BaseCommand):
    help = (
        "Renders the public catalog (programs with their subjects and "
        "admission requirements, fee structures, upcoming admission "
        "deadlines, active scholarships) into Document/DocumentChunk rows "
        "and embeds them. Upserts by source record, so re-runs update "
        "changed records in place instead of duplicating them, and skip "
        "unchanged records without calling the embedding API. Safe to run "
        "repeatedly - schedule it (e.g. periodic cron / k8s CronJob) so the "
        "assistant's public catalog knowledge stays in sync with the "
        "database."
    )

    def handle(self, *args, **options):
        result = services.sync_catalog_documents()
        self.stdout.write(
            self.style.SUCCESS(
                f"Synced {result.synced} catalog document(s); "
                f"removed {result.removed} orphaned document(s)."
            )
        )
