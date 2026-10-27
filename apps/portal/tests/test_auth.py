from django.core.cache import cache
from django.urls import reverse

from apps.portal.tests.base import PortalTestCase


class LoginViewTests(PortalTestCase):
    def test_login_page_renders(self):
        response = self.client.get(reverse("portal:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Log in")

    def test_valid_student_login_redirects_and_establishes_session(self):
        response = self.client.post(
            reverse("portal:login"), {"username": "student1", "password": "pw"}
        )
        self.assertRedirects(response, reverse("portal:dashboard"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_admin_login_rejected_no_session_created(self):
        response = self.client.post(
            reverse("portal:login"), {"username": "admin1", "password": "pw"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This portal is for students only")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_wrong_password_shows_generic_error_no_session(self):
        response = self.client.post(
            reverse("portal:login"), {"username": "student1", "password": "wrong"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_already_authenticated_get_redirects_to_dashboard(self):
        self.login_student()
        response = self.client.get(reverse("portal:login"))
        self.assertRedirects(response, reverse("portal:dashboard"))

    def test_next_param_is_honored_end_to_end(self):
        protected_url = reverse("portal:fees")
        response = self.client.get(protected_url)
        self.assertRedirects(response, f"{reverse('portal:login')}?next={protected_url}")

        response = self.client.post(
            reverse("portal:login"),
            {"username": "student1", "password": "pw", "next": protected_url},
        )
        self.assertRedirects(response, protected_url)


class LoginThrottleTests(PortalTestCase):
    """Regression: the session login view had no rate limiting at all,
    leaving unlimited credential-stuffing/brute-force attempts against it
    (see SECURITY_NOTES.md). Shares the "login" throttle scope with the
    JWT login/refresh views (apps.accounts.views)."""

    def setUp(self):
        super().setUp()
        cache.clear()

    def tearDown(self):
        cache.clear()
        super().tearDown()

    def test_login_is_rate_limited_per_ip(self):
        for _ in range(10):
            response = self.client.post(
                reverse("portal:login"), {"username": "student1", "password": "wrong"}
            )
            self.assertNotEqual(response.status_code, 429)

        response = self.client.post(
            reverse("portal:login"), {"username": "student1", "password": "wrong"}
        )
        self.assertEqual(response.status_code, 429)
        self.assertContains(response, "Too many login attempts", status_code=429)
        self.assertNotIn("_auth_user_id", self.client.session)


class LogoutViewTests(PortalTestCase):
    def test_logout_requires_post(self):
        self.login_student()
        response = self.client.get(reverse("portal:logout"))
        self.assertEqual(response.status_code, 405)

    def test_logout_clears_session_and_redirects_to_login(self):
        self.login_student()
        response = self.client.post(reverse("portal:logout"))
        self.assertRedirects(response, reverse("portal:login"))
        self.assertNotIn("_auth_user_id", self.client.session)
