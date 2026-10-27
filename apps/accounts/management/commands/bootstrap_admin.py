import os

from django.core.management.base import BaseCommand, CommandError

from apps.accounts import services

REQUIRED_VARS = ["BOOTSTRAP_ADMIN_USERNAME", "BOOTSTRAP_ADMIN_EMAIL", "BOOTSTRAP_ADMIN_PASSWORD"]


class Command(BaseCommand):
    help = (
        "Creates (or promotes) the first admin account from "
        "BOOTSTRAP_ADMIN_USERNAME/EMAIL/PASSWORD env vars, wired through "
        "role=admin + sync_admin_access rather than is_superuser. Intended "
        "to run as a Render one-off job (or once via preDeployCommand) "
        "against the web service - no shell on the host needed. Safe to "
        "rerun."
    )

    def handle(self, *args, **options):
        values = {name: os.environ.get(name) for name in REQUIRED_VARS}
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise CommandError(f"Missing required env var(s): {', '.join(missing)}")

        user = services.bootstrap_admin(
            username=values["BOOTSTRAP_ADMIN_USERNAME"],
            email=values["BOOTSTRAP_ADMIN_EMAIL"],
            password=values["BOOTSTRAP_ADMIN_PASSWORD"],
        )
        self.stdout.write(self.style.SUCCESS(f"Admin ready: {user.username} (role={user.role})"))
