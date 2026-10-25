from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render

from apps.common.forms import changed_field_labels

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

    if request.method == "POST":
        if form.is_valid():
            category = form.save(commit=False)
            category.user = request.user
            category.save()
            messages.success(
                request,
                f'{category.get_category_type_display()} category '
                f'"{category.name}" created.',
            )
            return redirect("categories:list")
        messages.error(
            request,
            "Category was not created. Please fix the highlighted fields.",
        )

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
    old_name = category.name
    form = CategoryForm(
        request.POST or None,
        instance=category,
        user=request.user,
    )

    if request.method == "POST":
        if form.is_valid():
            changed_labels = changed_field_labels(form)
            category = form.save()
            if "Name" in changed_labels:
                messages.success(
                    request,
                    f'Category "{old_name}" renamed to "{category.name}".',
                )
            elif changed_labels:
                messages.success(
                    request,
                    f'Category "{category.name}" updated: '
                    f'{", ".join(changed_labels)}.',
                )
            else:
                messages.info(
                    request,
                    f'Category "{category.name}" saved. '
                    "No changes were detected.",
                )
            return redirect("categories:list")
        messages.error(
            request,
            "Category was not updated. Please fix the highlighted fields.",
        )

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

        messages.success(
            request,
            f'Category "{category.name}" deleted.',
        )
        return redirect("categories:list")

    return render(
        request,
        "categories/confirm_delete.html",
        {
            "category": category,
            "transaction_count": transaction_count,
        },
    )
