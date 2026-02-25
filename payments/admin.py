from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "borrowing",
        "type",
        "status",
        "money_to_pay",
        "created_at",
    )
    list_filter = ("status", "type")
    search_fields = ("borrowing__user__email",)
