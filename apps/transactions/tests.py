from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction as db_transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Transaction


class TransactionModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="suyesh", password="Str0ng-Passw0rd!23"
        )

    def build_transaction(self, **overrides):
        values = {
            "user": self.user,
            "transaction_type": Transaction.Type.EXPENSE,
            "amount": Decimal("25.50"),
            "title": "Lunch",
            "date": timezone.localdate(),
        }
        values.update(overrides)
        return Transaction(**values)

    def test_positive_amount_is_valid(self):
        self.build_transaction().full_clean()

    def test_zero_amount_is_invalid(self):
        transaction = self.build_transaction(amount=Decimal("0.00"))

        with self.assertRaises(ValidationError) as context:
            transaction.full_clean()

        self.assertIn("amount", context.exception.message_dict)

    def test_negative_amount_is_invalid(self):
        transaction = self.build_transaction(amount=Decimal("-5.00"))

        with self.assertRaises(ValidationError) as context:
            transaction.full_clean()

        self.assertIn("amount", context.exception.message_dict)

    def test_database_rejects_non_positive_amount(self):
        with self.assertRaises(IntegrityError):
            with db_transaction.atomic():
                Transaction.objects.bulk_create(
                    [
                        self.build_transaction(amount=Decimal("-1.00")),
                    ]
                )

    def test_transactions_are_ordered_newest_first(self):
        today = timezone.localdate()
        older = Transaction.objects.create(
            user=self.user,
            transaction_type=Transaction.Type.EXPENSE,
            amount=Decimal("10.00"),
            title="Older",
            date=today - timedelta(days=2),
        )
        newer = Transaction.objects.create(
            user=self.user,
            transaction_type=Transaction.Type.INCOME,
            amount=Decimal("20.00"),
            title="Newer",
            date=today,
        )

        self.assertEqual(
            list(Transaction.objects.filter(user=self.user)),
            [newer, older],
        )


class TransactionViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="suyesh", password="Str0ng-Passw0rd!23"
        )
        cls.other_user = User.objects.create_user(
            username="other", password="Str0ng-Passw0rd!23"
        )

    def setUp(self):
        self.client.force_login(self.user)

    def create_transaction(self, **overrides):
        values = {
            "user": self.user,
            "transaction_type": Transaction.Type.EXPENSE,
            "amount": Decimal("10.00"),
            "title": "Coffee",
            "date": timezone.localdate(),
        }
        values.update(overrides)
        return Transaction.objects.create(**values)


class TransactionLoginRequiredTests(TransactionViewTestCase):
    def setUp(self):
        super().setUp()
        self.transaction = self.create_transaction()
        self.client.logout()

    def test_private_transaction_pages_require_login(self):
        urls = [
            reverse("transactions:list"),
            reverse("transactions:create"),
            reverse("transactions:detail", args=[self.transaction.pk]),
            reverse("transactions:edit", args=[self.transaction.pk]),
            reverse("transactions:delete", args=[self.transaction.pk]),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(
                    response,
                    f"{reverse('accounts:login')}?next={url}",
                )


class TransactionCreateTests(TransactionViewTestCase):
    def setUp(self):
        super().setUp()
        self.create_url = reverse("transactions:create")

    def valid_data(self, **overrides):
        data = {
            "transaction_type": Transaction.Type.EXPENSE,
            "amount": "1234.56",
            "title": "Monthly rent",
            "date": timezone.localdate().isoformat(),
            "notes": "Paid by bank transfer.",
        }
        data.update(overrides)
        return data

    def test_create_form_prefills_requested_type(self):
        response = self.client.get(
            f"{self.create_url}?type=income"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["form"]["transaction_type"].value(),
            "income",
        )

    def test_create_expense(self):
        response = self.client.post(self.create_url, self.valid_data())

        transaction = Transaction.objects.get()
        self.assertRedirects(
            response,
            reverse("transactions:detail", args=[transaction.pk]),
        )
        self.assertEqual(transaction.user, self.user)
        self.assertEqual(
            transaction.transaction_type,
            Transaction.Type.EXPENSE,
        )
        self.assertEqual(transaction.amount, Decimal("1234.56"))
        self.assertEqual(transaction.title, "Monthly rent")
        self.assertEqual(transaction.notes, "Paid by bank transfer.")

    def test_create_income(self):
        data = self.valid_data(
            transaction_type=Transaction.Type.INCOME,
            amount="5000.00",
            title="Freelance payment",
        )

        response = self.client.post(self.create_url, data)

        transaction = Transaction.objects.get()
        self.assertRedirects(
            response,
            reverse("transactions:detail", args=[transaction.pk]),
        )
        self.assertEqual(
            transaction.transaction_type,
            Transaction.Type.INCOME,
        )
        self.assertEqual(transaction.amount, Decimal("5000.00"))

    def test_user_is_always_the_logged_in_user(self):
        data = {
            **self.valid_data(),
            "user": self.other_user.pk,
        }

        self.client.post(self.create_url, data)

        self.assertEqual(Transaction.objects.get().user, self.user)

    def test_non_positive_amounts_are_rejected(self):
        for amount in ("0", "0.00", "-5.00"):
            with self.subTest(amount=amount):
                response = self.client.post(
                    self.create_url,
                    self.valid_data(amount=amount),
                )

                self.assertEqual(response.status_code, 200)
                self.assertIn(
                    "amount",
                    response.context["form"].errors,
                )
                self.assertEqual(Transaction.objects.count(), 0)

    def test_future_date_is_rejected(self):
        tomorrow = timezone.localdate() + timedelta(days=1)

        response = self.client.post(
            self.create_url,
            self.valid_data(date=tomorrow.isoformat()),
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("date", response.context["form"].errors)
        self.assertContains(
            response,
            "Transaction date cannot be in the future.",
        )
        self.assertEqual(Transaction.objects.count(), 0)

    def test_invalid_date_is_rejected(self):
        response = self.client.post(
            self.create_url,
            self.valid_data(date="not-a-date"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("date", response.context["form"].errors)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_blank_title_is_rejected(self):
        response = self.client.post(
            self.create_url,
            self.valid_data(title="   "),
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("title", response.context["form"].errors)
        self.assertEqual(Transaction.objects.count(), 0)


class TransactionDetailEditDeleteTests(TransactionViewTestCase):
    def test_detail_shows_transaction(self):
        transaction = self.create_transaction(
            title="Team lunch",
            amount=Decimal("75.25"),
            notes="Shared with colleagues.",
        )

        response = self.client.get(
            reverse("transactions:detail", args=[transaction.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "transactions/detail.html")
        self.assertContains(response, "Team lunch")
        self.assertContains(response, "75.25")
        self.assertContains(response, "Shared with colleagues.")

    def test_edit_updates_transaction(self):
        transaction = self.create_transaction()
        edit_url = reverse("transactions:edit", args=[transaction.pk])

        response = self.client.post(
            edit_url,
            {
                "transaction_type": Transaction.Type.INCOME,
                "amount": "42.00",
                "title": "Updated title",
                "date": transaction.date.isoformat(),
                "notes": "",
            },
        )

        self.assertRedirects(
            response,
            reverse("transactions:detail", args=[transaction.pk]),
        )
        transaction.refresh_from_db()
        self.assertEqual(transaction.transaction_type, Transaction.Type.INCOME)
        self.assertEqual(transaction.amount, Decimal("42.00"))
        self.assertEqual(transaction.title, "Updated title")
        self.assertEqual(transaction.user, self.user)

    def test_edit_cannot_change_owner(self):
        transaction = self.create_transaction()

        self.client.post(
            reverse("transactions:edit", args=[transaction.pk]),
            {
                "transaction_type": Transaction.Type.EXPENSE,
                "amount": "15.00",
                "title": "Still mine",
                "date": transaction.date.isoformat(),
                "notes": "",
                "user": self.other_user.pk,
            },
        )

        transaction.refresh_from_db()
        self.assertEqual(transaction.user, self.user)

    def test_delete_confirmation_does_not_delete(self):
        transaction = self.create_transaction()

        response = self.client.get(
            reverse("transactions:delete", args=[transaction.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "transactions/confirm_delete.html",
        )
        self.assertTrue(Transaction.objects.filter(pk=transaction.pk).exists())

    def test_delete_via_post(self):
        transaction = self.create_transaction()

        response = self.client.post(
            reverse("transactions:delete", args=[transaction.pk])
        )

        self.assertRedirects(response, reverse("transactions:list"))
        self.assertFalse(Transaction.objects.filter(pk=transaction.pk).exists())


class TransactionIsolationTests(TransactionViewTestCase):
    def test_list_excludes_other_users_transactions(self):
        self.create_transaction(title="My transaction")
        self.create_transaction(
            user=self.other_user,
            title="Other user transaction",
        )

        response = self.client.get(reverse("transactions:list"))

        self.assertContains(response, "My transaction")
        self.assertNotContains(response, "Other user transaction")

    def test_other_users_transaction_is_not_accessible(self):
        transaction = self.create_transaction(user=self.other_user)
        urls = [
            reverse("transactions:detail", args=[transaction.pk]),
            reverse("transactions:edit", args=[transaction.pk]),
            reverse("transactions:delete", args=[transaction.pk]),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 404)

    def test_other_users_transaction_cannot_be_edited(self):
        transaction = self.create_transaction(
            user=self.other_user,
            title="Original title",
        )

        response = self.client.post(
            reverse("transactions:edit", args=[transaction.pk]),
            {
                "transaction_type": Transaction.Type.INCOME,
                "amount": "999.00",
                "title": "Hijacked",
                "date": transaction.date.isoformat(),
                "notes": "",
            },
        )

        self.assertEqual(response.status_code, 404)
        transaction.refresh_from_db()
        self.assertEqual(transaction.title, "Original title")

    def test_other_users_transaction_cannot_be_deleted(self):
        transaction = self.create_transaction(user=self.other_user)

        response = self.client.post(
            reverse("transactions:delete", args=[transaction.pk])
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Transaction.objects.filter(pk=transaction.pk).exists())


class TransactionFilterTests(TransactionViewTestCase):
    def setUp(self):
        super().setUp()
        today = timezone.localdate()
        self.expense_recent = self.create_transaction(
            title="Groceries",
            amount=Decimal("100.00"),
            date=today,
        )
        self.income_recent = self.create_transaction(
            title="Salary",
            transaction_type=Transaction.Type.INCOME,
            amount=Decimal("500.00"),
            date=today,
        )
        self.expense_old = self.create_transaction(
            title="Old expense",
            amount=Decimal("25.50"),
            date=today - timedelta(days=10),
        )
        self.other_transaction = self.create_transaction(
            user=self.other_user,
            title="Other user expense",
            amount=Decimal("999.00"),
            date=today,
        )
        self.list_url = reverse("transactions:list")

    def test_type_filter_shows_only_matching_transactions(self):
        response = self.client.get(
            self.list_url,
            {"type": Transaction.Type.EXPENSE},
        )

        self.assertContains(response, "Groceries")
        self.assertContains(response, "Old expense")
        self.assertNotContains(response, "Salary")

    def test_type_filter_totals_are_filtered(self):
        response = self.client.get(
            self.list_url,
            {"type": Transaction.Type.EXPENSE},
        )

        self.assertEqual(
            response.context["total_expenses"],
            Decimal("125.50"),
        )
        self.assertEqual(
            response.context["total_income"],
            Decimal("0.00"),
        )
        self.assertEqual(
            response.context["net_total"],
            Decimal("-125.50"),
        )

    def test_income_filter_totals(self):
        response = self.client.get(
            self.list_url,
            {"type": Transaction.Type.INCOME},
        )

        self.assertEqual(
            response.context["total_income"],
            Decimal("500.00"),
        )
        self.assertEqual(
            response.context["total_expenses"],
            Decimal("0.00"),
        )
        self.assertEqual(
            response.context["net_total"],
            Decimal("500.00"),
        )

    def test_date_range_filter_is_inclusive(self):
        target_date = timezone.localdate() - timedelta(days=10)

        response = self.client.get(
            self.list_url,
            {
                "date_from": target_date.isoformat(),
                "date_to": target_date.isoformat(),
            },
        )

        self.assertContains(response, "Old expense")
        self.assertNotContains(response, "Groceries")
        self.assertNotContains(response, "Salary")

    def test_combined_filters(self):
        response = self.client.get(
            self.list_url,
            {
                "type": Transaction.Type.EXPENSE,
                "date_from": timezone.localdate().isoformat(),
            },
        )

        self.assertContains(response, "Groceries")
        self.assertNotContains(response, "Old expense")
        self.assertNotContains(response, "Salary")

    def test_invalid_date_range_shows_error(self):
        today = timezone.localdate()

        response = self.client.get(
            self.list_url,
            {
                "date_from": today.isoformat(),
                "date_to": (today - timedelta(days=5)).isoformat(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "End date must be on or after the start date.",
        )

    def test_invalid_date_value_shows_error(self):
        response = self.client.get(
            self.list_url,
            {"date_from": "not-a-date"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter a valid date.")

    def test_totals_use_accurate_decimal_arithmetic(self):
        Transaction.objects.filter(user=self.user).delete()
        today = timezone.localdate()
        self.create_transaction(
            title="Ten paisa",
            amount=Decimal("0.10"),
            date=today,
        )
        self.create_transaction(
            title="Twenty paisa",
            amount=Decimal("0.20"),
            date=today,
        )

        response = self.client.get(
            self.list_url,
            {"type": Transaction.Type.EXPENSE},
        )

        self.assertEqual(
            response.context["total_expenses"],
            Decimal("0.30"),
        )


class TransactionPaginationTests(TransactionViewTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        today = timezone.localdate()
        for index in range(25):
            Transaction.objects.create(
                user=cls.user,
                transaction_type=Transaction.Type.EXPENSE,
                amount=Decimal("10.00"),
                title=f"Transaction {index:02d}",
                date=today - timedelta(days=index),
            )

    def test_first_page_contains_twenty_transactions(self):
        response = self.client.get(reverse("transactions:list"))

        self.assertEqual(len(response.context["transactions"]), 20)
        self.assertTrue(response.context["page_obj"].has_next())
        self.assertContains(response, "Transaction 00")
        self.assertNotContains(response, "Transaction 20")

    def test_second_page_contains_remaining_transactions(self):
        response = self.client.get(
            reverse("transactions:list"),
            {"page": 2},
        )

        self.assertEqual(len(response.context["transactions"]), 5)
        self.assertFalse(response.context["page_obj"].has_next())
        self.assertContains(response, "Transaction 20")
        self.assertNotContains(response, "Transaction 00")

    def test_pagination_preserves_filters(self):
        response = self.client.get(
            reverse("transactions:list"),
            {
                "type": Transaction.Type.EXPENSE,
                "page": 2,
            },
        )

        self.assertEqual(response.context["querystring"], "type=expense")
        self.assertContains(response, "type=expense&amp;page=1")
