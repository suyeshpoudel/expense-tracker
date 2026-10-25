from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class MonthlyBudget(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="budgets",
    )
    month = models.DateField(
        help_text="The first day of the month this budget applies to."
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-month"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "month"],
                name="uniq_budget_user_month",
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="budget_amount_positive",
            ),
        ]

    def __str__(self):
        return f"{self.month:%B %Y}: {self.amount}"

    def clean(self):
        super().clean()
        if self.month and self.month.day != 1:
            raise ValidationError(
                {"month": "Budget month must be the first day of the month."}
            )
