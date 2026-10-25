from django.contrib import admin

from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "user",
        "transaction_type",
        "category",
        "amount",
        "title",
    )
    list_filter = ("transaction_type", "category", "date")
    search_fields = ("title", "notes", "user__username", "category__name")
    date_hierarchy = "date"
    list_select_related = ("user", "category")
