from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection
from django.db import transaction as db_transaction
from django.test import SimpleTestCase, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.categories.models import Category
from apps.core.services import shift_month
from apps.transactions.models import Transaction

from .forms import MonthlyBudgetForm
from .models import MonthlyBudget
from .services import budget_summaries, summarize_budget


class MonthlyBudgetModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="suyesh", password="Str0ng-Passw0rd!23"
        )
        cls.other_user = User.objects.create_user(
            username="other", password="Str0ng-Passw0rd!23"
        )

    def build_budget(self, **overrides):
        values = {
            "user": self.user,
            "month": date(2026, 1, 1),
            "amount": Decimal("1000.00"),
        }
        values.update(overrides)
        return MonthlyBudget(**values)

    def test_valid_budget(self):
        self.build_budget().full_clean()

    def test_amount_must_be_positive(self):
        for amount in (Decimal("0.00"), Decimal("-1.00")):
            with self.subTest(amount=amount):
                budget = self.build_budget(amount=amount)
                with self.assertRaises(ValidationError) as context:
                    budget.full_clean()
                self.assertIn("amount", context.exception.message_dict)

    def test_database_rejects_non_positive_amount(self):
        with self.assertRaises(IntegrityError):
            with db_transaction.atomic():
                MonthlyBudget.objects.bulk_create(
                    [self.build_budget(amount=Decimal("0.00"))]
                )

    def test_month_must_be_the_first_day(self):
        budget = self.build_budget(month=date(2026, 1, 15))

        with self.assertRaises(ValidationError) as context:
            budget.full_clean()

        self.assertIn("month", context.exception.message_dict)

    def test_each_user_can_have_only_one_budget_per_month(self):
        self.build_budget().save()

        with self.assertRaises(IntegrityError):
            with db_transaction.atomic():
                self.build_budget(amount=Decimal("500.00")).save()

    def test_different_users_can_budget_the_same_month(self):
        self.build_budget().save()
        self.build_budget(
            user=self.other_user,
            amount=Decimal("750.00"),
        ).save()

        self.assertEqual(MonthlyBudget.objects.count(), 2)

    def test_budgets_are_ordered_newest_month_first(self):
        january = self.build_budget(month=date(2026, 1, 1))
        january.save()
        march = self.build_budget(month=date(2026, 3, 1))
        march.save()
        february = self.build_budget(month=date(2026, 2, 1))
        february.save()

        self.assertEqual(
            list(MonthlyBudget.objects.filter(user=self.user)),
            [march, february, january],
        )


class MonthlyBudgetFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="suyesh", password="Str0ng-Passw0rd!23"
        )
        cls.other_user = User.objects.create_user(
            username="other", password="Str0ng-Passw0rd!23"
        )

    def test_new_form_defaults_to_the_current_month(self):
        form = MonthlyBudgetForm(user=self.user)

        self.assertEqual(
            form.initial["month"],
            timezone.localdate().replace(day=1),
        )
        self.assertIn('type="month"', form["month"].as_widget())

    def test_form_parses_a_month_value(self):
        form = MonthlyBudgetForm(
            data={"month": "2026-10", "amount": "1250.00"},
            user=self.user,
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["month"], date(2026, 10, 1))
        self.assertEqual(
            form.cleaned_data["amount"],
            Decimal("1250.00"),
        )

    def test_full_date_value_is_rejected(self):
        form = MonthlyBudgetForm(
            data={"month": "2026-10-01", "amount": "1250.00"},
            user=self.user,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("month", form.errors)

    def test_non_positive_amount_is_rejected(self):
        for amount in ("0", "0.00", "-1.00"):
            with self.subTest(amount=amount):
                form = MonthlyBudgetForm(
                    data={"month": "2026-10", "amount": amount},
                    user=self.user,
                )
                self.assertFalse(form.is_valid())
                self.assertIn("amount", form.errors)

    def test_duplicate_month_is_rejected(self):
        MonthlyBudget.objects.create(
            user=self.user,
            month=date(2026, 10, 1),
            amount=Decimal("1000.00"),
        )
        form = MonthlyBudgetForm(
            data={"month": "2026-10", "amount": "500.00"},
            user=self.user,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("month", form.errors)
        self.assertIn(
            "A budget already exists for this month",
            form.errors["month"][0],
        )

    def test_same_month_is_valid_for_another_user(self):
        MonthlyBudget.objects.create(
            user=self.other_user,
            month=date(2026, 10, 1),
            amount=Decimal("1000.00"),
        )
        form = MonthlyBudgetForm(
            data={"month": "2026-10", "amount": "500.00"},
            user=self.user,
        )

        self.assertTrue(form.is_valid())

    def test_editing_a_budget_does_not_conflict_with_itself(self):
        budget = MonthlyBudget.objects.create(
            user=self.user,
            month=date(2026, 10, 1),
            amount=Decimal("1000.00"),
        )
        form = MonthlyBudgetForm(
            data={"month": "2026-10", "amount": "1200.00"},
            instance=budget,
            user=self.user,
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(
            form.cleaned_data["amount"],
            Decimal("1200.00"),
        )

    def test_editing_into_another_existing_month_is_rejected(self):
        MonthlyBudget.objects.create(
            user=self.user,
            month=date(2026, 9, 1),
            amount=Decimal("900.00"),
        )
        budget = MonthlyBudget.objects.create(
            user=self.user,
            month=date(2026, 10, 1),
            amount=Decimal("1000.00"),
        )
        form = MonthlyBudgetForm(
            data={"month": "2026-09", "amount": "1200.00"},
            instance=budget,
            user=self.user,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("month", form.errors)


class BudgetSummaryServiceTests(SimpleTestCase):
    def test_summarizes_spending_below_budget(self):
        budget = SimpleNamespace(amount=Decimal("1000.00"))
        summary = summarize_budget(budget, Decimal("500.00"))

        self.assertEqual(summary["remaining"], Decimal("500.00"))
        self.assertEqual(summary["over_by"], Decimal("0.00"))
        self.assertEqual(summary["percentage"], Decimal("50.0"))
        self.assertEqual(summary["bar_width"], Decimal("50.0"))
        self.assertFalse(summary["is_over_budget"])
        self.assertFalse(summary["is_near_limit"])

    def test_near_limit_starts_at_eighty_percent(self):
        budget = SimpleNamespace(amount=Decimal("1000.00"))
        summary = summarize_budget(budget, Decimal("800.00"))

        self.assertEqual(summary["percentage"], Decimal("80.0"))
        self.assertTrue(summary["is_near_limit"])
        self.assertFalse(summary["is_over_budget"])

    def test_budget_at_exactly_one_hundred_percent_is_not_over(self):
        budget = SimpleNamespace(amount=Decimal("1000.00"))
        summary = summarize_budget(budget, Decimal("1000.00"))

        self.assertEqual(summary["remaining"], Decimal("0.00"))
        self.assertEqual(summary["percentage"], Decimal("100.0"))
        self.assertTrue(summary["is_near_limit"])
        self.assertFalse(summary["is_over_budget"])

    def test_over_budget_caps_progress_width(self):
        budget = SimpleNamespace(amount=Decimal("1000.00"))
        summary = summarize_budget(budget, Decimal("1200.00"))

        self.assertEqual(summary["remaining"], Decimal("-200.00"))
        self.assertEqual(summary["over_by"], Decimal("200.00"))
        self.assertEqual(summary["percentage"], Decimal("120.0"))
        self.assertEqual(summary["bar_width"], Decimal("100.0"))
        self.assertTrue(summary["is_over_budget"])
        self.assertFalse(summary["is_near_limit"])

    def test_no_spending(self):
        budget = SimpleNamespace(amount=Decimal("1000.00"))
        summary = summarize_budget(budget, Decimal("0.00"))

        self.assertEqual(summary["percentage"], Decimal("0.0"))
        self.assertEqual(summary["bar_width"], Decimal("0.0"))
        self.assertEqual(summary["remaining"], Decimal("1000.00"))
        self.assertFalse(summary["is_near_limit"])


class BudgetSummaryQueryTests(TestCase):
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

    def create_transaction(self, **overrides):
        values = {
            "user": self.user,
            "transaction_type": Transaction.Type.EXPENSE,
            "amount": Decimal("10.00"),
            "title": "Test transaction",
            "category": self.food,
            "date": date(2026, 1, 15),
        }
        values.update(overrides)
        return Transaction.objects.create(**values)

    def test_summaries_use_monthly_expenses_only(self):
        january = MonthlyBudget.objects.create(
            user=self.user,
            month=date(2026, 1, 1),
            amount=Decimal("100.00"),
        )
        february = MonthlyBudget.objects.create(
            user=self.user,
            month=date(2026, 2, 1),
            amount=Decimal("200.00"),
        )
        march = MonthlyBudget.objects.create(
            user=self.user,
            month=date(2026, 3, 1),
            amount=Decimal("300.00"),
        )
        self.create_transaction(
            amount=Decimal("80.00"),
            date=date(2026, 1, 10),
        )
        self.create_transaction(
            transaction_type=Transaction.Type.INCOME,
            category=self.salary,
            amount=Decimal("5000.00"),
            date=date(2026, 1, 11),
        )
        self.create_transaction(
            amount=Decimal("450.00"),
            date=date(2026, 3, 10),
        )
        self.create_transaction(
            user=self.other_user,
            category=self.other_food,
            amount=Decimal("900.00"),
            date=date(2026, 2, 10),
        )

        summaries = budget_summaries(
            self.user,
            [march, february, january],
        )

        self.assertEqual(
            [summary["spent"] for summary in summaries],
            [Decimal("450.00"), Decimal("0.00"), Decimal("80.00")],
        )
        self.assertEqual(
            [summary["remaining"] for summary in summaries],
            [Decimal("-150.00"), Decimal("200.00"), Decimal("20.00")],
        )
        self.assertEqual(
            [summary["percentage"] for summary in summaries],
            [Decimal("150.0"), Decimal("0.0"), Decimal("80.0")],
        )
        self.assertTrue(summaries[0]["is_over_budget"])
        self.assertTrue(summaries[2]["is_near_limit"])

    def test_empty_budget_list_returns_empty_summaries(self):
        self.assertEqual(budget_summaries(self.user, []), [])

    def test_summaries_use_one_expense_query(self):
        budgets = [
            MonthlyBudget.objects.create(
                user=self.user,
                month=date(2026, 1, 1),
                amount=Decimal("100.00"),
            ),
            MonthlyBudget.objects.create(
                user=self.user,
                month=date(2026, 2, 1),
                amount=Decimal("200.00"),
            ),
        ]

        with CaptureQueriesContext(connection) as queries:
            budget_summaries(self.user, budgets)

        self.assertEqual(len(queries), 1)


class BudgetViewTestCase(TestCase):
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

    def setUp(self):
        self.client.force_login(self.user)

    def create_budget(self, **overrides):
        values = {
            "user": self.user,
            "month": date(2026, 1, 1),
            "amount": Decimal("1000.00"),
        }
        values.update(overrides)
        return MonthlyBudget.objects.create(**values)

    def create_transaction(self, **overrides):
        values = {
            "user": self.user,
            "transaction_type": Transaction.Type.EXPENSE,
            "amount": Decimal("10.00"),
            "title": "Test transaction",
            "category": self.food,
            "date": date(2026, 1, 15),
        }
        values.update(overrides)
        return Transaction.objects.create(**values)


class BudgetLoginRequiredTests(BudgetViewTestCase):
    def setUp(self):
        super().setUp()
        self.budget = self.create_budget()
        self.client.logout()

    def test_private_budget_pages_require_login(self):
        urls = [
            reverse("budgets:list"),
            reverse("budgets:create"),
            reverse("budgets:edit", args=[self.budget.pk]),
            reverse("budgets:delete", args=[self.budget.pk]),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(
                    response,
                    f"{reverse('accounts:login')}?next={url}",
                )


class BudgetListTests(BudgetViewTestCase):
    def test_empty_budget_list(self):
        response = self.client.get(reverse("budgets:list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "budgets/list.html")
        self.assertContains(response, "No monthly budgets yet")
        self.assertContains(response, reverse("budgets:create"))

    def test_list_shows_only_the_users_budgets_with_usage(self):
        january = self.create_budget(
            month=date(2026, 1, 1),
            amount=Decimal("1000.00"),
        )
        self.create_budget(
            month=date(2026, 2, 1),
            amount=Decimal("500.00"),
        )
        self.create_budget(
            user=self.other_user,
            month=date(2026, 3, 1),
            amount=Decimal("999.00"),
        )
        self.create_transaction(
            amount=Decimal("1200.00"),
            date=date(2026, 1, 10),
        )
        self.create_transaction(
            amount=Decimal("400.00"),
            date=date(2026, 2, 10),
        )

        response = self.client.get(reverse("budgets:list"))

        self.assertContains(response, "January 2026")
        self.assertContains(response, "February 2026")
        self.assertNotContains(response, "March 2026")
        self.assertContains(response, "NPR 1000.00")
        self.assertContains(response, "NPR 1200.00")
        self.assertContains(response, "NPR 200.00 over")
        self.assertContains(response, "Over budget")
        self.assertContains(response, "Near limit")
        self.assertNotContains(response, "NPR 999.00")
        self.assertContains(
            response,
            reverse("budgets:edit", args=[january.pk]),
        )

    def test_current_month_is_marked(self):
        current_month = timezone.localdate().replace(day=1)
        budget = self.create_budget(month=current_month)

        response = self.client.get(reverse("budgets:list"))

        self.assertContains(response, "Current")
        self.assertContains(
            response,
            reverse("budgets:delete", args=[budget.pk]),
        )


class BudgetCreateTests(BudgetViewTestCase):
    def test_create_form_defaults_to_the_current_month(self):
        response = self.client.get(reverse("budgets:create"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["form"].initial["month"],
            timezone.localdate().replace(day=1),
        )
        self.assertContains(
            response,
            f'value="{timezone.localdate():%Y-%m}"',
        )

    def test_create_budget(self):
        response = self.client.post(
            reverse("budgets:create"),
            {"month": "2026-10", "amount": "1500.00"},
            follow=True,
        )

        budget = MonthlyBudget.objects.get()
        self.assertRedirects(response, reverse("budgets:list"))
        self.assertContains(
            response,
            "Budget set for October 2026: NPR 1,500.00.",
        )
        self.assertContains(
            response,
            'class="toast app-toast app-toast-success"',
        )
        self.assertEqual(budget.user, self.user)
        self.assertEqual(budget.month, date(2026, 10, 1))
        self.assertEqual(budget.amount, Decimal("1500.00"))

    def test_duplicate_month_is_rejected(self):
        self.create_budget(month=date(2026, 10, 1))

        response = self.client.post(
            reverse("budgets:create"),
            {"month": "2026-10", "amount": "500.00"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("month", response.context["form"].errors)
        self.assertEqual(MonthlyBudget.objects.count(), 1)

    def test_other_users_budget_does_not_block_this_user(self):
        self.create_budget(
            user=self.other_user,
            month=date(2026, 10, 1),
        )

        response = self.client.post(
            reverse("budgets:create"),
            {"month": "2026-10", "amount": "500.00"},
        )

        self.assertRedirects(response, reverse("budgets:list"))
        self.assertEqual(MonthlyBudget.objects.count(), 2)

    def test_non_positive_amount_is_rejected(self):
        response = self.client.post(
            reverse("budgets:create"),
            {"month": "2026-10", "amount": "0"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("amount", response.context["form"].errors)
        self.assertContains(
            response,
            "Budget was not saved. Please fix the highlighted fields.",
        )
        self.assertFalse(MonthlyBudget.objects.exists())


class BudgetEditTests(BudgetViewTestCase):
    def test_edit_form_renders_month_value(self):
        budget = self.create_budget(month=date(2026, 10, 1))

        response = self.client.get(
            reverse("budgets:edit", args=[budget.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="2026-10"')
        self.assertContains(response, 'value="1000.00"')

    def test_edit_budget(self):
        budget = self.create_budget(month=date(2026, 10, 1))

        response = self.client.post(
            reverse("budgets:edit", args=[budget.pk]),
            {"month": "2026-11", "amount": "1750.00"},
            follow=True,
        )

        budget.refresh_from_db()
        self.assertRedirects(response, reverse("budgets:list"))
        self.assertContains(
            response,
            "Budget for November 2026 updated: Month, Amount.",
        )
        self.assertEqual(budget.month, date(2026, 11, 1))
        self.assertEqual(budget.amount, Decimal("1750.00"))

    def test_cannot_edit_another_users_budget(self):
        budget = self.create_budget(user=self.other_user)

        response = self.client.get(
            reverse("budgets:edit", args=[budget.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_edit_rejects_a_month_that_already_has_a_budget(self):
        self.create_budget(month=date(2026, 9, 1))
        budget = self.create_budget(month=date(2026, 10, 1))

        response = self.client.post(
            reverse("budgets:edit", args=[budget.pk]),
            {"month": "2026-09", "amount": "1750.00"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("month", response.context["form"].errors)


class BudgetDeleteTests(BudgetViewTestCase):
    def test_delete_budget_does_not_delete_transactions(self):
        budget = self.create_budget(month=date(2026, 10, 1))
        transaction = self.create_transaction(date=date(2026, 10, 5))

        response = self.client.post(
            reverse("budgets:delete", args=[budget.pk]),
            follow=True,
        )

        self.assertRedirects(response, reverse("budgets:list"))
        self.assertContains(
            response,
            "Budget for October 2026 (NPR 1,000.00) removed.",
        )
        self.assertFalse(MonthlyBudget.objects.exists())
        self.assertTrue(
            Transaction.objects.filter(pk=transaction.pk).exists()
        )

    def test_delete_confirmation_renders(self):
        budget = self.create_budget(month=date(2026, 10, 1))

        response = self.client.get(
            reverse("budgets:delete", args=[budget.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "October 2026")
        self.assertContains(response, "Only the budget is removed.")

    def test_cannot_delete_another_users_budget(self):
        budget = self.create_budget(user=self.other_user)

        response = self.client.post(
            reverse("budgets:delete", args=[budget.pk])
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(MonthlyBudget.objects.filter(pk=budget.pk).exists())


class DashboardBudgetTests(BudgetViewTestCase):
    def test_dashboard_without_budget_shows_setup_link(self):
        response = self.client.get(reverse("core:dashboard"))

        self.assertContains(response, "No budget configured yet.")
        self.assertContains(response, reverse("budgets:create"))

    def test_dashboard_uses_current_month_budget_and_expenses(self):
        current_month = timezone.localdate().replace(day=1)
        budget = self.create_budget(
            month=current_month,
            amount=Decimal("1000.00"),
        )
        self.create_transaction(
            amount=Decimal("300.00"),
            date=timezone.localdate(),
        )
        self.create_transaction(
            transaction_type=Transaction.Type.INCOME,
            category=self.salary,
            amount=Decimal("5000.00"),
            date=timezone.localdate(),
        )

        response = self.client.get(reverse("core:dashboard"))

        status = response.context["budget_status"]
        self.assertEqual(response.context["budget"], budget)
        self.assertEqual(status["spent"], Decimal("300.00"))
        self.assertEqual(status["remaining"], Decimal("700.00"))
        self.assertEqual(status["percentage"], Decimal("30.0"))
        self.assertContains(response, "NPR 700.00")
        self.assertContains(response, "NPR 1000.00")
        self.assertContains(response, "30.0% used")
        self.assertContains(response, "On track")
        self.assertContains(
            response,
            reverse("budgets:edit", args=[budget.pk]),
        )

    def test_dashboard_shows_over_budget_state(self):
        current_month = timezone.localdate().replace(day=1)
        self.create_budget(
            month=current_month,
            amount=Decimal("100.00"),
        )
        self.create_transaction(
            amount=Decimal("150.00"),
            date=timezone.localdate(),
        )

        response = self.client.get(reverse("core:dashboard"))

        status = response.context["budget_status"]
        self.assertEqual(status["over_by"], Decimal("50.00"))
        self.assertEqual(status["percentage"], Decimal("150.0"))
        self.assertEqual(status["bar_width"], Decimal("100.0"))
        self.assertTrue(status["is_over_budget"])
        self.assertContains(response, "NPR 50.00")
        self.assertContains(response, "150.0% used")
        self.assertContains(response, "Over budget")

    def test_dashboard_ignores_budgets_for_other_months_and_users(self):
        self.create_budget(
            month=shift_month(timezone.localdate(), -1),
        )
        self.create_budget(
            user=self.other_user,
            month=timezone.localdate().replace(day=1),
        )

        response = self.client.get(reverse("core:dashboard"))

        self.assertIsNone(response.context["budget"])
        self.assertIsNone(response.context["budget_status"])
        self.assertContains(response, "No budget configured yet.")
