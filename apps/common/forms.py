from django import forms
from django.db import models


class BootstrapFormMixin:
    """Apply the project's form control classes to widgets."""

    def apply_bootstrap_classes(self):
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                css_class = "field-checkbox"
            elif isinstance(widget, forms.Select):
                css_class = "field-select"
            elif isinstance(widget, forms.Textarea):
                css_class = "field-textarea"
            else:
                css_class = "field-input"

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
