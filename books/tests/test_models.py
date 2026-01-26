from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from books.models import Book


class BookModelTests(TestCase):

    def test_create_book_with_valid_data(self):
        book = Book.objects.create(
            title="Clean Code",
            author="Robert C. Martin",
            cover=Book.CoverType.SOFT,
            inventory=10,
            daily_fee=Decimal("2.50"),
        )

        self.assertEqual(book.title, "Clean Code")
        self.assertEqual(book.author, "Robert C. Martin")
        self.assertEqual(book.cover, Book.CoverType.SOFT)
        self.assertEqual(book.inventory, 10)
        self.assertEqual(book.daily_fee, Decimal("2.50"))

    def test_book_str_representation(self):
        book = Book.objects.create(
            title="Domain-Driven Design",
            author="Eric Evans",
            cover=Book.CoverType.HARD,
            inventory=3,
            daily_fee=Decimal("5.00"),
        )

        self.assertEqual(
            str(book),
            "Domain-Driven Design by Eric Evans"
        )

    def test_inventory_cannot_be_negative(self):
        book = Book(
            title="Invalid Book",
            author="Author",
            cover=Book.CoverType.SOFT,
            inventory=-1,
            daily_fee=Decimal("1.00"),
        )

        with self.assertRaises(ValidationError):
            book.full_clean()

    def test_daily_fee_cannot_be_negative(self):
        book = Book(
            title="Free Book",
            author="Author",
            cover=Book.CoverType.SOFT,
            inventory=1,
            daily_fee=Decimal("-0.01"),
        )

        with self.assertRaises(ValidationError):
            book.full_clean()

    def test_inventory_can_be_zero(self):
        book = Book.objects.create(
            title="Out of Stock",
            author="Author",
            cover=Book.CoverType.SOFT,
            inventory=0,
            daily_fee=Decimal("1.00"),
        )

        self.assertEqual(book.inventory, 0)

    def test_daily_fee_can_be_zero(self):
        book = Book.objects.create(
            title="Promotional Book",
            author="Author",
            cover=Book.CoverType.SOFT,
            inventory=1,
            daily_fee=Decimal("0.00"),
        )

        self.assertEqual(book.daily_fee, Decimal("0.00"))

    def test_cover_type_choices(self):
        book = Book.objects.create(
            title="Hardcover Book",
            author="Author",
            cover=Book.CoverType.HARD,
            inventory=2,
            daily_fee=Decimal("3.00"),
        )

        self.assertEqual(book.cover, Book.CoverType.HARD)
        self.assertIn(
            book.cover,
            Book.CoverType.values
        )