from decimal import Decimal

from apps.core.services import (
    ZERO,
    month_bounds,
    monthly_expense_trend,
)

PERCENTAGE_PRECISION = Decimal("0.1")
NEAR_LIMIT_PERCENTAGE = Decimal("80.0")
FULL_PERCENTAGE = Decimal("100.0")


def summarize_budget(budget, spent):
    remaining = budget.amount - spent
    percentage = (
        spent * 100 / budget.amount
    ).quantize(PERCENTAGE_PRECISION)
    is_over_budget = remaining < 0

    return {
        "budget": budget,
        "spent": spent,
        "remaining": remaining,
        "over_by": max(spent - budget.amount, ZERO),
        "percentage": percentage,
        "bar_width": min(percentage, FULL_PERCENTAGE),
        "is_over_budget": is_over_budget,
        "is_near_limit": (
            not is_over_budget
            and percentage >= NEAR_LIMIT_PERCENTAGE
        ),
    }


def budget_summaries(user, budgets):
    budgets = list(budgets)
    if not budgets:
        return []

    months = [budget.month for budget in budgets]
    trend = monthly_expense_trend(
        user,
        min(months),
        month_bounds(max(months))[1],
    )
    spending_by_month = {
        (item["month"].year, item["month"].month): item["total"]
        for item in trend
    }

    return [
        summarize_budget(
            budget,
            spending_by_month.get(
                (budget.month.year, budget.month.month),
                ZERO,
            ),
        )
        for budget in budgets
    ]
