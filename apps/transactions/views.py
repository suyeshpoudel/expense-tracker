from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404, redirect, render

from apps.common.forms import changed_field_labels

from .forms import TransactionFilterForm, TransactionForm
from .models import Transaction

PAGE_SIZE = 20

SORT_ORDERS = {
    TransactionFilterForm.Sort.NEWEST: ("-date", "-created_at"),
    TransactionFilterForm.Sort.OLDEST: ("date", "created_at"),
    TransactionFilterForm.Sort.AMOUNT_DESC: ("-amount", "-date"),
    TransactionFilterForm.Sort.AMOUNT_ASC: ("amount", "-date"),
    TransactionFilterForm.Sort.TITLE: (Lower("title"), "-date"),
}


def user_transactions(user):
    return Transaction.objects.filter(user=user).select_related("category")


@login_required
def transaction_list(request):
    filter_form = TransactionFilterForm(request.GET or None, user=request.user)
    transactions = user_transactions(request.user)

    if filter_form.is_bound and filter_form.is_valid():
        filters = filter_form.cleaned_data
        if filters["q"]:
            transactions = transactions.filter(
                Q(title__icontains=filters["q"])
                | Q(notes__icontains=filters["q"])
                | Q(category__name__icontains=filters["q"])
            )
        if filters["type"]:
            transactions = transactions.filter(
                transaction_type=filters["type"]
            )
        if filters["category"]:
            transactions = transactions.filter(category=filters["category"])
        if filters["date_from"]:
            transactions = transactions.filter(
                date__gte=filters["date_from"]
            )
        if filters["date_to"]:
            transactions = transactions.filter(date__lte=filters["date_to"])
        if filters["amount_min"] is not None:
            transactions = transactions.filter(
                amount__gte=filters["amount_min"]
            )
        if filters["amount_max"] is not None:
            transactions = transactions.filter(
                amount__lte=filters["amount_max"]
            )

        sort = filters["sort"] or TransactionFilterForm.Sort.NEWEST
        transactions = transactions.order_by(*SORT_ORDERS[sort])

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

    has_filters = False
    if filter_form.is_bound and filter_form.is_valid():
        filters = filter_form.cleaned_data
        has_filters = any(
            [
                filters["q"],
                filters["type"],
                filters["category"],
                filters["date_from"],
                filters["date_to"],
                filters["amount_min"] is not None,
                filters["amount_max"] is not None,
            ]
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

    form = TransactionForm(
        request.POST or None,
        user=request.user,
        initial=initial,
    )

    if request.method == "POST":
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.save()
            messages.success(
                request,
                f'{transaction.get_transaction_type_display()} '
                f'"{transaction.title}" for {settings.CURRENCY_CODE} '
                f"{transaction.amount:,.2f} added.",
            )
            return redirect("transactions:detail", pk=transaction.pk)
        messages.error(
            request,
            "Transaction was not added. Please fix the highlighted fields.",
        )

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
        Transaction.objects.select_related("category"),
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
        Transaction.objects.select_related("category"),
        pk=pk,
        user=request.user,
    )
    form = TransactionForm(
        request.POST or None,
        instance=transaction,
        user=request.user,
    )

    if request.method == "POST":
        if form.is_valid():
            changed_labels = changed_field_labels(form)
            transaction = form.save()
            if changed_labels:
                messages.success(
                    request,
                    f'Transaction "{transaction.title}" updated: '
                    f'{", ".join(changed_labels)}.',
                )
            else:
                messages.info(
                    request,
                    f'Transaction "{transaction.title}" saved. '
                    "No changes were detected.",
                )
            return redirect("transactions:detail", pk=transaction.pk)
        messages.error(
            request,
            "Transaction was not updated. Please fix the highlighted fields.",
        )

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
        Transaction.objects.select_related("category"),
        pk=pk,
        user=request.user,
    )

    if request.method == "POST":
        title = transaction.title
        transaction.delete()
        messages.success(
            request,
            f'Transaction "{title}" deleted.',
        )
        return redirect("transactions:list")

    return render(
        request,
        "transactions/confirm_delete.html",
        {"transaction": transaction},
    )
