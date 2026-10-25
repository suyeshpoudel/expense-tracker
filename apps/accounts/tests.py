from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class RegistrationTests(TestCase):
    def setUp(self):
        self.register_url = reverse("accounts:register")
        self.valid_data = {
            "username": "suyesh",
            "email": "suyesh@example.com",
            "password1": "Str0ng-Passw0rd!23",
            "password2": "Str0ng-Passw0rd!23",
        }

    def test_registration_page_renders(self):
        response = self.client.get(self.register_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/register.html")

    def test_valid_registration_creates_user_and_logs_them_in(self):
        response = self.client.post(self.register_url, self.valid_data)

        self.assertRedirects(response, reverse("core:dashboard"))
        user = User.objects.get(username="suyesh")
        self.assertEqual(user.email, "suyesh@example.com")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_duplicate_username_is_rejected(self):
        User.objects.create_user(username="suyesh", password="Str0ng-Passw0rd!23")

        response = self.client.post(self.register_url, self.valid_data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username="suyesh").count(), 1)
        self.assertContains(response, "A user with that username already exists.")

    def test_mismatched_passwords_are_rejected(self):
        data = {**self.valid_data, "password2": "Another-Passw0rd!23"}

        response = self.client.post(self.register_url, data)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="suyesh").exists())
        self.assertContains(response, "The two password fields didn’t match.")

    def test_authenticated_user_is_redirected_to_dashboard(self):
        user = User.objects.create_user(
            username="suyesh", password="Str0ng-Passw0rd!23"
        )
        self.client.force_login(user)

        response = self.client.get(self.register_url)

        self.assertRedirects(response, reverse("core:dashboard"))


class AuthenticationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="suyesh", password="Str0ng-Passw0rd!23"
        )

    def setUp(self):
        self.login_url = reverse("accounts:login")

    def test_login_page_renders(self):
        response = self.client.get(self.login_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/login.html")

    def test_valid_login_redirects_to_dashboard(self):
        response = self.client.post(
            self.login_url,
            {"username": "suyesh", "password": "Str0ng-Passw0rd!23"},
        )

        self.assertRedirects(response, reverse("core:dashboard"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_invalid_login_shows_error(self):
        response = self.client.post(
            self.login_url,
            {"username": "suyesh", "password": "wrong-password"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(
            response,
            "Please enter a correct username and password.",
        )

    def test_login_respects_local_next_url(self):
        dashboard_url = reverse("core:dashboard")

        response = self.client.post(
            f"{self.login_url}?next={dashboard_url}",
            {"username": "suyesh", "password": "Str0ng-Passw0rd!23"},
        )

        self.assertRedirects(response, dashboard_url)

    def test_login_ignores_external_next_url(self):
        response = self.client.post(
            f"{self.login_url}?next=https://example.com/",
            {"username": "suyesh", "password": "Str0ng-Passw0rd!23"},
        )

        self.assertRedirects(response, reverse("core:dashboard"))

    def test_authenticated_user_is_redirected_from_login(self):
        self.client.force_login(self.user)

        response = self.client.get(self.login_url)

        self.assertRedirects(response, reverse("core:dashboard"))

    def test_logout_requires_post(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("accounts:logout"))

        self.assertEqual(response.status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)

    def test_logout_clears_session(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("accounts:logout"))

        self.assertRedirects(response, reverse("core:home"))
        self.assertNotIn("_auth_user_id", self.client.session)
