from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.academics.models import Department, Program
from apps.accounts.models import AdminProfile, StudentProfile, User


class UserModelTests(TestCase):
    def test_default_role_is_student(self):
        user = User.objects.create_user(username="stu", password="pw")
        self.assertEqual(user.role, User.Role.STUDENT)


class StudentProfileModelTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=self.department, code="CS", name="Computer Science"
        )

    def test_registration_no_must_be_unique(self):
        user1 = User.objects.create_user(username="stu1", password="pw")
        user2 = User.objects.create_user(username="stu2", password="pw")
        StudentProfile.objects.create(user=user1, registration_no="REG-1", program=self.program)
        with self.assertRaises(IntegrityError), transaction.atomic():
            StudentProfile.objects.create(user=user2, registration_no="REG-1", program=self.program)

    def test_user_can_have_only_one_student_profile(self):
        user = User.objects.create_user(username="stu", password="pw")
        StudentProfile.objects.create(user=user, registration_no="REG-1", program=self.program)
        with self.assertRaises(IntegrityError), transaction.atomic():
            StudentProfile.objects.create(user=user, registration_no="REG-2", program=self.program)


class AdminProfileModelTests(TestCase):
    def test_user_can_have_only_one_admin_profile(self):
        user = User.objects.create_user(username="adm", password="pw", role=User.Role.ADMIN)
        AdminProfile.objects.create(user=user)
        with self.assertRaises(IntegrityError), transaction.atomic():
            AdminProfile.objects.create(user=user)
