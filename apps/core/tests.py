from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.transactions.models import Transaction


class HomePageTests(TestCase):
    def test_home_page_renders(self):
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/home.html")
        self.assertTemplateUsed(response, "base.html")

    def test_home_page_loads_application_stylesheet(self):
        response = self.client.get(reverse("core:home"))

        self.assertContains(response, "css/app.css")
        self.assertContains(response, "vendor/bootstrap/bootstrap.min.css")

    def test_anonymous_home_page_shows_auth_links(self):
        response = self.client.get(reverse("core:home"))

        self.assertContains(response, reverse("accounts:login"))
        self.assertContains(response, reverse("accounts:register"))
        self.assertNotContains(response, reverse("core:dashboard"))

    def test_authenticated_home_page_shows_navigation(self):
        user = User.objects.create_user(
            username="suyesh", password="Str0ng-Passw0rd!23"
        )
        self.client.force_login(user)

        response = self.client.get(reverse("core:home"))

        self.assertContains(response, reverse("core:dashboard"))
        self.assertContains(response, reverse("accounts:logout"))
        self.assertContains(response, "Log out")


class DashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="suyesh", password="Str0ng-Passw0rd!23"
        )

    def test_anonymous_user_is_redirected_to_login(self):
        dashboard_url = reverse("core:dashboard")

        response = self.client.get(dashboard_url)

        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={dashboard_url}",
        )

    def test_dashboard_renders_for_authenticated_user(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("core:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/dashboard.html")
        self.assertContains(response, "Monthly totals are not available yet.")
        self.assertContains(response, "No budget configured yet.")
        self.assertContains(response, "No transactions recorded yet")

    def test_dashboard_does_not_show_fabricated_totals(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("core:dashboard"))

        self.assertNotContains(response, "NPR")
        self.assertNotContains(response, "0.00")

    def test_dashboard_shows_only_the_users_recent_transactions(self):
        other_user = User.objects.create_user(
            username="other", password="Str0ng-Passw0rd!23"
        )
        Transaction.objects.create(
            user=self.user,
            transaction_type=Transaction.Type.EXPENSE,
            amount=Decimal("50.00"),
            title="My recent expense",
            date=timezone.localdate(),
        )
        Transaction.objects.create(
            user=other_user,
            transaction_type=Transaction.Type.INCOME,
            amount=Decimal("900.00"),
            title="Other user income",
            date=timezone.localdate(),
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("core:dashboard"))

        self.assertContains(response, "My recent expense")
        self.assertContains(response, "NPR")
        self.assertNotContains(response, "Other user income")
