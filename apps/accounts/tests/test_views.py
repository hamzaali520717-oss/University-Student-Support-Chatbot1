from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.academics.models import Department, Program
from apps.accounts.models import AdminProfile, StudentProfile, User


class LoginTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="stu", password="a-strong-passw0rd")

    def test_login_success_returns_tokens(self):
        response = self.client.post(
            reverse("login"), {"username": "stu", "password": "a-strong-passw0rd"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_bad_credentials_rejected(self):
        response = self.client.post(reverse("login"), {"username": "stu", "password": "wrong"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token(self):
        login = self.client.post(
            reverse("login"), {"username": "stu", "password": "a-strong-passw0rd"}
        )
        response = self.client.post(reverse("login-refresh"), {"refresh": login.data["refresh"]})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)


class LoginThrottleTests(APITestCase):
    """Regression: the JWT login/refresh views had no rate limiting at all,
    leaving unlimited credential-stuffing/brute-force attempts against
    them (see SECURITY_NOTES.md)."""

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_login_is_rate_limited_per_ip(self):
        for _ in range(10):
            response = self.client.post(reverse("login"), {"username": "stu", "password": "wrong"})
            self.assertNotEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        response = self.client.post(reverse("login"), {"username": "stu", "password": "wrong"})
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_refresh_is_rate_limited_per_ip(self):
        for _ in range(10):
            response = self.client.post(reverse("login-refresh"), {"refresh": "not-a-real-token"})
            self.assertNotEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        response = self.client.post(reverse("login-refresh"), {"refresh": "not-a-real-token"})
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class MeTests(APITestCase):
    def setUp(self):
        self.department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=self.department, code="CS", name="Computer Science"
        )

    def test_me_unauthenticated_rejected(self):
        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_student_returns_profile(self):
        user = User.objects.create_user(username="stu", password="pw")
        StudentProfile.objects.create(user=user, registration_no="REG-1", program=self.program)
        self.client.force_authenticate(user=user)
        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["username"], "stu")
        self.assertEqual(response.data["profile"]["registration_no"], "REG-1")

    def test_me_admin_returns_profile(self):
        user = User.objects.create_user(username="adm", password="pw", role=User.Role.ADMIN)
        AdminProfile.objects.create(user=user)
        self.client.force_authenticate(user=user)
        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["role"], User.Role.ADMIN)


class AdminOnlyEndpointTests(APITestCase):
    def test_student_forbidden_from_admin_user_list(self):
        student = User.objects.create_user(username="stu", password="pw", role=User.Role.STUDENT)
        self.client.force_authenticate(user=student)
        response = self.client.get(reverse("admin-user-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_rejected_from_admin_user_list(self):
        response = self.client.get(reverse("admin-user-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_can_reach_admin_user_list(self):
        admin = User.objects.create_user(username="adm", password="pw", role=User.Role.ADMIN)
        self.client.force_authenticate(user=admin)
        response = self.client.get(reverse("admin-user-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class RegisterTests(APITestCase):
    def setUp(self):
        self.department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=self.department, code="CS", name="Computer Science"
        )

    def _payload(self, **overrides):
        payload = dict(
            username="newstudent",
            email="new@example.com",
            password="a-strong-passw0rd",
            first_name="New",
            last_name="Student",
            registration_no="REG-1",
            program="CS",
        )
        payload.update(overrides)
        return payload

    def test_register_success_returns_tokens(self):
        response = self.client.post(reverse("register"), self._payload())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["username"], "newstudent")
        self.assertTrue(StudentProfile.objects.filter(registration_no="REG-1").exists())

    def test_register_duplicate_username_rejected(self):
        User.objects.create_user(username="newstudent", password="pw")
        response = self.client.post(reverse("register"), self._payload())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_registration_no_rejected(self):
        existing = User.objects.create_user(username="other", password="pw")
        StudentProfile.objects.create(user=existing, registration_no="REG-1", program=self.program)
        response = self.client.post(reverse("register"), self._payload())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_unknown_program_rejected(self):
        response = self.client.post(reverse("register"), self._payload(program="UNKNOWN"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_weak_password_returns_400_not_500(self):
        # Regression: register_student() (apps.accounts.services) validates
        # the password with django.contrib.auth.password_validation and
        # raises Django's ValidationError, not DRF's - the exception handler
        # didn't recognize it and let it fall through as an unhandled 500.
        response = self.client.post(reverse("register"), self._payload(password="12345678"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username="newstudent").exists())


class RegisterThrottleTests(APITestCase):
    """Regression: the public, unauthenticated RegisterView had no rate
    limiting, leaving unlimited account-creation spam (see
    SECURITY_NOTES.md)."""

    def setUp(self):
        self.department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=self.department, code="CS", name="Computer Science"
        )
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_register_is_rate_limited_per_ip(self):
        payload = {
            "username": "dup",
            "email": "dup@example.com",
            "password": "a-strong-passw0rd",
            "first_name": "Dup",
            "last_name": "Licate",
            "registration_no": "REG-DUP",
            "program": "CS",
        }
        for _ in range(5):
            response = self.client.post(reverse("register"), payload)
            self.assertNotEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        response = self.client.post(reverse("register"), payload)
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
