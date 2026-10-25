from django.contrib import admin

from .models import MonthlyBudget


@admin.register(MonthlyBudget)
class MonthlyBudgetAdmin(admin.ModelAdmin):
    list_display = ("month", "amount", "user")
    list_filter = ("month",)
    search_fields = ("user__username",)
    list_select_related = ("user",)
    date_hierarchy = "month"
