from django.db import models

from apps.academics.models import Program
from apps.core.models import BaseModel


class AdmissionRequirement(BaseModel):
    program = models.ForeignKey(
        Program, on_delete=models.PROTECT, related_name="admission_requirements"
    )
    title = models.CharField(max_length=150)
    description = models.TextField()

    class Meta(BaseModel.Meta):
        unique_together = ("program", "title")

    def __str__(self) -> str:
        return f"{self.program.code}: {self.title}"


class AdmissionDeadline(BaseModel):
    program = models.ForeignKey(
        Program, on_delete=models.PROTECT, related_name="admission_deadlines"
    )
    label = models.CharField(max_length=150)
    date = models.DateField()

    class Meta(BaseModel.Meta):
        unique_together = ("program", "label", "date")

    def __str__(self) -> str:
        return f"{self.program.code} - {self.label} ({self.date})"


class Scholarship(BaseModel):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    eligibility_criteria = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name
