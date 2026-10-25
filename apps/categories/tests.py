from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.transactions.models import Transaction

from .models import Category
from .services import seed_default_categories


class DefaultCategoryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="suyesh", password="Str0ng-Passw0rd!23"
        )

    def test_seed_creates_defaults_and_is_idempotent(self):
        created = seed_default_categories(self.user)

        self.assertEqual(created, 16)
        self.assertEqual(
            self.user.categories.filter(
                category_type=Category.Type.EXPENSE
            ).count(),
            10,
        )
        self.assertEqual(
            self.user.categories.filter(
                category_type=Category.Type.INCOME
            ).count(),
            6,
        )
        self.assertTrue(
            self.user.categories.filter(
                name="Food and groceries",
                category_type=Category.Type.EXPENSE,
            ).exists()
        )

        self.assertEqual(seed_default_categories(self.user), 0)
        self.assertEqual(self.user.categories.count(), 16)

    def test_seed_is_scoped_per_user(self):
        other_user = User.objects.create_user(
            username="other", password="Str0ng-Passw0rd!23"
        )

        seed_default_categories(self.user)
        seed_default_categories(other_user)

        self.assertEqual(self.user.categories.count(), 16)
        self.assertEqual(other_user.categories.count(), 16)
        self.assertFalse(
            self.user.categories.filter(user=other_user).exists()
        )

    def test_registration_seeds_default_categories(self):
        self.client.post(
            reverse("accounts:register"),
            {
                "username": "newuser",
                "email": "",
                "password1": "Str0ng-Passw0rd!23",
                "password2": "Str0ng-Passw0rd!23",
            },
        )

        user = User.objects.get(username="newuser")
        self.assertEqual(user.categories.count(), 16)


class SeedDefaultCategoriesCommandTests(TestCase):
    def test_command_seeds_existing_user_idempotently(self):
        user = User.objects.create_user(
            username="suyesh", password="Str0ng-Passw0rd!23"
        )

        output = StringIO()
        call_command(
            "seed_default_categories",
            "--user",
            user.username,
            stdout=output,
        )

        self.assertEqual(user.categories.count(), 16)
        self.assertIn("Created 16 default categories", output.getvalue())

        second_output = StringIO()
        call_command(
            "seed_default_categories",
            "--user",
            user.username,
            stdout=second_output,
        )
        self.assertEqual(user.categories.count(), 16)
        self.assertIn("Created 0 default categories", second_output.getvalue())

    def test_command_rejects_unknown_user(self):
        with self.assertRaises(CommandError):
            call_command("seed_default_categories", "--user", "missing")


class CategoryViewTestCase(TestCase):
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
        cls.other_category = Category.objects.create(
            user=cls.other_user,
            category_type=Category.Type.EXPENSE,
            name="Secret category",
        )

    def setUp(self):
        self.client.force_login(self.user)


class CategoryLoginRequiredTests(CategoryViewTestCase):
    def setUp(self):
        super().setUp()
        self.client.logout()

    def test_category_pages_require_login(self):
        urls = [
            reverse("categories:list"),
            reverse("categories:create"),
            reverse("categories:edit", args=[self.expense_category.pk]),
            reverse("categories:delete", args=[self.expense_category.pk]),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(
                    response,
                    f"{reverse('accounts:login')}?next={url}",
                )


class CategoryListTests(CategoryViewTestCase):
    def test_list_shows_only_the_users_categories(self):
        response = self.client.get(reverse("categories:list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "categories/list.html")
        self.assertContains(response, "Food and groceries")
        self.assertContains(response, "Salary")
        self.assertNotContains(response, "Secret category")

    def test_list_shows_transaction_counts(self):
        Transaction.objects.create(
            user=self.user,
            transaction_type=Transaction.Type.EXPENSE,
            category=self.expense_category,
            amount="15.00",
            title="Lunch",
            date=timezone.localdate(),
        )

        response = self.client.get(reverse("categories:list"))

        self.assertContains(response, "1 transaction")


class CategoryCreateTests(CategoryViewTestCase):
    def setUp(self):
        super().setUp()
        self.create_url = reverse("categories:create")

    def test_create_form_prefills_requested_type(self):
        response = self.client.get(f"{self.create_url}?type=income")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["form"]["category_type"].value(),
            "income",
        )

    def test_create_expense_category(self):
        response = self.client.post(
            self.create_url,
            {
                "category_type": Category.Type.EXPENSE,
                "name": "Travel",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("categories:list"))
        self.assertContains(
            response,
            'Expense category &quot;Travel&quot; created.',
        )
        self.assertContains(
            response,
            'class="toast app-toast app-toast-success"',
        )
        category = Category.objects.get(name="Travel")
        self.assertEqual(category.user, self.user)
        self.assertEqual(
            category.category_type,
            Category.Type.EXPENSE,
        )

    def test_create_income_category(self):
        response = self.client.post(
            self.create_url,
            {
                "category_type": Category.Type.INCOME,
                "name": "Rental income",
            },
        )

        self.assertRedirects(response, reverse("categories:list"))
        category = Category.objects.get(name="Rental income")
        self.assertEqual(
            category.category_type,
            Category.Type.INCOME,
        )
        self.assertEqual(category.user, self.user)

    def test_user_is_always_the_logged_in_user(self):
        self.client.post(
            self.create_url,
            {
                "category_type": Category.Type.EXPENSE,
                "name": "Travel",
                "user": self.other_user.pk,
            },
        )

        self.assertEqual(Category.objects.get(name="Travel").user, self.user)

    def test_duplicate_name_within_type_is_rejected_case_insensitively(self):
        response = self.client.post(
            self.create_url,
            {
                "category_type": Category.Type.EXPENSE,
                "name": "food AND groceries",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "You already have a category with this name.",
        )
        self.assertEqual(Category.objects.filter(user=self.user).count(), 2)

    def test_same_name_can_exist_for_different_types(self):
        response = self.client.post(
            self.create_url,
            {
                "category_type": Category.Type.INCOME,
                "name": "Food and groceries",
            },
        )

        self.assertRedirects(response, reverse("categories:list"))
        self.assertTrue(
            Category.objects.filter(
                user=self.user,
                name="Food and groceries",
                category_type=Category.Type.INCOME,
            ).exists()
        )

    def test_blank_name_is_rejected(self):
        response = self.client.post(
            self.create_url,
            {
                "category_type": Category.Type.EXPENSE,
                "name": "   ",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("name", response.context["form"].errors)
        self.assertContains(
            response,
            "Category was not created. Please fix the highlighted fields.",
        )
        self.assertContains(
            response,
            'class="toast app-toast app-toast-danger"',
        )


class CategoryEditTests(CategoryViewTestCase):
    def test_edit_renames_category_and_preserves_transactions(self):
        transaction = Transaction.objects.create(
            user=self.user,
            transaction_type=Transaction.Type.EXPENSE,
            category=self.expense_category,
            amount="15.00",
            title="Lunch",
            date=timezone.localdate(),
        )

        response = self.client.post(
            reverse("categories:edit", args=[self.expense_category.pk]),
            {
                "category_type": Category.Type.EXPENSE,
                "name": "Groceries and food",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("categories:list"))
        self.assertContains(
            response,
            'Category &quot;Food and groceries&quot; renamed to '
            '&quot;Groceries and food&quot;.',
        )
        transaction.refresh_from_db()
        self.assertEqual(transaction.category_id, self.expense_category.pk)
        self.assertEqual(transaction.category.name, "Groceries and food")

    def test_category_type_cannot_be_changed(self):
        self.client.post(
            reverse("categories:edit", args=[self.expense_category.pk]),
            {
                "category_type": Category.Type.INCOME,
                "name": "Food and groceries",
            },
        )

        self.expense_category.refresh_from_db()
        self.assertEqual(
            self.expense_category.category_type,
            Category.Type.EXPENSE,
        )

    def test_duplicate_rename_is_rejected(self):
        Category.objects.create(
            user=self.user,
            category_type=Category.Type.EXPENSE,
            name="Transportation",
        )

        response = self.client.post(
            reverse("categories:edit", args=[self.expense_category.pk]),
            {
                "category_type": Category.Type.EXPENSE,
                "name": "transportation",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "You already have a category with this name.",
        )
        self.expense_category.refresh_from_db()
        self.assertEqual(
            self.expense_category.name,
            "Food and groceries",
        )


class CategoryDeleteTests(CategoryViewTestCase):
    def test_delete_unused_category(self):
        category = Category.objects.create(
            user=self.user,
            category_type=Category.Type.EXPENSE,
            name="Temporary",
        )

        confirmation = self.client.get(
            reverse("categories:delete", args=[category.pk])
        )
        self.assertEqual(confirmation.status_code, 200)
        self.assertTemplateUsed(
            confirmation,
            "categories/confirm_delete.html",
        )
        self.assertTrue(Category.objects.filter(pk=category.pk).exists())

        response = self.client.post(
            reverse("categories:delete", args=[category.pk]),
            follow=True,
        )

        self.assertRedirects(response, reverse("categories:list"))
        self.assertContains(response, 'Category &quot;Temporary&quot; deleted.')
        self.assertFalse(Category.objects.filter(pk=category.pk).exists())

    def test_delete_used_category_is_blocked(self):
        transaction = Transaction.objects.create(
            user=self.user,
            transaction_type=Transaction.Type.EXPENSE,
            category=self.expense_category,
            amount="15.00",
            title="Lunch",
            date=timezone.localdate(),
        )

        confirmation = self.client.get(
            reverse("categories:delete", args=[self.expense_category.pk])
        )
        self.assertContains(
            confirmation,
            "cannot be deleted",
        )
        self.assertNotContains(
            confirmation,
            "Delete category</button>",
        )

        response = self.client.post(
            reverse("categories:delete", args=[self.expense_category.pk])
        )

        self.assertRedirects(response, reverse("categories:list"))
        self.assertTrue(
            Category.objects.filter(pk=self.expense_category.pk).exists()
        )
        self.assertTrue(
            Transaction.objects.filter(pk=transaction.pk).exists()
        )

    def test_used_category_can_be_deleted_after_reassigning_transactions(self):
        transaction = Transaction.objects.create(
            user=self.user,
            transaction_type=Transaction.Type.EXPENSE,
            category=self.expense_category,
            amount="15.00",
            title="Lunch",
            date=timezone.localdate(),
        )
        replacement = Category.objects.create(
            user=self.user,
            category_type=Category.Type.EXPENSE,
            name="Meals",
        )
        transaction.category = replacement
        transaction.save()

        self.client.post(
            reverse("categories:delete", args=[self.expense_category.pk])
        )

        self.assertFalse(
            Category.objects.filter(pk=self.expense_category.pk).exists()
        )
        transaction.refresh_from_db()
        self.assertEqual(transaction.category, replacement)

    def test_other_users_category_cannot_be_deleted(self):
        delete_url = reverse(
            "categories:delete",
            args=[self.other_category.pk],
        )

        self.assertEqual(self.client.get(delete_url).status_code, 404)

        response = self.client.post(delete_url)

        self.assertEqual(response.status_code, 404)
        self.assertTrue(
            Category.objects.filter(pk=self.other_category.pk).exists()
        )

    def test_other_users_category_cannot_be_edited(self):
        edit_url = reverse("categories:edit", args=[self.other_category.pk])

        self.assertEqual(self.client.get(edit_url).status_code, 404)

        response = self.client.post(
            edit_url,
            {
                "category_type": Category.Type.EXPENSE,
                "name": "Hijacked",
            },
        )

        self.assertEqual(response.status_code, 404)
        self.other_category.refresh_from_db()
        self.assertEqual(self.other_category.name, "Secret category")
