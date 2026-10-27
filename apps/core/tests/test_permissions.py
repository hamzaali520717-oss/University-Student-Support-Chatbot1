from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import SimpleTestCase
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from apps.core.permissions import (
    IsAdminOrReadOnly,
    IsAdminStaff,
    IsAuthenticatedReadOnly,
    IsStudent,
)

User = get_user_model()
factory = APIRequestFactory()


def _request(method="GET", user=None):
    django_request = getattr(factory, method.lower())("/")
    request = Request(django_request)
    request.user = user if user is not None else AnonymousUser()
    return request


class IsStudentTests(SimpleTestCase):
    def test_allows_student(self):
        user = User(username="stu", role=User.Role.STUDENT)
        self.assertTrue(IsStudent().has_permission(_request(user=user), None))

    def test_rejects_admin(self):
        user = User(username="adm", role=User.Role.ADMIN)
        self.assertFalse(IsStudent().has_permission(_request(user=user), None))

    def test_rejects_anonymous(self):
        self.assertFalse(IsStudent().has_permission(_request(), None))


class IsAdminStaffTests(SimpleTestCase):
    def test_allows_admin_role(self):
        user = User(username="adm", role=User.Role.ADMIN)
        self.assertTrue(IsAdminStaff().has_permission(_request(user=user), None))

    def test_allows_superuser(self):
        user = User(username="root", role=User.Role.STUDENT, is_superuser=True)
        self.assertTrue(IsAdminStaff().has_permission(_request(user=user), None))

    def test_rejects_staff_without_admin_role_or_superuser(self):
        # Regression: this used to be `test_allows_django_staff` - is_staff
        # alone used to be sufficient, which meant a demoted admin (role
        # flipped to student, but is_staff not yet cleared by whatever wrote
        # the change) still passed. is_staff is a Django admin-site-access
        # flag, not this app's admin/permission concept - role and
        # is_superuser are the only things that should grant access here.
        user = User(username="stf", role=User.Role.STUDENT, is_staff=True)
        self.assertFalse(IsAdminStaff().has_permission(_request(user=user), None))

    def test_rejects_plain_student(self):
        user = User(username="stu", role=User.Role.STUDENT)
        self.assertFalse(IsAdminStaff().has_permission(_request(user=user), None))

    def test_rejects_anonymous(self):
        self.assertFalse(IsAdminStaff().has_permission(_request(), None))


class IsAdminOrReadOnlyTests(SimpleTestCase):
    def test_allows_safe_method_for_anyone(self):
        self.assertTrue(IsAdminOrReadOnly().has_permission(_request("GET"), None))

    def test_allows_write_for_admin_role(self):
        user = User(username="adm", role=User.Role.ADMIN)
        self.assertTrue(IsAdminOrReadOnly().has_permission(_request("POST", user), None))

    def test_allows_write_for_superuser(self):
        user = User(username="root", role=User.Role.STUDENT, is_superuser=True)
        self.assertTrue(IsAdminOrReadOnly().has_permission(_request("POST", user), None))

    def test_rejects_write_for_demoted_staff_account(self):
        # Regression: this used to fall back to `or user.is_staff`, so a
        # demoted admin (role flipped to student, is_staff not yet cleared)
        # could still write here even though they're no longer role=admin.
        user = User(username="stf", role=User.Role.STUDENT, is_staff=True)
        self.assertFalse(IsAdminOrReadOnly().has_permission(_request("POST", user), None))

    def test_rejects_write_for_plain_student(self):
        user = User(username="stu", role=User.Role.STUDENT)
        self.assertFalse(IsAdminOrReadOnly().has_permission(_request("POST", user), None))

    def test_rejects_write_for_anonymous(self):
        self.assertFalse(IsAdminOrReadOnly().has_permission(_request("POST"), None))


class IsAuthenticatedReadOnlyTests(SimpleTestCase):
    def test_allows_authenticated_get(self):
        user = User(username="stu", role=User.Role.STUDENT)
        self.assertTrue(IsAuthenticatedReadOnly().has_permission(_request("GET", user), None))

    def test_rejects_authenticated_post(self):
        user = User(username="stu", role=User.Role.STUDENT)
        self.assertFalse(IsAuthenticatedReadOnly().has_permission(_request("POST", user), None))

    def test_rejects_anonymous_get(self):
        self.assertFalse(IsAuthenticatedReadOnly().has_permission(_request("GET"), None))
