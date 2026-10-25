from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.categories.models import Category
from apps.transactions.models import Transaction

from .services import month_bounds, shift_month


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
        self.assertContains(response, reverse("core:reports"))
        self.assertContains(response, reverse("budgets:list"))
        self.assertContains(response, reverse("accounts:logout"))
        self.assertContains(response, "Log out")


class ReportViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="suyesh", password="Str0ng-Passw0rd!23"
        )
        cls.other_user = User.objects.create_user(
            username="other", password="Str0ng-Passw0rd!23"
        )
        cls.food = Category.objects.create(
            user=cls.user,
            category_type=Category.Type.EXPENSE,
            name="Food and groceries",
        )
        cls.transport = Category.objects.create(
            user=cls.user,
            category_type=Category.Type.EXPENSE,
            name="Transport",
        )
        cls.salary = Category.objects.create(
            user=cls.user,
            category_type=Category.Type.INCOME,
            name="Salary",
        )
        cls.other_food = Category.objects.create(
            user=cls.other_user,
            category_type=Category.Type.EXPENSE,
            name="Food and groceries",
        )
        cls.other_salary = Category.objects.create(
            user=cls.other_user,
            category_type=Category.Type.INCOME,
            name="Salary",
        )

    def setUp(self):
        self.client.force_login(self.user)

    def create_transaction(self, **overrides):
        user = overrides.get("user", self.user)
        transaction_type = overrides.get(
            "transaction_type",
            Transaction.Type.EXPENSE,
        )
        if "category" not in overrides:
            if user == self.user:
                category = (
                    self.food
                    if transaction_type == Transaction.Type.EXPENSE
                    else self.salary
                )
            else:
                category = (
                    self.other_food
                    if transaction_type == Transaction.Type.EXPENSE
                    else self.other_salary
                )
            overrides["category"] = category

        values = {
            "user": self.user,
            "transaction_type": Transaction.Type.EXPENSE,
            "amount": Decimal("10.00"),
            "title": "Test transaction",
            "date": timezone.localdate(),
        }
        values.update(overrides)
        return Transaction.objects.create(**values)


class DashboardTests(ReportViewTestCase):
    def test_anonymous_user_is_redirected_to_login(self):
        self.client.logout()
        dashboard_url = reverse("core:dashboard")

        response = self.client.get(dashboard_url)

        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={dashboard_url}",
        )

    def test_dashboard_renders_real_zero_totals(self):
        response = self.client.get(reverse("core:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/dashboard.html")
        self.assertContains(response, "NPR 0.00")
        self.assertContains(response, "No budget configured yet.")
        self.assertContains(response, "No transactions recorded yet")
        self.assertContains(response, "No expenses recorded")
        self.assertContains(response, "No spending in this period")
        self.assertNotContains(response, "Monthly totals are not available yet.")
        self.assertNotContains(response, "chart.umd.min.js")
        self.assertNotContains(response, "charts.js")

    def test_dashboard_shows_current_month_totals(self):
        period_from, _ = month_bounds(timezone.localdate())
        self.create_transaction(
            amount=Decimal("125.50"),
            date=timezone.localdate(),
        )
        self.create_transaction(
            amount=Decimal("30.00"),
            date=period_from,
        )
        self.create_transaction(
            transaction_type=Transaction.Type.INCOME,
            amount=Decimal("500.00"),
            date=timezone.localdate(),
        )
        self.create_transaction(
            user=self.other_user,
            amount=Decimal("1000.00"),
            date=timezone.localdate(),
        )

        response = self.client.get(reverse("core:dashboard"))

        self.assertEqual(
            response.context["total_expenses"],
            Decimal("155.50"),
        )
        self.assertEqual(
            response.context["total_income"],
            Decimal("500.00"),
        )
        self.assertEqual(response.context["net_total"], Decimal("344.50"))
        self.assertContains(response, "NPR 155.50")
        self.assertContains(response, "NPR 500.00")
        self.assertContains(response, "NPR 344.50")
        self.assertNotContains(response, "NPR 1000.00")

    def test_dashboard_excludes_other_months_from_totals(self):
        period_from, _ = month_bounds(timezone.localdate())
        self.create_transaction(
            amount=Decimal("999.00"),
            date=shift_month(period_from, -1),
        )
        self.create_transaction(
            amount=Decimal("888.00"),
            date=shift_month(period_from, 1),
        )
        self.create_transaction(
            user=self.other_user,
            amount=Decimal("777.00"),
            date=timezone.localdate(),
        )

        response = self.client.get(reverse("core:dashboard"))

        self.assertEqual(
            response.context["total_expenses"],
            Decimal("0.00"),
        )
        self.assertEqual(response.context["expense_breakdown"], [])
        self.assertEqual(response.context["net_total"], Decimal("0.00"))

    def test_dashboard_groups_expenses_by_category(self):
        self.create_transaction(
            category=self.food,
            amount=Decimal("75.00"),
        )
        self.create_transaction(
            category=self.transport,
            amount=Decimal("25.00"),
        )
        self.create_transaction(
            transaction_type=Transaction.Type.INCOME,
            category=self.salary,
            amount=Decimal("1000.00"),
        )

        response = self.client.get(reverse("core:dashboard"))

        breakdown = response.context["expense_breakdown"]
        self.assertEqual(
            [item["name"] for item in breakdown],
            ["Food and groceries", "Transport"],
        )
        self.assertEqual(
            [item["total"] for item in breakdown],
            [Decimal("75.00"), Decimal("25.00")],
        )
        self.assertEqual(
            [item["percentage"] for item in breakdown],
            [Decimal("75.0"), Decimal("25.0")],
        )
        self.assertEqual(
            response.context["category_chart_data"]["values"],
            [75.0, 25.0],
        )
        self.assertContains(response, "category-spending-chart")
        self.assertContains(response, "category-spending-data")
        self.assertContains(response, "vendor/chartjs/chart.umd.min.js")
        self.assertContains(response, "js/charts.js")

    def test_dashboard_includes_previous_months_in_six_month_trend(self):
        period_from, _ = month_bounds(timezone.localdate())
        previous_month = shift_month(period_from, -1)
        self.create_transaction(
            amount=Decimal("40.00"),
            date=previous_month,
        )

        response = self.client.get(reverse("core:dashboard"))

        trend = response.context["trend"]
        self.assertEqual(len(trend), 6)
        self.assertEqual(trend[-2]["total"], Decimal("40.00"))
        self.assertEqual(trend[-1]["total"], Decimal("0.00"))
        self.assertTrue(response.context["trend_has_data"])
        self.assertContains(response, "monthly-trend-chart")
        self.assertContains(response, "monthly-trend-data")

    def test_dashboard_query_count_does_not_grow_with_transactions(self):
        self.create_transaction(amount=Decimal("10.00"))
        dashboard_url = reverse("core:dashboard")

        with CaptureQueriesContext(connection) as baseline:
            self.client.get(dashboard_url)

        for index in range(8):
            self.create_transaction(
                amount=Decimal("10.00") + index,
                title=f"Transaction {index}",
            )

        with CaptureQueriesContext(connection) as after_more_transactions:
            self.client.get(dashboard_url)

        self.assertEqual(len(baseline), len(after_more_transactions))

    def test_dashboard_shows_only_the_users_recent_transactions(self):
        self.create_transaction(title="My recent expense")
        self.create_transaction(
            user=self.other_user,
            transaction_type=Transaction.Type.INCOME,
            title="Other user income",
        )

        response = self.client.get(reverse("core:dashboard"))

        self.assertContains(response, "My recent expense")
        self.assertNotContains(response, "Other user income")


class ReportsTests(ReportViewTestCase):
    def test_anonymous_user_is_redirected_to_login(self):
        self.client.logout()
        reports_url = reverse("core:reports")

        response = self.client.get(reports_url)

        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reports_url}",
        )

    def test_default_report_uses_current_month(self):
        period_from, period_to = month_bounds(timezone.localdate())

        response = self.client.get(reverse("core:reports"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/reports.html")
        self.assertTrue(response.context["show_report"])
        self.assertEqual(response.context["date_from"], period_from)
        self.assertEqual(response.context["date_to"], period_to)
        self.assertEqual(
            response.context["form"]["date_from"].value(),
            period_from,
        )
        self.assertEqual(
            response.context["form"]["date_to"].value(),
            period_to,
        )
        self.assertContains(response, "NPR 0.00")
        self.assertContains(response, "No expenses recorded")
        self.assertContains(response, "No spending in this period")

    def test_custom_range_filters_and_calculates_report(self):
        self.create_transaction(
            category=self.food,
            amount=Decimal("100.00"),
            date=date(2026, 1, 10),
        )
        self.create_transaction(
            category=self.transport,
            amount=Decimal("50.00"),
            date=date(2026, 1, 31),
        )
        self.create_transaction(
            transaction_type=Transaction.Type.INCOME,
            category=self.salary,
            amount=Decimal("300.00"),
            date=date(2026, 1, 20),
        )
        self.create_transaction(
            amount=Decimal("500.00"),
            date=date(2025, 12, 31),
        )
        self.create_transaction(
            user=self.other_user,
            amount=Decimal("700.00"),
            date=date(2026, 1, 15),
        )

        response = self.client.get(
            reverse("core:reports"),
            {
                "date_from": "2026-01-01",
                "date_to": "2026-01-31",
            },
        )

        self.assertEqual(response.context["date_from"], date(2026, 1, 1))
        self.assertEqual(response.context["date_to"], date(2026, 1, 31))
        self.assertEqual(
            response.context["total_expenses"],
            Decimal("150.00"),
        )
        self.assertEqual(
            response.context["total_income"],
            Decimal("300.00"),
        )
        self.assertEqual(response.context["net_total"], Decimal("150.00"))
        self.assertEqual(
            [item["total"] for item in response.context["expense_breakdown"]],
            [Decimal("100.00"), Decimal("50.00")],
        )
        self.assertEqual(
            response.context["trend"][0]["total"],
            Decimal("150.00"),
        )
        self.assertContains(response, "NPR 150.00")
        self.assertContains(response, "NPR 300.00")
        self.assertContains(response, "category-spending-chart")
        self.assertContains(response, "monthly-trend-chart")
        self.assertContains(response, "vendor/chartjs/chart.umd.min.js")
        self.assertContains(response, "js/charts.js")

    def test_report_accepts_a_single_day_range(self):
        self.create_transaction(
            amount=Decimal("30.00"),
            date=date(2026, 1, 15),
        )
        self.create_transaction(
            amount=Decimal("20.00"),
            date=date(2026, 1, 14),
        )

        response = self.client.get(
            reverse("core:reports"),
            {
                "date_from": "2026-01-15",
                "date_to": "2026-01-15",
            },
        )

        self.assertTrue(response.context["show_report"])
        self.assertEqual(
            response.context["total_expenses"],
            Decimal("30.00"),
        )

    def test_report_trend_fills_empty_months(self):
        self.create_transaction(
            amount=Decimal("10.00"),
            date=date(2026, 1, 5),
        )
        self.create_transaction(
            amount=Decimal("30.00"),
            date=date(2026, 3, 5),
        )

        response = self.client.get(
            reverse("core:reports"),
            {
                "date_from": "2026-01-01",
                "date_to": "2026-03-31",
            },
        )

        self.assertEqual(
            [item["label"] for item in response.context["trend"]],
            ["Jan 2026", "Feb 2026", "Mar 2026"],
        )
        self.assertEqual(
            [item["total"] for item in response.context["trend"]],
            [Decimal("10.00"), Decimal("0.00"), Decimal("30.00")],
        )

    def test_report_rejects_reversed_date_range(self):
        response = self.client.get(
            reverse("core:reports"),
            {
                "date_from": "2026-02-01",
                "date_to": "2026-01-01",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["show_report"])
        self.assertIn("date_to", response.context["form"].errors)
        self.assertContains(
            response,
            "End date must be on or after the start date.",
        )
        self.assertNotContains(response, "Spending by category")

    def test_report_rejects_invalid_dates(self):
        response = self.client.get(
            reverse("core:reports"),
            {
                "date_from": "not-a-date",
                "date_to": "2026-01-31",
            },
        )

        self.assertFalse(response.context["show_report"])
        self.assertIn("date_from", response.context["form"].errors)

    def test_report_requires_both_dates(self):
        response = self.client.get(
            reverse("core:reports"),
            {
                "date_from": "",
                "date_to": "",
            },
        )

        self.assertFalse(response.context["show_report"])
        self.assertIn("date_from", response.context["form"].errors)
        self.assertIn("date_to", response.context["form"].errors)

    def test_report_without_expenses_skips_charts(self):
        response = self.client.get(
            reverse("core:reports"),
            {
                "date_from": "2026-04-01",
                "date_to": "2026-04-30",
            },
        )

        self.assertTrue(response.context["show_report"])
        self.assertFalse(response.context["has_expenses"])
        self.assertNotContains(response, "chart.umd.min.js")
        self.assertNotContains(response, "charts.js")
        self.assertNotContains(response, "category-spending-chart")
        self.assertNotContains(response, "monthly-trend-chart")
