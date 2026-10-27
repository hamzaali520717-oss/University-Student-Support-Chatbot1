import datetime
from decimal import Decimal

from django.db import transaction

from apps.academics.models import Program
from apps.admissions.models import AdmissionDeadline, AdmissionRequirement, Scholarship


@transaction.atomic
def create_requirement(
    *, program: Program, title: str, description: str
) -> AdmissionRequirement:
    return AdmissionRequirement.objects.create(
        program=program, title=title, description=description
    )


@transaction.atomic
def update_requirement(
    *, requirement: AdmissionRequirement, **fields
) -> AdmissionRequirement:
    for field, value in fields.items():
        setattr(requirement, field, value)
    requirement.save(update_fields=[*fields.keys(), "updated_at"])
    return requirement


@transaction.atomic
def delete_requirement(*, requirement: AdmissionRequirement) -> None:
    requirement.delete()


@transaction.atomic
def create_deadline(
    *, program: Program, label: str, date: datetime.date
) -> AdmissionDeadline:
    return AdmissionDeadline.objects.create(program=program, label=label, date=date)


@transaction.atomic
def update_deadline(*, deadline: AdmissionDeadline, **fields) -> AdmissionDeadline:
    for field, value in fields.items():
        setattr(deadline, field, value)
    deadline.save(update_fields=[*fields.keys(), "updated_at"])
    return deadline


@transaction.atomic
def delete_deadline(*, deadline: AdmissionDeadline) -> None:
    deadline.delete()


@transaction.atomic
def create_scholarship(
    *,
    name: str,
    description: str,
    amount: Decimal | None = None,
    eligibility_criteria: str = "",
    is_active: bool = True,
) -> Scholarship:
    return Scholarship.objects.create(
        name=name,
        description=description,
        amount=amount,
        eligibility_criteria=eligibility_criteria,
        is_active=is_active,
    )


@transaction.atomic
def update_scholarship(*, scholarship: Scholarship, **fields) -> Scholarship:
    for field, value in fields.items():
        setattr(scholarship, field, value)
    scholarship.save(update_fields=[*fields.keys(), "updated_at"])
    return scholarship


@transaction.atomic
def delete_scholarship(*, scholarship: Scholarship) -> None:
    scholarship.delete()
