from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction as db_transaction
from django.test import TestCase
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
