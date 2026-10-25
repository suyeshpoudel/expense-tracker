from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase

from apps.categories.models import Category
from apps.transactions.models import Transaction

from .services import (
    expense_breakdown,
    month_bounds,
    monthly_expense_trend,
    shift_month,
    transaction_totals,
)


class DateHelperTests(SimpleTestCase):
    def test_month_bounds_returns_full_calendar_month(self):
        self.assertEqual(
            month_bounds(date(2026, 2, 14)),
            (date(2026, 2, 1), date(2026, 2, 28)),
        )
        self.assertEqual(
            month_bounds(date(2028, 2, 14)),
            (date(2028, 2, 1), date(2028, 2, 29)),
        )

    def test_shift_month_handles_year_boundaries(self):
        self.assertEqual(
            shift_month(date(2026, 1, 1), -1),
            date(2025, 12, 1),
        )
        self.assertEqual(
            shift_month(date(2026, 1, 1), 13),
            date(2027, 2, 1),
        )
        self.assertEqual(
            shift_month(date(2026, 1, 1), 0),
            date(2026, 1, 1),
        )


class ReportServiceTestCase(TestCase):
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


class TransactionTotalsTests(ReportServiceTestCase):
    def test_separates_expenses_and_income(self):
        self.create_transaction(amount=Decimal("100.50"))
        self.create_transaction(amount=Decimal("20.25"))
        self.create_transaction(
            transaction_type=Transaction.Type.INCOME,
            category=self.salary,
            amount=Decimal("2000.00"),
        )

        totals = transaction_totals(
            self.user,
            date(2026, 1, 1),
            date(2026, 1, 31),
        )

        self.assertEqual(totals["expenses"], Decimal("120.75"))
        self.assertEqual(totals["income"], Decimal("2000.00"))
        self.assertEqual(totals["net"], Decimal("1879.25"))

    def test_date_range_is_inclusive_and_excludes_outside_dates(self):
        self.create_transaction(
            amount=Decimal("10.00"),
            date=date(2026, 1, 1),
        )
        self.create_transaction(
            amount=Decimal("20.00"),
            date=date(2026, 1, 31),
        )
        self.create_transaction(
            amount=Decimal("30.00"),
            date=date(2025, 12, 31),
        )
        self.create_transaction(
            amount=Decimal("40.00"),
            date=date(2026, 2, 1),
        )

        totals = transaction_totals(
            self.user,
            date(2026, 1, 1),
            date(2026, 1, 31),
        )

        self.assertEqual(totals["expenses"], Decimal("30.00"))

    def test_excludes_other_users(self):
        self.create_transaction(amount=Decimal("25.00"))
        self.create_transaction(
            user=self.other_user,
            category=self.other_food,
            amount=Decimal("900.00"),
        )
        self.create_transaction(
            user=self.other_user,
            transaction_type=Transaction.Type.INCOME,
            category=self.other_salary,
            amount=Decimal("1500.00"),
        )

        totals = transaction_totals(
            self.user,
            date(2026, 1, 1),
            date(2026, 1, 31),
        )

        self.assertEqual(totals["expenses"], Decimal("25.00"))
        self.assertEqual(totals["income"], Decimal("0.00"))

    def test_net_cash_flow_can_be_negative(self):
        self.create_transaction(amount=Decimal("100.00"))
        self.create_transaction(
            transaction_type=Transaction.Type.INCOME,
            category=self.salary,
            amount=Decimal("40.00"),
        )

        totals = transaction_totals(
            self.user,
            date(2026, 1, 1),
            date(2026, 1, 31),
        )

        self.assertEqual(totals["net"], Decimal("-60.00"))

    def test_empty_range_returns_zero_totals(self):
        totals = transaction_totals(
            self.user,
            date(2026, 4, 1),
            date(2026, 4, 30),
        )

        self.assertEqual(totals["expenses"], Decimal("0.00"))
        self.assertEqual(totals["income"], Decimal("0.00"))
        self.assertEqual(totals["net"], Decimal("0.00"))


class ExpenseBreakdownTests(ReportServiceTestCase):
    def test_groups_category_totals_and_calculates_shares(self):
        self.create_transaction(
            category=self.food,
            amount=Decimal("75.00"),
        )
        self.create_transaction(
            category=self.food,
            amount=Decimal("25.00"),
        )
        self.create_transaction(
            category=self.transport,
            amount=Decimal("50.00"),
        )
        self.create_transaction(
            category=None,
            amount=Decimal("25.00"),
        )
        self.create_transaction(
            transaction_type=Transaction.Type.INCOME,
            category=self.salary,
            amount=Decimal("1000.00"),
        )

        breakdown = expense_breakdown(
            self.user,
            date(2026, 1, 1),
            date(2026, 1, 31),
        )

        self.assertEqual(
            [item["name"] for item in breakdown],
            ["Food and groceries", "Transport", "Uncategorized"],
        )
        self.assertEqual(
            [item["total"] for item in breakdown],
            [Decimal("100.00"), Decimal("50.00"), Decimal("25.00")],
        )
        self.assertEqual(
            [item["count"] for item in breakdown],
            [2, 1, 1],
        )
        self.assertEqual(
            [item["percentage"] for item in breakdown],
            [Decimal("57.1"), Decimal("28.6"), Decimal("14.3")],
        )

    def test_excludes_other_users_and_outside_dates(self):
        self.create_transaction(amount=Decimal("20.00"))
        self.create_transaction(
            user=self.other_user,
            category=self.other_food,
            amount=Decimal("90.00"),
        )
        self.create_transaction(
            amount=Decimal("40.00"),
            date=date(2026, 2, 1),
        )

        breakdown = expense_breakdown(
            self.user,
            date(2026, 1, 1),
            date(2026, 1, 31),
        )

        self.assertEqual(len(breakdown), 1)
        self.assertEqual(breakdown[0]["total"], Decimal("20.00"))
        self.assertEqual(breakdown[0]["percentage"], Decimal("100.0"))

    def test_empty_range_returns_an_empty_list(self):
        self.create_transaction(amount=Decimal("20.00"))

        breakdown = expense_breakdown(
            self.user,
            date(2026, 3, 1),
            date(2026, 3, 31),
        )

        self.assertEqual(breakdown, [])


class MonthlyExpenseTrendTests(ReportServiceTestCase):
    def test_fills_months_with_no_expenses(self):
        self.create_transaction(
            amount=Decimal("10.00"),
            date=date(2026, 1, 5),
        )
        self.create_transaction(
            amount=Decimal("30.00"),
            date=date(2026, 3, 10),
        )

        trend = monthly_expense_trend(
            self.user,
            date(2026, 1, 1),
            date(2026, 3, 31),
        )

        self.assertEqual(
            [item["label"] for item in trend],
            ["Jan 2026", "Feb 2026", "Mar 2026"],
        )
        self.assertEqual(
            [item["total"] for item in trend],
            [Decimal("10.00"), Decimal("0.00"), Decimal("30.00")],
        )

    def test_includes_only_expenses_for_the_user_in_range(self):
        self.create_transaction(
            amount=Decimal("10.00"),
            date=date(2026, 1, 5),
        )
        self.create_transaction(
            transaction_type=Transaction.Type.INCOME,
            category=self.salary,
            amount=Decimal("500.00"),
            date=date(2026, 1, 6),
        )
        self.create_transaction(
            user=self.other_user,
            category=self.other_food,
            amount=Decimal("80.00"),
            date=date(2026, 1, 7),
        )
        self.create_transaction(
            amount=Decimal("20.00"),
            date=date(2025, 12, 31),
        )
        self.create_transaction(
            amount=Decimal("30.00"),
            date=date(2026, 2, 1),
        )

        trend = monthly_expense_trend(
            self.user,
            date(2026, 1, 1),
            date(2026, 1, 31),
        )

        self.assertEqual(len(trend), 1)
        self.assertEqual(trend[0]["total"], Decimal("10.00"))

    def test_partial_month_range_only_counts_selected_dates(self):
        self.create_transaction(
            amount=Decimal("10.00"),
            date=date(2026, 1, 10),
        )
        self.create_transaction(
            amount=Decimal("20.00"),
            date=date(2026, 1, 20),
        )

        trend = monthly_expense_trend(
            self.user,
            date(2026, 1, 15),
            date(2026, 1, 31),
        )

        self.assertEqual(trend[0]["total"], Decimal("20.00"))

    def test_spans_year_boundaries(self):
        self.create_transaction(
            amount=Decimal("10.00"),
            date=date(2025, 12, 20),
        )
        self.create_transaction(
            amount=Decimal("20.00"),
            date=date(2026, 1, 20),
        )
        self.create_transaction(
            amount=Decimal("30.00"),
            date=date(2026, 2, 20),
        )

        trend = monthly_expense_trend(
            self.user,
            date(2025, 12, 1),
            date(2026, 2, 28),
        )

        self.assertEqual(
            [item["total"] for item in trend],
            [Decimal("10.00"), Decimal("20.00"), Decimal("30.00")],
        )

    def test_invalid_date_range_raises_value_error(self):
        with self.assertRaises(ValueError):
            monthly_expense_trend(
                self.user,
                date(2026, 2, 1),
                date(2026, 1, 1),
            )
