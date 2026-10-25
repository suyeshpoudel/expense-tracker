from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CategoryForm
from .models import Category


@login_required
def category_list(request):
    categories = request.user.categories.annotate(
        transaction_count=Count("transactions")
    )
    expense_categories = [
        category
        for category in categories
        if category.category_type == Category.Type.EXPENSE
    ]
    income_categories = [
        category
        for category in categories
        if category.category_type == Category.Type.INCOME
    ]

    return render(
        request,
        "categories/list.html",
        {
            "expense_categories": expense_categories,
            "income_categories": income_categories,
        },
    )


@login_required
def category_create(request):
    initial = {}
    requested_type = request.GET.get("type")
    if requested_type in Category.Type.values:
        initial["category_type"] = requested_type

    form = CategoryForm(
        request.POST or None,
        user=request.user,
        initial=initial,
    )

    if request.method == "POST" and form.is_valid():
        category = form.save(commit=False)
        category.user = request.user
        category.save()
        messages.success(request, "Category created successfully.")
        return redirect("categories:list")

    return render(
        request,
        "categories/form.html",
        {
            "form": form,
            "page_title": "Add category",
            "submit_label": "Save category",
        },
    )


@login_required
def category_edit(request, pk):
    category = get_object_or_404(
        Category,
        pk=pk,
        user=request.user,
    )
    form = CategoryForm(
        request.POST or None,
        instance=category,
        user=request.user,
    )

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Category updated successfully.")
        return redirect("categories:list")

    return render(
        request,
        "categories/form.html",
        {
            "form": form,
            "category": category,
            "page_title": "Edit category",
            "submit_label": "Save changes",
        },
    )


@login_required
def category_delete(request, pk):
    category = get_object_or_404(
        Category,
        pk=pk,
        user=request.user,
    )
    transaction_count = category.transactions.count()

    if request.method == "POST":
        if transaction_count:
            messages.error(
                request,
                f'"{category.name}" is used by {transaction_count} '
                f"transaction{'s' if transaction_count != 1 else ''} and "
                "cannot be deleted. Reassign or delete those transactions "
                "first.",
            )
            return redirect("categories:list")

        try:
            category.delete()
        except ProtectedError:
            messages.error(
                request,
                f'"{category.name}" is used by transactions and cannot be '
                "deleted.",
            )
            return redirect("categories:list")

        messages.success(request, "Category deleted successfully.")
        return redirect("categories:list")

    return render(
        request,
        "categories/confirm_delete.html",
        {
            "category": category,
            "transaction_count": transaction_count,
        },
    )
