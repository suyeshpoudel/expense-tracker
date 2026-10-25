from django.conf import settings
from django.db import models


class Category(models.Model):
    class Type(models.TextChoices):
        EXPENSE = "expense", "Expense"
        INCOME = "income", "Income"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="categories",
    )
    category_type = models.CharField(
        max_length=10,
        choices=Type.choices,
        verbose_name="type",
    )
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ["category_type", "name"]
        verbose_name_plural = "categories"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "category_type", "name"],
                name="uniq_category_user_type_name",
            ),
        ]

    def __str__(self):
        return self.name
