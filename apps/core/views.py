from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone


def home(request):
    return render(request, "core/home.html")


@login_required
def dashboard(request):
    return render(
        request,
        "core/dashboard.html",
        {"month_label": timezone.localdate().strftime("%B %Y")},
    )
