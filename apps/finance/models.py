from django.db import models

from apps.academics.models import Program
from apps.accounts.models import StudentProfile
from apps.core.models import BaseModel


class FeeStructure(BaseModel):
    program = models.ForeignKey(Program, on_delete=models.PROTECT, related_name="fee_structures")
    semester = models.PositiveSmallIntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    breakdown = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        unique_together = ("program", "semester")

    def __str__(self) -> str:
        return f"{self.program.code} S{self.semester}"


class FeeStatus(BaseModel):
    class Status(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        PARTIAL = "partial", "Partial"
        PAID = "paid", "Paid"

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="fee_statuses")
    semester = models.PositiveSmallIntegerField()
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.UNPAID)

    class Meta(BaseModel.Meta):
        unique_together = ("student", "semester")
        verbose_name_plural = "Fee statuses"

    def __str__(self) -> str:
        return f"{self.student} S{self.semester} ({self.status})"
