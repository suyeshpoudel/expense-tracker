from django import forms
from django.db import models


class BootstrapFormMixin:
    """Apply Bootstrap classes to form widgets."""

    def apply_bootstrap_classes(self):
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                css_class = "form-check-input"
            elif isinstance(widget, forms.Select):
                css_class = "form-select"
            else:
                css_class = "form-control"

            existing = widget.attrs.get("class", "")
            widget.attrs["class"] = f"{existing} {css_class}".strip()


def _comparable(value):
    if isinstance(value, models.Model):
        return value.pk
    return value


def changed_field_labels(form):
    """Return labels for fields whose submitted value differs from initial."""
    labels = []
    for name in form.changed_data:
        value = form.cleaned_data.get(name)
        initial = form.initial.get(name, form.fields[name].initial)
        if _comparable(value) == _comparable(initial):
            continue
        labels.append(str(form.fields[name].label))
    return labels
