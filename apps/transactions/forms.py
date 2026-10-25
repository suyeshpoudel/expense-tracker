from decimal import Decimal

from django import forms
from django.db import models
from django.utils import timezone

from apps.categories.forms import CategoryChoiceField
from apps.categories.models import Category
from apps.common.forms import BootstrapFormMixin

from .models import Transaction


class TransactionForm(BootstrapFormMixin, forms.ModelForm):
    category = CategoryChoiceField(
        queryset=Category.objects.none(),
        label="Category",
        empty_label="Select a category",
        help_text="Choose a category that matches the transaction type.",
    )

    class Meta:
        model = Transaction
        fields = (
            "transaction_type",
            "category",
            "amount",
            "title",
            "date",
            "notes",
        )
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
            "amount": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0.01",
                    "inputmode": "decimal",
                }
            ),
        }
        help_texts = {
            "amount": "Enter a positive amount.",
            "date": "Use today or an earlier date.",
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(user=user)
        self.apply_bootstrap_classes()
        self.order_fields(
            [
                "transaction_type",
                "category",
                "amount",
                "title",
                "date",
                "notes",
            ]
        )
        self.fields["title"].widget.attrs["autofocus"] = True
        self.fields["date"].widget.attrs["max"] = (
            timezone.localdate().isoformat()
        )

        if not self.is_bound and not self.instance.pk:
            self.initial.setdefault("date", timezone.localdate())

    def clean_date(self):
        value = self.cleaned_data["date"]
        if value and value > timezone.localdate():
            raise forms.ValidationError(
                "Transaction date cannot be in the future."
            )
        return value

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get("category")
        transaction_type = cleaned_data.get("transaction_type")

        if (
            category
            and transaction_type
            and category.category_type != transaction_type
        ):
            self.add_error(
                "category",
                "Choose a category that matches the transaction type.",
            )

        return cleaned_data


class TransactionFilterForm(BootstrapFormMixin, forms.Form):
    class Sort(models.TextChoices):
        NEWEST = "newest", "Newest first"
        OLDEST = "oldest", "Oldest first"
        AMOUNT_DESC = "amount_desc", "Amount: high to low"
        AMOUNT_ASC = "amount_asc", "Amount: low to high"
        TITLE = "title", "Title: A to Z"

    q = forms.CharField(
        required=False,
        label="Search",
        max_length=200,
        widget=forms.TextInput(
            attrs={
                "type": "search",
                "placeholder": "Title, notes, or category",
                "autocomplete": "off",
            }
        ),
    )
    type = forms.ChoiceField(
        required=False,
        label="Type",
        choices=[("", "All types"), *Transaction.Type.choices],
    )
    category = CategoryChoiceField(
        queryset=Category.objects.none(),
        required=False,
        label="Category",
        empty_label="All categories",
    )
    date_from = forms.DateField(
        required=False,
        label="From",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    date_to = forms.DateField(
        required=False,
        label="To",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    amount_min = forms.DecimalField(
        required=False,
        label="Min amount",
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.00"),
        widget=forms.NumberInput(
            attrs={
                "step": "0.01",
                "min": "0.00",
                "inputmode": "decimal",
            }
        ),
    )
    amount_max = forms.DecimalField(
        required=False,
        label="Max amount",
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.00"),
        widget=forms.NumberInput(
            attrs={
                "step": "0.01",
                "min": "0.00",
                "inputmode": "decimal",
            }
        ),
    )
    sort = forms.ChoiceField(
        required=False,
        label="Sort by",
        choices=Sort.choices,
        initial=Sort.NEWEST,
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(user=user)
        self.apply_bootstrap_classes()
        self.order_fields(
            [
                "q",
                "type",
                "category",
                "date_from",
                "date_to",
                "amount_min",
                "amount_max",
                "sort",
            ]
        )

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get("date_from")
        date_to = cleaned_data.get("date_to")
        amount_min = cleaned_data.get("amount_min")
        amount_max = cleaned_data.get("amount_max")

        if date_from and date_to and date_from > date_to:
            self.add_error(
                "date_to",
                "End date must be on or after the start date.",
            )

        if (
            amount_min is not None
            and amount_max is not None
            and amount_min > amount_max
        ):
            self.add_error(
                "amount_max",
                "Maximum amount must be on or after the minimum amount.",
            )

        return cleaned_data
