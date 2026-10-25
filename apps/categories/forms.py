from django import forms

from apps.common.forms import BootstrapFormMixin

from .models import Category


class CategoryChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.name} ({obj.get_category_type_display()})"


class CategoryForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ("category_type", "name")

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()
        self.fields["name"].widget.attrs["autofocus"] = True

        if self.instance.pk:
            self.fields["category_type"].disabled = True
            self.fields["category_type"].help_text = (
                "The category type cannot be changed after creation."
            )

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        category_type = self.cleaned_data.get("category_type")
        if not category_type:
            category_type = self.instance.category_type

        duplicates = Category.objects.filter(
            user=self.user,
            category_type=category_type,
            name__iexact=name,
        )
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)

        if duplicates.exists():
            raise forms.ValidationError(
                "You already have a category with this name."
            )

        return name
