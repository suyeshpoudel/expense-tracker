from django import forms
from django.utils import timezone

from apps.common.forms import BootstrapFormMixin

from .models import Transaction


class TransactionForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ("transaction_type", "amount", "title", "date", "notes")
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()
        self.fields["title"].widget.attrs["autofocus"] = True
        self.fields["date"].widget.attrs["max"] = timezone.localdate().isoformat()

        if not self.is_bound and not self.instance.pk:
            self.initial.setdefault("date", timezone.localdate())

    def clean_date(self):
        value = self.cleaned_data["date"]
        if value and value > timezone.localdate():
            raise forms.ValidationError(
                "Transaction date cannot be in the future."
            )
        return value


class TransactionFilterForm(BootstrapFormMixin, forms.Form):
    type = forms.ChoiceField(
        required=False,
        label="Type",
        choices=[("", "All types"), *Transaction.Type.choices],
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
