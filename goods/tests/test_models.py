from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from goods.models import Item, Order, Discount, Tax


class ItemModelTest(TestCase):
    def test_create_and_str_fields(self):
        item = Item.objects.create(
            name="Test Product",
            description="Just a test",
            price=Decimal("9.99"),
            currency="rub"
        )
        self.assertEqual(len(Item.objects.all()), 1)
        self.assertEqual(item.name, "Test Product")
        self.assertEqual(item.description, "Just a test")
        self.assertEqual(item.price, Decimal("9.99"))
        self.assertEqual(item.currency, "rub")

    def test_price_cannot_be_negative(self):
        item = Item(
            name="Bad",
            description="Neg price",
            price=Decimal("-1.00"),
            currency="usd"
        )
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_currency_choices_validation(self):
        item = Item(
            name="BadCurrency",
            description="Wrong currency",
            price=Decimal("1.00"),
            currency="eur"
        )
        with self.assertRaises(ValidationError):
            item.full_clean()


class OrderModelTest(TestCase):
    def setUp(self):
        self.i1 = Item.objects.create(
            name="A", description="A", price=Decimal("1.00"), currency="usd"
        )
        self.i2 = Item.objects.create(
            name="B", description="B", price=Decimal("2.00"), currency="usd"
        )

    def test_create_order_and_add_items(self):
        order = Order.objects.create()
        self.assertEqual(order.currency, "usd")

        order.items.set([self.i1, self.i2])
        self.assertEqual(
            list(order.items.all()),
            list(Item.objects.all())
        )


class DiscountModelTest(TestCase):
    @patch("goods.models.stripe.Coupon.create")
    def test_save_creates_coupon_and_saves_id(self, mock_coupon_create):
        mock_coupon_create.return_value = type("C", (), {"id": "coupon_12345"})()
        disc = Discount(name="TestSale", percentage=15)
        disc.full_clean()
        disc.save()
        self.assertEqual(disc.stripe_coupon_id, "coupon_12345")
        mock_coupon_create.assert_called_once_with(
            percent_off=15,
            duration="forever",
            name="TestSale"
        )

    def test_save_without_percentage_raises(self):
        disc = Discount(name="NoPercent", percentage=None)
        with self.assertRaises(ValidationError):
            disc.save()


class TaxModelTest(TestCase):
    @patch("goods.models.stripe.TaxRate.create")
    def test_save_creates_taxrate_and_saves_id(self, mock_taxrate_create):
        mock_taxrate_create.return_value = type("T", (), {"id": "txr_67890"})()

        tax = Tax(name="VAT", percentage=20)
        tax.full_clean()
        tax.save()
        self.assertEqual(tax.stripe_tax_rate_id, "txr_67890")
        mock_taxrate_create.assert_called_once_with(
            display_name="VAT",
            inclusive=False,
            percentage=20
        )

    def test_percentage_validator(self):
        with self.assertRaises(ValidationError):
            t = Tax(name="TooMuch", percentage=150)
            t.full_clean()
