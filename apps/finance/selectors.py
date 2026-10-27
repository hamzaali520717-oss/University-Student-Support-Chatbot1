from django.db.models import QuerySet

from apps.accounts.models import StudentProfile
from apps.finance.models import FeeStatus, FeeStructure


def list_fee_structures(*, program_code: str | None = None) -> QuerySet[FeeStructure]:
    queryset = FeeStructure.objects.select_related("program").order_by(
        "program__code", "semester"
    )
    if program_code:
        queryset = queryset.filter(program__code=program_code)
    return queryset


def list_student_fee_statuses(*, student: StudentProfile) -> QuerySet[FeeStatus]:
    return FeeStatus.objects.filter(student=student).select_related("student").order_by(
        "semester"
    )


def list_fee_statuses() -> QuerySet[FeeStatus]:
    return FeeStatus.objects.select_related("student", "student__user").order_by(
        "student__registration_no", "semester"
    )


def fee_status_outstanding(fee_status: FeeStatus):
    """Amount still owed on a single fee-status record - the one shared source
    apps.portal's dashboard and AI-panel intents both read from, instead of
    each independently recomputing amount_due - amount_paid."""
    return fee_status.amount_due - fee_status.amount_paid


def is_fee_status_settled(fee_status: FeeStatus) -> bool:
    return fee_status.status == FeeStatus.Status.PAID
