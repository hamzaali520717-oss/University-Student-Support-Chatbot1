import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.academics.models import Attendance, Enrollment, Program, Subject
from apps.accounts.models import StudentProfile, User
from apps.finance.models import FeeStatus


class Command(BaseCommand):
    help = (
        "Seed (or refresh) a demo student account for manually exploring the "
        "student portal (/portal/) in a browser. Safe to re-run - updates the "
        "existing row rather than duplicating it. Requires seed_academics to "
        "have been run first (reuses its BSCS program/subjects)."
    )

    USERNAME = "demo_student"
    PASSWORD = "DemoPass123"
    FIRST_NAME = "Laiba"
    LAST_NAME = "Ishaq"
    REGISTRATION_NO = "2026-CS-042"

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            program = Program.objects.get(code="BSCS")
        except Program.DoesNotExist as exc:
            raise CommandError(
                "BSCS program not found - run `python manage.py seed_academics` first."
            ) from exc

        user, _ = User.objects.update_or_create(
            username=self.USERNAME,
            defaults={
                "first_name": self.FIRST_NAME,
                "last_name": self.LAST_NAME,
                "role": User.Role.STUDENT,
            },
        )
        user.set_password(self.PASSWORD)
        user.save()

        student, _ = StudentProfile.objects.update_or_create(
            user=user,
            defaults={"registration_no": self.REGISTRATION_NO, "program": program},
        )

        subject_1 = Subject.objects.get(program=program, course__code="CS101")
        subject_2 = Subject.objects.get(program=program, course__code="CS201")
        enrollment_1, _ = Enrollment.objects.get_or_create(student=student, subject=subject_1)
        Enrollment.objects.get_or_create(student=student, subject=subject_2)

        base_date = timezone.localdate()
        for i in range(20):
            status = Attendance.Status.PRESENT if i < 17 else Attendance.Status.ABSENT
            Attendance.objects.update_or_create(
                enrollment=enrollment_1,
                date=base_date - datetime.timedelta(days=i),
                defaults={"status": status},
            )

        FeeStatus.objects.update_or_create(
            student=student,
            semester=1,
            defaults={
                "amount_due": 60000,
                "amount_paid": 60000,
                "status": FeeStatus.Status.PAID,
            },
        )
        FeeStatus.objects.update_or_create(
            student=student,
            semester=2,
            defaults={
                "amount_due": 65000,
                "amount_paid": 20000,
                "status": FeeStatus.Status.PARTIAL,
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded demo student '{self.USERNAME}' ({self.FIRST_NAME} {self.LAST_NAME}) / "
                f"password '{self.PASSWORD}'."
            )
        )
