from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.timezone import now

from books.models import Book


class Borrowing(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="borrowings",
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name="borrowings",
    )

    borrow_date = models.DateField(auto_now_add=True)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-borrow_date", "-id"]

    def clean(self):
        borrow_date = self.borrow_date or now().date()

        if self.expected_return_date < borrow_date:
            raise ValidationError(
                "Expected return date cannot be earlier than borrow date."
            )

        if self.actual_return_date and self.actual_return_date < borrow_date:
            raise ValidationError(
                "Actual return date cannot be earlier than borrow date."
            )

    @property
    def is_active(self):
        return self.actual_return_date is None

    def __str__(self):
        return f"{self.user} borrowed {self.book}"