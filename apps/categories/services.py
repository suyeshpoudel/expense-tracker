from django.db import transaction

from .models import Category

DEFAULT_EXPENSE_CATEGORIES = (
    "Food and groceries",
    "Transportation",
    "Housing and utilities",
    "Shopping",
    "Health",
    "Education",
    "Entertainment",
    "Subscriptions",
    "Personal care",
    "Other",
)

DEFAULT_INCOME_CATEGORIES = (
    "Salary",
    "Freelance work",
    "Business",
    "Investments",
    "Gifts",
    "Other income",
)

DEFAULT_CATEGORIES = {
    Category.Type.EXPENSE: DEFAULT_EXPENSE_CATEGORIES,
    Category.Type.INCOME: DEFAULT_INCOME_CATEGORIES,
}


def seed_default_categories(user):
    """Create any missing default categories and return the number created."""
    created_count = 0

    with transaction.atomic():
        for category_type, names in DEFAULT_CATEGORIES.items():
            for name in names:
                _, created = Category.objects.get_or_create(
                    user=user,
                    category_type=category_type,
                    name=name,
                )
                created_count += int(created)

    return created_count
