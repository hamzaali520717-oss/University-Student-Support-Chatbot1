from collections.abc import Iterable

from django.db.models import Count, QuerySet, Sum

from apps.academics.models import (
    Attendance,
    Course,
    Department,
    Program,
    SemesterPlan,
    Subject,
)
from apps.accounts.models import StudentProfile


def list_departments() -> QuerySet[Department]:
    return Department.objects.all().order_by("code")


def list_programs() -> QuerySet[Program]:
    return Program.objects.select_related("department").order_by("code")


def list_programs_with_stats() -> QuerySet[Program]:
    """Programs annotated with subject_count/total_credit_hours, for display
    contexts that show curriculum size without an extra query per program."""
    return list_programs().annotate(
        subject_count=Count("subjects", distinct=True),
        total_credit_hours=Sum("subjects__credit_hours"),
    )


def unique_departments_from_programs(*, programs) -> list[Department]:
    """Departments represented in the given programs, sorted by code."""
    return sorted({program.department for program in programs}, key=lambda d: d.code)


def list_courses() -> QuerySet[Course]:
    return Course.objects.select_related("department").order_by("code")


def list_subjects(*, program_code: str | None = None) -> QuerySet[Subject]:
    queryset = Subject.objects.select_related("program", "course").order_by(
        "program__code", "semester"
    )
    if program_code:
        queryset = queryset.filter(program__code=program_code)
    return queryset


def list_student_enrollments(*, student: StudentProfile) -> QuerySet:
    return (
        student.enrollments.select_related("subject", "subject__course", "subject__program")
        .order_by("-created_at")
    )


def list_student_attendance(
    *, student: StudentProfile, subject_id: int | None = None
) -> QuerySet[Attendance]:
    queryset = Attendance.objects.filter(enrollment__student=student).select_related(
        "enrollment", "enrollment__subject", "enrollment__subject__course"
    )
    if subject_id is not None:
        queryset = queryset.filter(enrollment__subject_id=subject_id)
    return queryset.order_by("-date")


def summarize_attendance(records: Iterable[Attendance]) -> dict:
    """Present/total/rate for a set of attendance records - the one shared
    source apps.portal's dashboard, apps.portal's AI-panel intents, and
    apps.assistant's RAG grounding context all read from, instead of each
    independently recomputing the same present-out-of-total math."""
    records = list(records)
    total = len(records)
    present = sum(1 for record in records if record.status == Attendance.Status.PRESENT)
    rate = round(present / total * 100) if total else 0
    return {"total": total, "present": present, "rate": rate}


def list_student_semester_plans(*, student: StudentProfile) -> QuerySet[SemesterPlan]:
    return student.semester_plans.prefetch_related("subjects__course").order_by("semester")
