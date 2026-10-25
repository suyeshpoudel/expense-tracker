from django import forms
from django.utils import timezone

from apps.common.forms import BootstrapFormMixin

from .models import MonthlyBudget


class MonthlyBudgetForm(BootstrapFormMixin, forms.ModelForm):
    month = forms.DateField(
        label="Month",
        input_formats=["%Y-%m"],
        widget=forms.DateInput(
            format="%Y-%m",
            attrs={"type": "month"},
        ),
    )

    class Meta:
        model = MonthlyBudget
        fields = ("month", "amount")
        widgets = {
            "amount": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0.01",
                    "inputmode": "decimal",
                }
            ),
        }

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()
        self.fields["month"].widget.attrs["autofocus"] = True
        self.fields["month"].help_text = (
            "Choose the calendar month this budget applies to."
        )
        self.fields["amount"].help_text = (
            "Expenses in that month count against this budget."
        )

        if not self.is_bound and not self.instance.pk:
            self.initial.setdefault(
                "month",
                timezone.localdate().replace(day=1),
            )

    def clean_month(self):
        month = self.cleaned_data["month"]
        if month.day != 1:
            raise forms.ValidationError("Choose a month, not a specific date.")
        return month

    def clean(self):
        cleaned_data = super().clean()
        month = cleaned_data.get("month")

        if month:
            duplicates = MonthlyBudget.objects.filter(
                user=self.user,
                month=month,
            )
            if self.instance.pk:
                duplicates = duplicates.exclude(pk=self.instance.pk)

            if duplicates.exists():
                self.add_error(
                    "month",
                    "A budget already exists for this month. Edit that budget instead.",
                )

        return cleaned_data
