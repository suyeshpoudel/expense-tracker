from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from apps.common.forms import BootstrapFormMixin


class RegistrationForm(BootstrapFormMixin, UserCreationForm):
    email = forms.EmailField(
        required=False,
        help_text="Optional.",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()
        self.fields["username"].widget.attrs["autofocus"] = True
        self.fields["username"].widget.attrs["autocomplete"] = "username"
        self.fields["email"].widget.attrs["autocomplete"] = "email"

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()
        self.fields["username"].widget.attrs["autofocus"] = True
        self.fields["username"].widget.attrs["autocomplete"] = "username"
        self.fields["password"].widget.attrs["autocomplete"] = "current-password"
