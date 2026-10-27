from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.academics.models import Department, Program
from apps.accounts.models import StudentProfile, User
from apps.accounts.services import register_student


class RegisterStudentTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=self.department, code="CS", name="Computer Science"
        )

    def _register(self, **overrides):
        defaults = dict(
            username="newstudent",
            email="new@example.com",
            password="a-strong-passw0rd",
            first_name="New",
            last_name="Student",
            registration_no="REG-1",
            program=self.program,
        )
        defaults.update(overrides)
        return register_student(**defaults)

    def test_creates_user_and_student_profile(self):
        user = self._register()
        self.assertEqual(user.role, User.Role.STUDENT)
        self.assertTrue(user.check_password("a-strong-passw0rd"))
        profile = StudentProfile.objects.get(user=user)
        self.assertEqual(profile.registration_no, "REG-1")
        self.assertEqual(profile.program, self.program)

    def test_weak_password_rejected_and_rolled_back(self):
        with self.assertRaises(ValidationError):
            self._register(password="123")
        self.assertFalse(User.objects.filter(username="newstudent").exists())

    def test_duplicate_registration_no_rolled_back(self):
        self._register()
        with self.assertRaises(Exception):
            self._register(username="anotherstudent", email="another@example.com")
        self.assertFalse(User.objects.filter(username="anotherstudent").exists())
