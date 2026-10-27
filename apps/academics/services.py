import datetime

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.academics.models import Attendance, Enrollment, Subject
from apps.accounts.models import StudentProfile


@transaction.atomic
def enroll_student(*, student: StudentProfile, subject: Subject) -> Enrollment:
    if Enrollment.objects.filter(student=student, subject=subject).exists():
        raise ValidationError("Already enrolled in this subject.")
    try:
        # Nested atomic() = a savepoint, so a duplicate-key race (two
        # near-simultaneous enrolls both passing the .exists() check above)
        # only rolls back this insert, not the whole caller's transaction -
        # letting us turn the DB-level race into the same ValidationError a
        # caught-early duplicate raises, instead of an uncaught IntegrityError.
        with transaction.atomic():
            return Enrollment.objects.create(student=student, subject=subject)
    except IntegrityError as exc:
        raise ValidationError("Already enrolled in this subject.") from exc


@transaction.atomic
def record_attendance(
    *, enrollment: Enrollment, date: datetime.date, status: str
) -> Attendance:
    attendance, _ = Attendance.objects.update_or_create(
        enrollment=enrollment, date=date, defaults={"status": status}
    )
    return attendance
