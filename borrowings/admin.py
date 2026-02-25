from django.contrib import admin
from .models import Borrowing


@admin.register(Borrowing)
class BorrowingAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "book",
        "borrow_date",
        "expected_return_date",
        "actual_return_date",
        "is_active",
    )
    list_filter = ("borrow_date", "expected_return_date")
    search_fields = ("user__email", "book__title")
