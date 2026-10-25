from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.categories.services import seed_default_categories
from apps.common.forms import changed_field_labels

from .forms import (
    LoginForm,
    ProfileForm,
    ProfilePasswordChangeForm,
    RegistrationForm,
)


class AppLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"Welcome back, {form.get_user().get_username()}.",
        )
        return response

    def form_invalid(self, form):
        messages.error(
            self.request,
            "Log in failed. Check your username and password.",
        )
        return super().form_invalid(form)


def register(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save()
                seed_default_categories(user)
            login(request, user)
            messages.success(
                request,
                f'Account "{user.get_username()}" was created successfully.',
            )
            return redirect("core:dashboard")
        messages.error(
            request,
            "Account was not created. Please fix the highlighted fields.",
        )
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile(request):
    profile_form = ProfileForm(instance=request.user)
    password_form = ProfilePasswordChangeForm(request.user)

    if request.method == "POST":
        if request.POST.get("form") == "profile":
            profile_form = ProfileForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                changed_labels = changed_field_labels(profile_form)
                profile_form.save()
                if changed_labels:
                    messages.success(
                        request,
                        "Profile updated: "
                        + ", ".join(changed_labels)
                        + ".",
                    )
                else:
                    messages.info(
                        request,
                        "Profile saved. No changes were detected.",
                    )
                return redirect("accounts:profile")
            messages.error(
                request,
                "Profile was not updated. Please fix the highlighted fields.",
            )
        elif request.POST.get("form") == "password":
            password_form = ProfilePasswordChangeForm(
                request.user,
                request.POST,
            )
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, request.user)
                messages.success(
                    request,
                    "Your password was changed successfully.",
                )
                return redirect("accounts:profile")
            messages.error(
                request,
                "Password was not changed. Please fix the highlighted fields.",
            )

    context = {
        "profile_form": profile_form,
        "password_form": password_form,
        "transaction_count": request.user.transactions.count(),
        "category_count": request.user.categories.count(),
        "budget_count": request.user.budgets.count(),
    }
    return render(request, "accounts/profile.html", context)


@require_POST
def logout_view(request):
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, "You have been logged out.")
    return redirect("core:home")
