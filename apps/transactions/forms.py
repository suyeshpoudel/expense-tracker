from django import forms
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

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(user=user)
        self.apply_bootstrap_classes()

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get("date_from")
        date_to = cleaned_data.get("date_to")

        if date_from and date_to and date_from > date_to:
            self.add_error(
                "date_to",
                "End date must be on or after the start date.",
            )

        return cleaned_data
