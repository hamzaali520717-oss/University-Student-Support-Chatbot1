from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from apps.academics.models import Department, Program
from apps.accounts import services
from apps.accounts.models import AdminProfile, User
from apps.core.signals import ADMIN_STAFF_GROUP_NAME, sync_admin_staff_group


class UserAdminRoleTests(TestCase):
    def setUp(self):
        sync_admin_staff_group()
        self.department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=self.department, code="CS", name="Computer Science"
        )
        # A bootstrap superuser only to act as the already-privileged operator
        # submitting the User admin forms below - not the behavior under test.
        self.bootstrap = User.objects.create_superuser(
            username="bootstrap", password="pw", role=User.Role.ADMIN
        )
        self.client.force_login(self.bootstrap)

    def _empty_student_profile_formset(self, **overrides):
        data = {
            "student_profile-TOTAL_FORMS": "1",
            "student_profile-INITIAL_FORMS": "0",
            "student_profile-MIN_NUM_FORMS": "0",
            "student_profile-MAX_NUM_FORMS": "1",
            "student_profile-0-registration_no": "",
            "student_profile-0-program": "",
            "student_profile-0-id": "",
        }
        data.update(overrides)
        return data

    def test_creating_admin_role_user_grants_staff_and_group_not_superuser(self):
        response = self.client.post(
            reverse("admin:accounts_user_add"),
            {
                "username": "new_admin",
                "password1": "Sup3rSecretPW!1",
                "password2": "Sup3rSecretPW!1",
                "role": "admin",
                "_save": "Save",
                **self._empty_student_profile_formset(),
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        user = User.objects.get(username="new_admin")
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.groups.filter(name=ADMIN_STAFF_GROUP_NAME).exists())
        self.assertTrue(AdminProfile.objects.filter(user=user).exists())

    def test_demoting_admin_to_student_revokes_staff_and_group(self):
        user = User.objects.create_user(
            username="existing_admin", password="pw", role=User.Role.ADMIN, is_staff=True
        )
        user.groups.add(Group.objects.get(name=ADMIN_STAFF_GROUP_NAME))
        AdminProfile.objects.create(user=user)

        response = self.client.post(
            reverse("admin:accounts_user_change", args=[user.pk]),
            {
                "username": "existing_admin",
                "first_name": "",
                "last_name": "",
                "email": "",
                "is_active": "on",
                "date_joined_0": user.date_joined.strftime("%Y-%m-%d"),
                "date_joined_1": user.date_joined.strftime("%H:%M:%S"),
                "role": "student",
                "_save": "Save",
                **self._empty_student_profile_formset(
                    **{
                        "student_profile-0-registration_no": "REG-DEMOTED",
                        "student_profile-0-program": str(self.program.pk),
                    }
                ),
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        user.refresh_from_db()
        self.assertFalse(user.is_staff)
        self.assertFalse(user.groups.filter(name=ADMIN_STAFF_GROUP_NAME).exists())

    def test_demoting_superuser_to_student_still_revokes_staff(self):
        # Regression: previously `save_model` only cleared is_staff when
        # `not obj.is_superuser`, so a legacy/bootstrap superuser demoted to
        # student kept is_staff=True and therefore full admin API access via
        # IsAdminStaff's old `or user.is_staff` clause.
        user = User.objects.create_user(
            username="legacy_superuser",
            password="pw",
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        user.groups.add(Group.objects.get(name=ADMIN_STAFF_GROUP_NAME))
        AdminProfile.objects.create(user=user)

        response = self.client.post(
            reverse("admin:accounts_user_change", args=[user.pk]),
            {
                "username": "legacy_superuser",
                "first_name": "",
                "last_name": "",
                "email": "",
                "is_active": "on",
                "is_superuser": "on",
                "date_joined_0": user.date_joined.strftime("%Y-%m-%d"),
                "date_joined_1": user.date_joined.strftime("%H:%M:%S"),
                "role": "student",
                "_save": "Save",
                **self._empty_student_profile_formset(
                    **{
                        "student_profile-0-registration_no": "REG-LEGACY",
                        "student_profile-0-program": str(self.program.pk),
                    }
                ),
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        user.refresh_from_db()
        self.assertTrue(user.is_superuser)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.groups.filter(name=ADMIN_STAFF_GROUP_NAME).exists())

    def test_non_superuser_cannot_grant_superuser_via_change_form(self):
        # Regression: UserAdmin.fieldsets used to inherit Django's stock
        # Permissions fieldset unmodified, so any non-superuser "Admin Staff"
        # group member (who has accounts.change_user) could tick "Superuser
        # status" on the ordinary change form and grant themselves full
        # Django superuser.
        non_super_admin = User.objects.create_user(
            username="group_admin_only", password="pw", role=User.Role.ADMIN, is_staff=True
        )
        non_super_admin.groups.add(Group.objects.get(name=ADMIN_STAFF_GROUP_NAME))
        self.client.force_login(non_super_admin)

        response = self.client.post(
            reverse("admin:accounts_user_change", args=[non_super_admin.pk]),
            {
                "username": "group_admin_only",
                "first_name": "",
                "last_name": "",
                "email": "",
                "is_active": "on",
                "is_staff": "on",
                "is_superuser": "on",
                "date_joined_0": non_super_admin.date_joined.strftime("%Y-%m-%d"),
                "date_joined_1": non_super_admin.date_joined.strftime("%H:%M:%S"),
                "role": "admin",
                "_save": "Save",
                **self._empty_student_profile_formset(),
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        non_super_admin.refresh_from_db()
        self.assertFalse(non_super_admin.is_superuser)

    def test_sync_admin_access_is_atomic(self):
        # Regression: the group/is_staff/AdminProfile writes used to happen
        # as loose statements in save_model with no transaction wrapper, so a
        # failure partway through could leave is_staff flipped with no
        # matching group membership. Exercise the service directly (not
        # through the admin view) to simulate that failure.
        from unittest.mock import patch

        user = User.objects.create_user(username="atomic_test", password="pw", role=User.Role.STUDENT)
        user.role = User.Role.ADMIN

        with patch(
            "apps.accounts.services.AdminProfile.objects.get_or_create",
            side_effect=RuntimeError("boom"),
        ):
            with self.assertRaises(RuntimeError):
                services.sync_admin_access(user=user)

        user.refresh_from_db()
        self.assertFalse(user.is_staff)
        self.assertFalse(user.groups.filter(name=ADMIN_STAFF_GROUP_NAME).exists())


class SuperuserProtectionTests(TestCase):
    """Regression: apps.accounts.services.sync_admin_access and UserAdmin's
    get_readonly_fields stop an Admin Staff member from granting themselves
    is_superuser through the form, but that left a second door open - the
    "Admin Staff" group holds accounts.change_user (see
    apps.core.signals.ADMIN_MANAGED_APPS), and Django's stock
    user_change_password/change/delete views only ever checked that
    model-level permission, not whether the *target* was a superuser. A
    non-superuser Admin Staff member could open an existing superuser's
    change-password form directly and reset it - hijacking that account
    instead of needing to grant itself the flag at all."""

    def setUp(self):
        sync_admin_staff_group()
        self.staff_user = User.objects.create_user(
            username="group_admin", password="pw", role=User.Role.ADMIN, is_staff=True
        )
        self.staff_user.groups.add(Group.objects.get(name=ADMIN_STAFF_GROUP_NAME))
        assert not self.staff_user.is_superuser
        self.client.force_login(self.staff_user)

        self.target_superuser = User.objects.create_superuser(
            username="victim_superuser", password="OriginalPW123!"
        )

    def test_cannot_view_or_change_superuser(self):
        response = self.client.get(
            reverse("admin:accounts_user_change", args=[self.target_superuser.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_cannot_get_superuser_password_form(self):
        response = self.client.get(
            reverse("admin:auth_user_password_change", args=[self.target_superuser.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_cannot_post_superuser_password_change(self):
        response = self.client.post(
            reverse("admin:auth_user_password_change", args=[self.target_superuser.pk]),
            {"password1": "HijackedPW456!", "password2": "HijackedPW456!"},
        )
        self.assertEqual(response.status_code, 403)

        self.target_superuser.refresh_from_db()
        self.assertFalse(self.target_superuser.check_password("HijackedPW456!"))
        self.assertTrue(self.target_superuser.check_password("OriginalPW123!"))
        self.assertTrue(self.target_superuser.is_superuser)

    def test_cannot_delete_superuser(self):
        response = self.client.post(
            reverse("admin:accounts_user_delete", args=[self.target_superuser.pk])
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(User.objects.filter(pk=self.target_superuser.pk).exists())

    def test_superuser_hidden_from_changelist(self):
        response = self.client.get(reverse("admin:accounts_user_changelist"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "victim_superuser")

    def test_superuser_can_still_manage_superuser_accounts(self):
        # The guard is scoped to non-superuser requesters - a real superuser
        # must retain full access to other superuser accounts.
        superuser_operator = User.objects.create_superuser(username="root_operator", password="pw")
        self.client.force_login(superuser_operator)

        response = self.client.get(
            reverse("admin:accounts_user_change", args=[self.target_superuser.pk])
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse("admin:accounts_user_changelist"))
        self.assertContains(response, "victim_superuser")
