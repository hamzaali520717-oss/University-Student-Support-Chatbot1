import datetime

from django.db.models import QuerySet
from django.utils import timezone

from apps.admissions.models import AdmissionDeadline, AdmissionRequirement, Scholarship


def list_requirements(*, program_code: str | None = None) -> QuerySet[AdmissionRequirement]:
    queryset = AdmissionRequirement.objects.select_related("program").order_by(
        "program__code", "title"
    )
    if program_code:
        queryset = queryset.filter(program__code=program_code)
    return queryset


def list_deadlines() -> QuerySet[AdmissionDeadline]:
    return AdmissionDeadline.objects.select_related("program").order_by("date")


def list_upcoming_deadlines(*, program_code: str | None = None) -> QuerySet[AdmissionDeadline]:
    today: datetime.date = timezone.localdate()
    queryset = list_deadlines().filter(date__gte=today)
    if program_code:
        queryset = queryset.filter(program__code=program_code)
    return queryset


def list_scholarships() -> QuerySet[Scholarship]:
    return Scholarship.objects.all().order_by("name")


def list_active_scholarships() -> QuerySet[Scholarship]:
    return list_scholarships().filter(is_active=True)
