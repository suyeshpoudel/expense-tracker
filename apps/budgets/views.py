from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.common.forms import changed_field_labels

from .forms import MonthlyBudgetForm
from .models import MonthlyBudget
from .services import budget_summaries


@login_required
def budget_list(request):
    summaries = budget_summaries(
        request.user,
        request.user.budgets.all(),
    )

    return render(
        request,
        "budgets/list.html",
        {
            "budget_summaries": summaries,
            "current_month": timezone.localdate().replace(day=1),
        },
    )


@login_required
def budget_create(request):
    form = MonthlyBudgetForm(
        request.POST or None,
        user=request.user,
    )

    if request.method == "POST":
        if form.is_valid():
            budget = form.save(commit=False)
            budget.user = request.user
            budget.save()
            messages.success(
                request,
                f"Budget set for {budget.month:%B %Y}: "
                f"{settings.CURRENCY_CODE} {budget.amount:,.2f}.",
            )
            return redirect("budgets:list")
        messages.error(
            request,
            "Budget was not saved. Please fix the highlighted fields.",
        )

    return render(
        request,
        "budgets/form.html",
        {
            "form": form,
            "page_title": "Set monthly budget",
            "submit_label": "Save budget",
        },
    )


@login_required
def budget_edit(request, pk):
    budget = get_object_or_404(
        MonthlyBudget,
        pk=pk,
        user=request.user,
    )
    form = MonthlyBudgetForm(
        request.POST or None,
        instance=budget,
        user=request.user,
    )

    if request.method == "POST":
        if form.is_valid():
            changed_labels = changed_field_labels(form)
            budget = form.save()
            if changed_labels:
                messages.success(
                    request,
                    f"Budget for {budget.month:%B %Y} updated: "
                    f"{', '.join(changed_labels)}.",
                )
            else:
                messages.info(
                    request,
                    f"Budget for {budget.month:%B %Y} saved. "
                    "No changes were detected.",
                )
            return redirect("budgets:list")
        messages.error(
            request,
            "Budget was not updated. Please fix the highlighted fields.",
        )

    return render(
        request,
        "budgets/form.html",
        {
            "form": form,
            "budget": budget,
            "page_title": "Edit monthly budget",
            "submit_label": "Save changes",
        },
    )


@login_required
def budget_delete(request, pk):
    budget = get_object_or_404(
        MonthlyBudget,
        pk=pk,
        user=request.user,
    )

    if request.method == "POST":
        month_label = f"{budget.month:%B %Y}"
        amount = f"{settings.CURRENCY_CODE} {budget.amount:,.2f}"
        budget.delete()
        messages.success(
            request,
            f"Budget for {month_label} ({amount}) removed.",
        )
        return redirect("budgets:list")

    return render(
        request,
        "budgets/confirm_delete.html",
        {"budget": budget},
    )
