from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from .forms import TransactionFilterForm, TransactionForm
from .models import Transaction

PAGE_SIZE = 20


def user_transactions(user):
    return Transaction.objects.filter(user=user)


@login_required
def transaction_list(request):
    filter_form = TransactionFilterForm(request.GET or None)
    transactions = user_transactions(request.user)

    if filter_form.is_bound and filter_form.is_valid():
        filters = filter_form.cleaned_data
        if filters["type"]:
            transactions = transactions.filter(
                transaction_type=filters["type"]
            )
        if filters["date_from"]:
            transactions = transactions.filter(
                date__gte=filters["date_from"]
            )
        if filters["date_to"]:
            transactions = transactions.filter(date__lte=filters["date_to"])

    totals = transactions.aggregate(
        expenses=Sum(
            "amount",
            filter=Q(transaction_type=Transaction.Type.EXPENSE),
        ),
        income=Sum(
            "amount",
            filter=Q(transaction_type=Transaction.Type.INCOME),
        ),
    )
    total_expenses = totals["expenses"] or Decimal("0.00")
    total_income = totals["income"] or Decimal("0.00")

    paginator = Paginator(transactions, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))

    query_params = request.GET.copy()
    query_params.pop("page", None)

    has_filters = bool(
        filter_form.is_bound
        and filter_form.is_valid()
        and any(filter_form.cleaned_data.values())
    )

    context = {
        "filter_form": filter_form,
        "page_obj": page_obj,
        "transactions": page_obj.object_list,
        "querystring": query_params.urlencode(),
        "page_range": paginator.get_elided_page_range(page_obj.number),
        "page_ellipsis": Paginator.ELLIPSIS,
        "has_filters": has_filters,
        "total_expenses": total_expenses,
        "total_income": total_income,
        "net_total": total_income - total_expenses,
    }
    return render(request, "transactions/list.html", context)


@login_required
def transaction_create(request):
    initial = {}
    requested_type = request.GET.get("type")
    if requested_type in Transaction.Type.values:
        initial["transaction_type"] = requested_type

    form = TransactionForm(request.POST or None, initial=initial)

    if request.method == "POST" and form.is_valid():
        transaction = form.save(commit=False)
        transaction.user = request.user
        transaction.save()
        messages.success(request, "Transaction added successfully.")
        return redirect("transactions:detail", pk=transaction.pk)

    return render(
        request,
        "transactions/form.html",
        {
            "form": form,
            "page_title": "Add transaction",
            "submit_label": "Save transaction",
        },
    )


@login_required
def transaction_detail(request, pk):
    transaction = get_object_or_404(
        Transaction,
        pk=pk,
        user=request.user,
    )
    return render(
        request,
        "transactions/detail.html",
        {"transaction": transaction},
    )


@login_required
def transaction_edit(request, pk):
    transaction = get_object_or_404(
        Transaction,
        pk=pk,
        user=request.user,
    )
    form = TransactionForm(request.POST or None, instance=transaction)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Transaction updated successfully.")
        return redirect("transactions:detail", pk=transaction.pk)

    return render(
        request,
        "transactions/form.html",
        {
            "form": form,
            "transaction": transaction,
            "page_title": "Edit transaction",
            "submit_label": "Save changes",
        },
    )


@login_required
def transaction_delete(request, pk):
    transaction = get_object_or_404(
        Transaction,
        pk=pk,
        user=request.user,
    )

    if request.method == "POST":
        transaction.delete()
        messages.success(request, "Transaction deleted.")
        return redirect("transactions:list")

    return render(
        request,
        "transactions/confirm_delete.html",
        {"transaction": transaction},
    )
