from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from apps.budgets.models import MonthlyBudget
from apps.budgets.services import summarize_budget

from .forms import ReportFilterForm
from .services import (
    ZERO,
    expense_breakdown,
    month_bounds,
    monthly_expense_trend,
    shift_month,
    transaction_totals,
)


def home(request):
    return render(request, "core/home.html")


def _chart_payload(labels, values):
    return {
        "labels": labels,
        "values": [float(value) for value in values],
        "currency": settings.CURRENCY_CODE,
    }


def _report_presets(today):
    current_from, current_to = month_bounds(today)
    last_from = shift_month(current_from, -1)
    last_to = month_bounds(last_from)[1]

    return [
        {
            "label": "This month",
            "date_from": current_from,
            "date_to": current_to,
        },
        {
            "label": "Last month",
            "date_from": last_from,
            "date_to": last_to,
        },
        {
            "label": "Last 30 days",
            "date_from": today - timedelta(days=29),
            "date_to": today,
        },
        {
            "label": "Year to date",
            "date_from": today.replace(month=1, day=1),
            "date_to": today,
        },
    ]


def _format_period(date_from, date_to):
    if date_from == date_to:
        return f"{date_from:%b} {date_from.day}, {date_from.year}"
    if date_from.year == date_to.year and date_from.month == date_to.month:
        return f"{date_from:%b} {date_from.day}\u2013{date_to.day}, {date_to.year}"
    if date_from.year == date_to.year:
        return (
            f"{date_from:%b} {date_from.day} \u2013 "
            f"{date_to:%b} {date_to.day}, {date_to.year}"
        )
    return (
        f"{date_from:%b} {date_from.day}, {date_from.year} \u2013 "
        f"{date_to:%b} {date_to.day}, {date_to.year}"
    )


@login_required
def dashboard(request):
    today = timezone.localdate()
    period_from, period_to = month_bounds(today)
    trend_from = shift_month(period_from, -5)

    totals = transaction_totals(request.user, period_from, period_to)
    breakdown = expense_breakdown(request.user, period_from, period_to)
    trend = monthly_expense_trend(request.user, trend_from, period_to)
    budget = MonthlyBudget.objects.filter(
        user=request.user,
        month=period_from,
    ).first()
    budget_status = (
        summarize_budget(budget, totals["expenses"]) if budget else None
    )
    recent_transactions = request.user.transactions.select_related(
        "category"
    )[:5]

    return render(
        request,
        "core/dashboard.html",
        {
            "month_label": today.strftime("%B %Y"),
            "period_label": today.strftime("%B %Y"),
            "total_expenses": totals["expenses"],
            "total_income": totals["income"],
            "net_total": totals["net"],
            "expense_breakdown": breakdown,
            "has_expenses": totals["expenses"] > 0,
            "category_chart_data": _chart_payload(
                [item["name"] for item in breakdown],
                [item["total"] for item in breakdown],
            ),
            "trend": trend,
            "trend_has_data": any(item["total"] > 0 for item in trend),
            "trend_chart_data": _chart_payload(
                [item["label"] for item in trend],
                [item["total"] for item in trend],
            ),
            "trend_label": "Last 6 months",
            "budget": budget,
            "budget_status": budget_status,
            "recent_transactions": recent_transactions,
        },
    )


@login_required
def reports(request):
    today = timezone.localdate()
    default_from, default_to = month_bounds(today)
    form = ReportFilterForm(
        request.GET or None,
        initial={
            "date_from": default_from,
            "date_to": default_to,
        },
    )

    show_report = True
    if form.is_bound:
        if form.is_valid():
            date_from = form.cleaned_data["date_from"]
            date_to = form.cleaned_data["date_to"]
        else:
            show_report = False
            date_from, date_to = default_from, default_to
    else:
        date_from, date_to = default_from, default_to

    context = {
        "form": form,
        "show_report": show_report,
        "date_from": date_from,
        "date_to": date_to,
        "period_label": _format_period(date_from, date_to),
        "total_expenses": ZERO,
        "total_income": ZERO,
        "net_total": ZERO,
        "expense_breakdown": [],
        "has_expenses": False,
        "category_chart_data": _chart_payload([], []),
        "trend": [],
        "trend_has_data": False,
        "trend_chart_data": _chart_payload([], []),
        "trend_label": _format_period(date_from, date_to),
        "report_presets": _report_presets(today),
    }

    if show_report:
        totals = transaction_totals(
            request.user,
            date_from,
            date_to,
        )
        breakdown = expense_breakdown(
            request.user,
            date_from,
            date_to,
        )
        trend = monthly_expense_trend(
            request.user,
            date_from,
            date_to,
        )

        context.update(
            {
                "total_expenses": totals["expenses"],
                "total_income": totals["income"],
                "net_total": totals["net"],
                "expense_breakdown": breakdown,
                "has_expenses": totals["expenses"] > 0,
                "category_chart_data": _chart_payload(
                    [item["name"] for item in breakdown],
                    [item["total"] for item in breakdown],
                ),
                "trend": trend,
                "trend_has_data": any(
                    item["total"] > 0 for item in trend
                ),
                "trend_chart_data": _chart_payload(
                    [item["label"] for item in trend],
                    [item["total"] for item in trend],
                ),
            }
        )

    return render(request, "core/reports.html", context)
