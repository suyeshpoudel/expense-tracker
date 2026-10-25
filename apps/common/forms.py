from django import forms


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
