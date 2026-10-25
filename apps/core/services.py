from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.transactions.models import Transaction

ZERO = Decimal("0.00")
PERCENTAGE_PRECISION = Decimal("0.1")


def month_bounds(day=None):
    """Return the first and last day of the month containing ``day``."""
    day = day or timezone.localdate()
    first_day = day.replace(day=1)
    last_day = day.replace(day=monthrange(day.year, day.month)[1])
    return first_day, last_day


def shift_month(month_start, offset):
    """Shift a first-of-month date by ``offset`` calendar months."""
    month_index = month_start.year * 12 + month_start.month - 1 + offset
    year, month_index = divmod(month_index, 12)
    return date(year, month_index + 1, 1)


def transaction_totals(user, date_from, date_to):
    """Aggregate expenses and income for one inclusive date range."""
    totals = Transaction.objects.filter(
        user=user,
        date__range=(date_from, date_to),
    ).aggregate(
        expenses=Sum(
            "amount",
            filter=Q(transaction_type=Transaction.Type.EXPENSE),
        ),
        income=Sum(
            "amount",
            filter=Q(transaction_type=Transaction.Type.INCOME),
        ),
    )

    expenses = totals["expenses"] or ZERO
    income = totals["income"] or ZERO

    return {
        "expenses": expenses,
        "income": income,
        "net": income - expenses,
    }


def expense_breakdown(user, date_from, date_to):
    """Group expense totals by category for one inclusive date range."""
    rows = (
        Transaction.objects.filter(
            user=user,
            transaction_type=Transaction.Type.EXPENSE,
            date__range=(date_from, date_to),
        )
        .values("category_id", "category__name")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total", "category__name")
    )

    rows = list(rows)
    total_expenses = sum((row["total"] for row in rows), ZERO)

    return [
        {
            "name": row["category__name"] or "Uncategorized",
            "total": row["total"],
            "count": row["count"],
            "percentage": (
                row["total"] * 100 / total_expenses
            ).quantize(PERCENTAGE_PRECISION)
            if total_expenses
            else ZERO,
        }
        for row in rows
    ]


def monthly_expense_trend(user, date_from, date_to):
    """Return expense totals for every calendar month in the date range."""
    if date_from > date_to:
        raise ValueError("Start date must be on or before end date.")

    start_month = date_from.replace(day=1)
    end_month = date_to.replace(day=1)

    rows = (
        Transaction.objects.filter(
            user=user,
            transaction_type=Transaction.Type.EXPENSE,
            date__range=(date_from, date_to),
        )
        .annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(total=Sum("amount"))
        .order_by("month")
    )

    totals_by_month = {}
    for row in rows:
        month = row["month"]
        if isinstance(month, datetime):
            month = month.date()
        totals_by_month[(month.year, month.month)] = row["total"] or ZERO

    trend = []
    current_month = start_month
    while current_month <= end_month:
        trend.append(
            {
                "month": current_month,
                "label": current_month.strftime("%b %Y"),
                "total": totals_by_month.get(
                    (current_month.year, current_month.month),
                    ZERO,
                ),
            }
        )
        current_month = shift_month(current_month, 1)

    return trend
