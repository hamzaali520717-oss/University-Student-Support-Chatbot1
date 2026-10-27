from django.db import models

from apps.core.models import BaseModel


class Department(BaseModel):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150, unique=True)

    def __str__(self) -> str:
        return self.code


class Program(BaseModel):
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="programs")
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150)

    def __str__(self) -> str:
        return self.code


class Course(BaseModel):
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="courses")
    code = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=150)

    def __str__(self) -> str:
        return self.code


class Subject(BaseModel):
    program = models.ForeignKey(Program, on_delete=models.PROTECT, related_name="subjects")
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="subjects")
    semester = models.PositiveSmallIntegerField()
    credit_hours = models.PositiveSmallIntegerField()

    class Meta(BaseModel.Meta):
        unique_together = ("program", "course", "semester")

    def __str__(self) -> str:
        return f"{self.course.code} ({self.program.code} S{self.semester})"


class Enrollment(BaseModel):
    student = models.ForeignKey(
        "accounts.StudentProfile", on_delete=models.CASCADE, related_name="enrollments"
    )
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="enrollments")

    class Meta(BaseModel.Meta):
        unique_together = ("student", "subject")

    def __str__(self) -> str:
        return f"{self.student} -> {self.subject}"


class SemesterPlan(BaseModel):
    student = models.ForeignKey(
        "accounts.StudentProfile", on_delete=models.CASCADE, related_name="semester_plans"
    )
    semester = models.PositiveSmallIntegerField()
    subjects = models.ManyToManyField(Subject, related_name="semester_plans")

    class Meta(BaseModel.Meta):
        unique_together = ("student", "semester")

    def __str__(self) -> str:
        return f"{self.student} S{self.semester}"


class Attendance(BaseModel):
    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        LEAVE = "leave", "Leave"

    enrollment = models.ForeignKey(
        Enrollment, on_delete=models.CASCADE, related_name="attendance_records"
    )
    date = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PRESENT)

    class Meta(BaseModel.Meta):
        unique_together = ("enrollment", "date")

    def __str__(self) -> str:
        return f"{self.enrollment} @ {self.date}"
