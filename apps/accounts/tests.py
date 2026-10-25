from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.test import Client, TestCase
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

    def test_registration_page_includes_password_strength_meter(self):
        response = self.client.get(self.register_url)

        self.assertContains(response, "data-password-strength")
        self.assertContains(response, "Password strength")
        self.assertContains(response, "js/password-strength.js")
        self.assertNotContains(response, "Your password can")
        self.assertNotContains(response, "Enter the same password")
        self.assertNotContains(response, "Enter a password")

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
        self.assertContains(
            response,
            "Log in failed. Check your username and password.",
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

    def test_logout_requires_a_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)

        response = client.post(reverse("accounts:logout"))

        self.assertEqual(response.status_code, 403)
        self.assertIn("_auth_user_id", client.session)


class ProfileTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="suyesh",
            email="suyesh@example.com",
            password="Str0ng-Passw0rd!23",
            first_name="Suyesh",
            last_name="Poudel",
        )
        cls.profile_url = reverse("accounts:profile")

    def setUp(self):
        self.client.force_login(self.user)

    def test_profile_page_requires_login(self):
        self.client.logout()

        response = self.client.get(self.profile_url)

        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={self.profile_url}",
        )

    def test_profile_page_shows_user_details(self):
        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/profile.html")
        self.assertContains(response, "My profile")
        self.assertContains(response, self.user.username)
        self.assertContains(response, self.user.email)
        self.assertContains(response, self.user.get_full_name())
        self.assertContains(response, "Profile details")
        self.assertContains(response, "Change password")
        self.assertContains(response, reverse("accounts:logout"))
        self.assertNotContains(response, "Enter the same password")
        self.assertNotContains(response, 'class="card app-card h-100"')

    def test_profile_is_linked_from_navbar_and_sidebar(self):
        response = self.client.get(reverse("core:dashboard"))

        self.assertContains(response, 'id="navbar-user-menu"')
        self.assertContains(response, self.user.get_full_name())
        self.assertContains(response, f"@{self.user.get_username()}")
        self.assertContains(response, reverse("accounts:profile"))
        self.assertContains(response, reverse("accounts:logout"))
        self.assertContains(response, "app-sidebar-profile-link")
        self.assertContains(response, self.user.email)

        content = response.content.decode()
        self.assertLess(
            content.index(reverse("categories:list")),
            content.index("app-sidebar-profile-link"),
        )

    def test_user_can_update_profile(self):
        response = self.client.post(
            self.profile_url,
            {
                "form": "profile",
                "username": "new-suyesh",
                "email": "new@example.com",
                "first_name": "New",
                "last_name": "Name",
            },
            follow=True,
        )

        self.assertRedirects(response, self.profile_url)
        self.assertContains(
            response,
            "Profile updated: Username, Email address, First name, "
            "Last name.",
        )
        self.assertContains(
            response,
            'class="toast app-toast app-toast-success"',
        )
        self.assertContains(response, 'data-bs-autohide="true"')
        self.assertContains(response, 'data-bs-delay="5000"')
        self.assertContains(response, "app-toast-progress-bar")
        self.assertContains(response, "js/toasts.js")
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "new-suyesh")
        self.assertEqual(self.user.email, "new@example.com")
        self.assertEqual(self.user.first_name, "New")
        self.assertEqual(self.user.last_name, "Name")

    def test_profile_update_rejects_duplicate_username(self):
        User.objects.create_user(
            username="taken",
            password="Str0ng-Passw0rd!23",
        )

        response = self.client.post(
            self.profile_url,
            {
                "form": "profile",
                "username": "taken",
                "email": "suyesh@example.com",
                "first_name": "Suyesh",
                "last_name": "Poudel",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A user with that username already exists.")
        self.assertContains(
            response,
            "Profile was not updated. Please fix the highlighted fields.",
        )
        self.assertContains(
            response,
            'class="toast app-toast app-toast-danger"',
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "suyesh")

    def test_user_can_change_password(self):
        response = self.client.post(
            self.profile_url,
            {
                "form": "password",
                "old_password": "Str0ng-Passw0rd!23",
                "new_password1": "N3w-Str0ng-Pass!",
                "new_password2": "N3w-Str0ng-Pass!",
            },
        )

        self.assertRedirects(response, self.profile_url)
        self.assertIsNotNone(
            authenticate(
                username=self.user.username,
                password="N3w-Str0ng-Pass!",
            )
        )
        self.assertEqual(self.client.get(self.profile_url).status_code, 200)

    def test_password_change_rejects_wrong_current_password(self):
        response = self.client.post(
            self.profile_url,
            {
                "form": "password",
                "old_password": "wrong-password",
                "new_password1": "N3w-Str0ng-Pass!",
                "new_password2": "N3w-Str0ng-Pass!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Your old password was entered incorrectly",
        )
        self.assertIsNotNone(
            authenticate(
                username=self.user.username,
                password="Str0ng-Passw0rd!23",
            )
        )
