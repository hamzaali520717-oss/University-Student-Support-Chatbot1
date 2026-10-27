import datetime

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.academics.models import Department, Program
from apps.admissions.models import Scholarship
from apps.admissions.services import (
    create_deadline,
    create_requirement,
    create_scholarship,
)
from apps.assistant.services.catalog import suppress_catalog_signals, sync_catalog_documents


class Command(BaseCommand):
    help = (
        "Seed sample admission requirements, deadlines, and scholarships for "
        "the BSCS and BSSE programs. Safe to re-run. Catalog signals are "
        "suppressed during the seed so it doesn't fire one embedding call per "
        "row - the whole batch is synced in one pass at the end instead."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        with suppress_catalog_signals():
            self._seed()
        result = sync_catalog_documents()
        self.stdout.write(self.style.SUCCESS("Seeded admissions data."))
        self.stdout.write(
            self.style.SUCCESS(
                f"Synced {result.synced} catalog document(s) ({result.removed} removed)."
            )
        )

    def _seed(self):
        department, _ = Department.objects.get_or_create(
            code="CS", defaults={"name": "Computer Science Department"}
        )
        bscs, _ = Program.objects.get_or_create(
            code="BSCS", defaults={"name": "BS Computer Science", "department": department}
        )
        bsse, _ = Program.objects.get_or_create(
            code="BSSE", defaults={"name": "BS Software Engineering", "department": department}
        )

        requirement_defs = [
            (bscs, "Minimum CGPA", "Minimum CGPA of 3.0/4.0 in intermediate/A-Levels."),
            (bscs, "Entry Test", "Pass the university's CS entry test with 60% or higher."),
            (bsse, "Minimum CGPA", "Minimum CGPA of 2.8/4.0 in intermediate/A-Levels."),
            (bsse, "Portfolio", "Submit a portfolio of prior coding or design projects."),
        ]
        for program, title, description in requirement_defs:
            if not program.admission_requirements.filter(title=title).exists():
                create_requirement(program=program, title=title, description=description)

        deadline_defs = [
            (bscs, "Fall 2026 Application Deadline", datetime.date(2026, 8, 15)),
            (bscs, "Fall 2026 Merit List", datetime.date(2026, 9, 1)),
            (bsse, "Fall 2026 Application Deadline", datetime.date(2026, 8, 20)),
        ]
        for program, label, date in deadline_defs:
            if not program.admission_deadlines.filter(label=label, date=date).exists():
                create_deadline(program=program, label=label, date=date)

        scholarship_defs = [
            (
                "Merit Scholarship",
                "Full tuition waiver for students scoring in the top 5% of the entry test.",
                None,
                "Top 5% of entry test scorers, minimum 3.7 CGPA.",
                True,
            ),
            (
                "Need-Based Grant",
                "Partial tuition support for financially disadvantaged students.",
                50000,
                "Household income below the university's declared threshold.",
                True,
            ),
            (
                "Sports Scholarship",
                "Tuition discount for national-level athletes.",
                25000,
                "Proof of national-level sports participation.",
                False,
            ),
        ]
        for name, description, amount, eligibility_criteria, is_active in scholarship_defs:
            if not Scholarship.objects.filter(name=name).exists():
                create_scholarship(
                    name=name,
                    description=description,
                    amount=amount,
                    eligibility_criteria=eligibility_criteria,
                    is_active=is_active,
                )
