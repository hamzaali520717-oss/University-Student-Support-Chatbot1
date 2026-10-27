from django.core.management.base import BaseCommand

from apps.assistant import services


class Command(BaseCommand):
    help = (
        "Mark assistant documents stuck in PROCESSING (from a worker that died "
        "or restarted mid-ingestion) as FAILED so they can be reindexed. Safe "
        "to run repeatedly - intended to be scheduled periodically (cron / "
        "k8s CronJob), since this project has no background task supervisor."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--timeout-minutes",
            type=int,
            default=30,
            help="How long a document may sit in PROCESSING before it's considered stuck.",
        )

    def handle(self, *args, **options):
        count = services.recover_stuck_documents(timeout_minutes=options["timeout_minutes"])
        self.stdout.write(self.style.SUCCESS(f"Recovered {count} stuck document(s)."))
