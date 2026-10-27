from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import BaseModel


class User(AbstractUser, BaseModel):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        ADMIN = "admin", "Admin"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)


class StudentProfile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    registration_no = models.CharField(max_length=32, unique=True)
    program = models.ForeignKey("academics.Program", on_delete=models.PROTECT, related_name="students")

    def __str__(self) -> str:
        return self.registration_no


class AdminProfile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="admin_profile")

    def __str__(self) -> str:
        return self.user.username
