from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction as db_transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.categories.models import Category

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

    def test_category_type_must_match_transaction_type(self):
        category = Category.objects.create(
            user=self.user,
            category_type=Category.Type.INCOME,
            name="Salary",
        )
        transaction = self.build_transaction(
            category=category,
            transaction_type=Transaction.Type.EXPENSE,
        )

        with self.assertRaises(ValidationError) as context:
            transaction.full_clean()

        self.assertIn("category", context.exception.message_dict)

    def test_category_owner_must_match_transaction_owner(self):
        other_user = User.objects.create_user(
            username="other", password="Str0ng-Passw0rd!23"
        )
        other_category = Category.objects.create(
            user=other_user,
            category_type=Category.Type.EXPENSE,
            name="Other category",
        )
        transaction = self.build_transaction(category=other_category)

        with self.assertRaises(ValidationError) as context:
            transaction.full_clean()

        self.assertIn("category", context.exception.message_dict)

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
        cls.expense_category = Category.objects.create(
            user=cls.user,
            category_type=Category.Type.EXPENSE,
            name="Food and groceries",
        )
        cls.income_category = Category.objects.create(
            user=cls.user,
            category_type=Category.Type.INCOME,
            name="Salary",
        )
        cls.other_expense_category = Category.objects.create(
            user=cls.other_user,
            category_type=Category.Type.EXPENSE,
            name="Food and groceries",
        )
        cls.other_income_category = Category.objects.create(
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
                    self.expense_category
                    if transaction_type == Transaction.Type.EXPENSE
                    else self.income_category
                )
            else:
                category = (
                    self.other_expense_category
                    if transaction_type == Transaction.Type.EXPENSE
                    else self.other_income_category
                )
            overrides["category"] = category

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
            "category": self.expense_category.pk,
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
        self.assertEqual(transaction.category, self.expense_category)

    def test_create_income(self):
        data = self.valid_data(
            transaction_type=Transaction.Type.INCOME,
            category=self.income_category.pk,
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
        self.assertEqual(transaction.category, self.income_category)

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

    def test_category_is_required(self):
        data = self.valid_data()
        data.pop("category")

        response = self.client.post(self.create_url, data)

        self.assertEqual(response.status_code, 200)
        self.assertIn("category", response.context["form"].errors)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_category_must_match_transaction_type(self):
        response = self.client.post(
            self.create_url,
            self.valid_data(category=self.income_category.pk),
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("category", response.context["form"].errors)
        self.assertContains(
            response,
            "Choose a category that matches the transaction type.",
        )
        self.assertEqual(Transaction.objects.count(), 0)

    def test_other_users_category_cannot_be_used(self):
        response = self.client.post(
            self.create_url,
            self.valid_data(category=self.other_expense_category.pk),
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("category", response.context["form"].errors)
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
                "category": self.income_category.pk,
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
        self.assertEqual(transaction.category, self.income_category)
        self.assertEqual(transaction.user, self.user)

    def test_edit_cannot_change_owner(self):
        transaction = self.create_transaction()

        self.client.post(
            reverse("transactions:edit", args=[transaction.pk]),
            {
                "transaction_type": Transaction.Type.EXPENSE,
                "category": self.expense_category.pk,
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
                "category": self.income_category.pk,
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
            title="Freelance payment",
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
        self.assertNotContains(response, "Freelance payment")

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
        self.assertNotContains(response, "Freelance payment")

    def test_category_filter_shows_only_matching_transactions(self):
        transport = Category.objects.create(
            user=self.user,
            category_type=Category.Type.EXPENSE,
            name="Transportation",
        )
        self.create_transaction(
            title="Bus fare",
            category=transport,
            amount=Decimal("15.00"),
        )

        response = self.client.get(
            self.list_url,
            {"category": transport.pk},
        )

        self.assertContains(response, "Bus fare")
        self.assertNotContains(response, "Groceries")
        self.assertEqual(
            response.context["total_expenses"],
            Decimal("15.00"),
        )

    def test_other_users_category_filter_is_rejected(self):
        response = self.client.get(
            self.list_url,
            {"category": self.other_expense_category.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "category",
            response.context["filter_form"].errors,
        )
        self.assertNotContains(response, "Other user expense")

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
        self.assertNotContains(response, "Freelance payment")

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

    def test_search_matches_titles_case_insensitively(self):
        response = self.client.get(self.list_url, {"q": "freeLANCE"})

        self.assertContains(response, "Freelance payment")
        self.assertNotContains(response, "Groceries")
        self.assertNotContains(response, "Old expense")
        self.assertEqual(
            response.context["total_income"],
            Decimal("500.00"),
        )
        self.assertTrue(response.context["has_filters"])
        self.assertContains(response, "1 matching transaction")

    def test_search_matches_notes(self):
        self.create_transaction(
            title="Team lunch",
            notes="Shared with a client.",
            amount=Decimal("30.00"),
        )

        response = self.client.get(self.list_url, {"q": "client"})

        self.assertContains(response, "Team lunch")
        self.assertNotContains(response, "Groceries")

    def test_search_matches_category_names(self):
        transport = Category.objects.create(
            user=self.user,
            category_type=Category.Type.EXPENSE,
            name="Transportation",
        )
        self.create_transaction(
            title="Bus fare",
            category=transport,
            amount=Decimal("15.00"),
        )

        response = self.client.get(self.list_url, {"q": "transport"})

        self.assertContains(response, "Bus fare")
        self.assertNotContains(response, "Groceries")

    def test_search_is_scoped_to_the_user(self):
        response = self.client.get(self.list_url, {"q": "other user"})

        self.assertEqual(response.context["page_obj"].paginator.count, 0)
        self.assertNotContains(response, "Other user expense")

    def test_search_is_combined_with_other_filters(self):
        response = self.client.get(
            self.list_url,
            {
                "q": "payment",
                "type": Transaction.Type.EXPENSE,
            },
        )

        self.assertEqual(response.context["page_obj"].paginator.count, 0)
        self.assertContains(response, "No matching transactions")

    def test_blank_search_is_not_an_active_filter(self):
        response = self.client.get(self.list_url, {"q": "   "})

        self.assertFalse(response.context["has_filters"])
        self.assertEqual(response.context["page_obj"].paginator.count, 3)

    def test_amount_range_is_inclusive(self):
        response = self.client.get(
            self.list_url,
            {"amount_min": "25.50", "amount_max": "100.00"},
        )

        self.assertContains(response, "Groceries")
        self.assertContains(response, "Old expense")
        self.assertNotContains(response, "Freelance payment")
        self.assertEqual(
            response.context["total_expenses"],
            Decimal("125.50"),
        )
        self.assertEqual(
            response.context["total_income"],
            Decimal("0.00"),
        )

    def test_single_amount_boundary(self):
        response = self.client.get(
            self.list_url,
            {"amount_min": "100.00"},
        )

        self.assertContains(response, "Groceries")
        self.assertContains(response, "Freelance payment")
        self.assertNotContains(response, "Old expense")

    def test_reversed_amount_range_shows_error(self):
        response = self.client.get(
            self.list_url,
            {"amount_min": "200.00", "amount_max": "100.00"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Maximum amount must be on or after the minimum amount.",
        )

    def test_invalid_amount_shows_error(self):
        response = self.client.get(
            self.list_url,
            {"amount_min": "not-a-number"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter a number.")

    def test_sort_newest_first_by_default(self):
        response = self.client.get(self.list_url)

        self.assertEqual(
            [transaction.title for transaction in response.context["transactions"]],
            ["Freelance payment", "Groceries", "Old expense"],
        )

    def test_sort_oldest_first(self):
        response = self.client.get(
            self.list_url,
            {"sort": "oldest"},
        )

        self.assertEqual(
            [transaction.title for transaction in response.context["transactions"]],
            ["Old expense", "Groceries", "Freelance payment"],
        )

    def test_sort_amount_high_to_low(self):
        response = self.client.get(
            self.list_url,
            {"sort": "amount_desc"},
        )

        self.assertEqual(
            [transaction.title for transaction in response.context["transactions"]],
            ["Freelance payment", "Groceries", "Old expense"],
        )

    def test_sort_amount_low_to_high(self):
        response = self.client.get(
            self.list_url,
            {"sort": "amount_asc"},
        )

        self.assertEqual(
            [transaction.title for transaction in response.context["transactions"]],
            ["Old expense", "Groceries", "Freelance payment"],
        )

    def test_sort_title_alphabetically(self):
        response = self.client.get(
            self.list_url,
            {"sort": "title"},
        )

        self.assertEqual(
            [transaction.title for transaction in response.context["transactions"]],
            ["Freelance payment", "Groceries", "Old expense"],
        )

    def test_invalid_sort_shows_error(self):
        response = self.client.get(
            self.list_url,
            {"sort": "not-a-sort"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Select a valid choice.")

    def test_sort_alone_is_not_an_active_filter(self):
        response = self.client.get(
            self.list_url,
            {"sort": "oldest"},
        )

        self.assertFalse(response.context["has_filters"])
        self.assertContains(response, "3 transactions")


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
                category=cls.expense_category,
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

    def test_pagination_preserves_search_amount_and_sort(self):
        response = self.client.get(
            reverse("transactions:list"),
            {
                "q": "Transaction",
                "amount_min": "10.00",
                "sort": "oldest",
                "page": 2,
            },
        )

        self.assertEqual(
            response.context["querystring"],
            "q=Transaction&amount_min=10.00&sort=oldest",
        )
        self.assertContains(
            response,
            "q=Transaction&amp;amount_min=10.00&amp;sort=oldest&amp;page=1",
        )
