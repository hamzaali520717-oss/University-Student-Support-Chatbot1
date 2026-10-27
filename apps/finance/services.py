from decimal import Decimal

from django.db import transaction

from apps.academics.models import Program
from apps.accounts.models import StudentProfile
from apps.finance.models import FeeStatus, FeeStructure


@transaction.atomic
def create_fee_structure(
    *, program: Program, semester: int, amount: Decimal, breakdown: dict | None = None
) -> FeeStructure:
    return FeeStructure.objects.create(
        program=program, semester=semester, amount=amount, breakdown=breakdown or {}
    )


@transaction.atomic
def update_fee_structure(*, fee_structure: FeeStructure, **fields) -> FeeStructure:
    for field, value in fields.items():
        setattr(fee_structure, field, value)
    fee_structure.save(update_fields=[*fields.keys(), "updated_at"])
    return fee_structure


@transaction.atomic
def delete_fee_structure(*, fee_structure: FeeStructure) -> None:
    fee_structure.delete()


def _status_for(*, amount_due: Decimal, amount_paid: Decimal) -> str:
    amount_due = Decimal(amount_due)
    amount_paid = Decimal(amount_paid)
    if amount_paid <= 0:
        return FeeStatus.Status.UNPAID
    if amount_paid >= amount_due:
        return FeeStatus.Status.PAID
    return FeeStatus.Status.PARTIAL


@transaction.atomic
def create_fee_status(
    *,
    student: StudentProfile,
    semester: int,
    amount_due: Decimal,
    amount_paid: Decimal = Decimal("0"),
) -> FeeStatus:
    return FeeStatus.objects.create(
        student=student,
        semester=semester,
        amount_due=amount_due,
        amount_paid=amount_paid,
        status=_status_for(amount_due=amount_due, amount_paid=amount_paid),
    )


@transaction.atomic
def record_payment(*, fee_status: FeeStatus, amount: Decimal) -> FeeStatus:
    fee_status.amount_paid = Decimal(fee_status.amount_paid) + Decimal(amount)
    fee_status.status = _status_for(
        amount_due=fee_status.amount_due, amount_paid=fee_status.amount_paid
    )
    fee_status.save(update_fields=["amount_paid", "status", "updated_at"])
    return fee_status


@transaction.atomic
def update_fee_status(*, fee_status: FeeStatus, **fields) -> FeeStatus:
    for field, value in fields.items():
        setattr(fee_status, field, value)
    fee_status.save(update_fields=[*fields.keys(), "updated_at"])
    return fee_status
