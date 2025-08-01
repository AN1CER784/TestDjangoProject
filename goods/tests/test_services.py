import json
from decimal import Decimal
from unittest.mock import patch, MagicMock

import stripe
from django.http import HttpResponse, JsonResponse
from django.test import TestCase, override_settings

from goods.models import Item, Discount, Tax
from goods.models import Order
from goods.services.db_service import create_or_get_order, get_order_by_user_data
from goods.services.stripe_service import StripeService, StripeEntity
from goods.services.stripe_service import WebHookStripeService
from goods.utils import convert_price


class StripeServiceLineItemsTest(TestCase):
    def setUp(self):
        self.item1 = Item.objects.create(
            name="First", description="Desc1", price=Decimal("10.00"), currency="usd"
        )
        self.item2 = Item.objects.create(
            name="Second", description="Desc2", price=Decimal("20.50"), currency="usd"
        )
        self.order = Order.objects.create(currency="usd")
        self.order.items.set([self.item1, self.item2])
        self.stripe_service = StripeService(order=self.order)

    def test_create_line_items_without_tax(self):
        line_items = self.stripe_service._create_line_items()
        # должно быть по одному элементу на каждый товар
        self.assertEqual(len(line_items), 2)
        expected_amounts = [convert_price(self.item1.price), convert_price(self.item2.price)]
        for li, expected in zip(line_items, expected_amounts):
            self.assertEqual(li["quantity"], 1)
            self.assertEqual(li["price_data"]["currency"], "usd")
            self.assertEqual(li["price_data"]["unit_amount"], expected)
            self.assertEqual(li["price_data"]["product_data"]["name"], li["price_data"]["product_data"]["name"])
            self.assertNotIn("tax_rates", li)

    def test_create_line_items_with_tax(self):
        # добавляем налог в заказ
        tax = Tax.objects.create(name="VAT", percentage=15)
        self.order.tax = tax
        self.order.save()
        # моким stripe.TaxRate.retrieve, чтобы у tax_rate.percentage был 15
        with patch("goods.services.stripe_service.StripeService._get_tax",
                   return_value=StripeEntity(stripe_id="txr_123")):
            line_items = self.stripe_service._create_line_items()
            for li in line_items:
                self.assertIn("tax_rates", li)
                self.assertEqual(li["tax_rates"], ["txr_123"])


class StripeServiceTaxDiscountTest(TestCase):
    def setUp(self):
        self.item = Item.objects.create(
            name="Solo", description="Desc", price=Decimal("5.00"), currency="rub"
        )
        self.order = Order.objects.create(currency="rub")
        self.order.items.add(self.item)
        self.stripe_service = StripeService(order=self.order)

    def test_get_tax_none(self):
        self.assertIsNone(self.stripe_service._get_tax())

    def test_get_tax_present(self):
        tax = Tax.objects.create(name="Fee", percentage=10)
        self.order.tax = tax
        self.order.save()
        result = self.stripe_service._get_tax()
        self.assertIsInstance(result, StripeEntity)
        self.assertEqual(result.stripe_id, tax.stripe_id)

    def test_get_discount_none(self):
        self.assertIsNone(self.stripe_service._get_discount())

    def test_get_discount_present(self):
        disc = Discount.objects.create(name="Sale", percentage=20)
        self.order.discount = disc
        self.order.save()
        result = self.stripe_service._get_discount()
        self.assertIsInstance(result, StripeEntity)
        self.assertEqual(result.stripe_id, disc.stripe_id)


class StripeServiceSessionParamsTest(TestCase):
    def setUp(self):
        self.line_items = [{"price_data": {}, "quantity": 1}]

    def test_get_session_params_no_discount(self):
        self.item = Item.objects.create(name="X", description="Y", price=Decimal("2.00"), currency="usd")
        self.order = Order.objects.create(currency="usd")
        self.order.items.add(self.item)
        self.stripe_service = StripeService(order=self.order)
        params = self.stripe_service._build_session_params(line_items=self.line_items,
                                                           cancel_url="http://localhost/cancel",
                                                           success_url="http://localhost/success")
        self.assertEqual(params["line_items"], self.line_items)
        self.assertEqual(params["mode"], "payment")
        self.assertIn("success_url", params)
        self.assertIn("cancel_url", params)
        self.assertEqual(params["discounts"], None)

    def test_get_session_params_with_discount(self):
        self.order = MagicMock()
        self.stripe_service = StripeService(order=self.order)
        fake_disc = StripeEntity(stripe_id="coupon_xyz")
        self.order.discount = fake_disc
        params = self.stripe_service._build_session_params(line_items=self.line_items,
                                                           cancel_url="http://localhost/cancel",
                                                           success_url="http://localhost/success")
        self.assertIn("discounts", params)
        self.assertEqual(params["discounts"], [{"coupon": "coupon_xyz"}])


class StripeServiceCreateSessionTest(TestCase):
    def setUp(self):
        self.item = Item.objects.create(name="X", description="Y", price=Decimal("2.00"), currency="usd")
        self.order = Order.objects.create(currency="usd")
        self.order.items.add(self.item)
        self.stripe_service = StripeService(order=self.order)

    @patch("stripe.checkout.Session.create")
    def test_create_stripe_session_calls_api(self, mock_create):
        mock_create.return_value = MagicMock(id="sess_abc123")
        session_id = self.stripe_service.create_checkout_session(cancel_url="http://localhost/cancel",
                                                                 success_url="http://localhost/success")
        mock_create.assert_called_once()
        self.assertEqual(session_id, "sess_abc123")


class StripeServiceCalculateTotalTest(TestCase):
    def setUp(self):
        self.i1 = Item.objects.create(name="A", description="A", price=Decimal("10.00"), currency="usd")
        self.order = Order.objects.create(currency="usd")
        self.order.items.add(self.i1)
        self.stripe_service = StripeService(order=self.order)

    @patch("stripe.Coupon.retrieve")
    @patch("stripe.TaxRate.retrieve")
    def test_calculate_total_with_discount_and_tax(self, mock_taxrate, mock_coupon):
        # устанавливаем поведение моков
        mock_coupon.return_value = MagicMock(percent_off=10)
        mock_taxrate.return_value = MagicMock(percentage=5)
        # создаём скидку и налог в модели, чтобы order.discount и order.tax не были None
        disc = Discount.objects.create(name="Test", percentage=10)
        tax = Tax.objects.create(name="Fee", percentage=5)
        self.order.discount = disc
        self.order.tax = tax
        self.order.save()

        total_cents = self.stripe_service._calculate_total()
        # расчёт: базово 10 USD → 1000 центов
        # coupon.percent_off = 900 центов → 1000-100=900
        # tax 5% на 900 → 900+45 = 945
        self.assertEqual(total_cents, 945)

    @patch("stripe.Coupon.retrieve", side_effect=Exception("no coupon"))
    @patch("stripe.TaxRate.retrieve", side_effect=Exception("no tax"))
    def test_calculate_total_without_discount_and_tax(self, *_):
        total_cents = self.stripe_service._calculate_total()
        self.assertEqual(total_cents, convert_price(self.i1.price))


class StripeServicePaymentIntentTest(TestCase):
    def setUp(self):
        self.i1 = Item.objects.create(name="Solo", description="Single", price=Decimal("3.50"), currency="usd")
        self.order = Order.objects.create(currency="usd")
        self.order.items.add(self.i1)
        self.stripe_service = StripeService(order=self.order)

    @patch("stripe.PaymentIntent.create")
    def test_create_payment_intent(self, mock_create_intent):
        mock_intent = MagicMock(client_secret="secret_123")
        mock_create_intent.return_value = mock_intent

        client_secret = self.stripe_service.create_payment_intent()
        mock_create_intent.assert_called_once_with(
            amount=convert_price(self.i1.price),
            currency="usd",
            metadata={"order_id": self.order.id},
        )
        self.assertEqual(client_secret, "secret_123")


class CreateOrderTests(TestCase):
    def setUp(self):
        self.item1 = Item.objects.create(name="Book", price=1000, description="Test Book")
        self.item2 = Item.objects.create(name="Pen", price=200, description="Blue pen")
        self.discount = Discount.objects.create(percentage=10, name="10% DISCOUNT")
        self.tax = Tax.objects.create(percentage=10, name="10% TAX")
        self.session_key = "session_123"

    def test_get_order_by_user_data_no_existing(self):
        result = get_order_by_user_data(
            items=[self.item1, self.item2],
            session_key=self.session_key,
        )
        self.assertIsNone(result)

    def test_get_order_by_user_data_match_exact(self):
        order = Order.objects.create(
            session_key=self.session_key,
            discount=self.discount,
            tax=self.tax,
            status="Created",
        )
        order.items.set([self.item1, self.item2])

        found = get_order_by_user_data(
            items=[self.item1, self.item2],
            session_key=self.session_key,
            discount=self.discount,
            tax=self.tax,
        )
        self.assertIsNotNone(found)
        self.assertEqual(found.pk, order.pk)

    def test_create_order_with_items_only(self):
        order = create_or_get_order(items=[self.item1, self.item2], session_key=self.session_key)

        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(order.items.count(), 2)
        self.assertIsNone(order.discount)
        self.assertIsNone(order.tax)

    def test_create_order_with_discount_and_tax(self):
        order = create_or_get_order(items=[self.item1], discount=self.discount, tax=self.tax,
                                    session_key=self.session_key)
        self.assertEqual(order.discount, self.discount)
        self.assertEqual(order.tax, self.tax)
        self.assertEqual(order.items.count(), 1)
        self.assertIn(self.item1, order.items.all())

    def test_order_relations_are_prefetched(self):
        order = create_or_get_order(items=[self.item1], discount=self.discount, tax=self.tax,
                                    session_key="Test session key")
        with self.assertNumQueries(0):
            _ = order.discount
            _ = order.tax
            list(order.items.all())


@override_settings(STRIPE_WEBHOOK_SECRET="whsec_testsecret")
class WebHookStripeServiceTests(TestCase):
    def setUp(self):
        self.order = Order.objects.create(status="Created")
        self.good_payload = json.dumps({
            "type": "checkout.session.completed",
            "data": {"object": {"metadata": {"order_id": str(self.order.id)}}}
        }).encode()
        self.sig_header = "t=123,v1=signature"

    @patch("stripe.Webhook.construct_event")
    def test_get_webhook_response_invalid_json(self, mock_construct):
        mock_construct.side_effect = ValueError()
        resp = WebHookStripeService.get_webhook_response(
            payload=b"not a json", sig_header=self.sig_header, endpoint_secret="whsec_test"
        )
        self.assertIsInstance(resp, HttpResponse)
        self.assertEqual(resp.status_code, 400)

    @patch("stripe.Webhook.construct_event")
    def test_get_webhook_response_invalid_signature(self, mock_construct):
        mock_construct.side_effect = stripe.error.SignatureVerificationError(
            message="sig fail", sig_header=self.sig_header
        )
        resp = WebHookStripeService.get_webhook_response(
            payload=self.good_payload, sig_header=self.sig_header, endpoint_secret="whsec_test"
        )
        self.assertIsInstance(resp, HttpResponse)
        self.assertEqual(resp.status_code, 400)

    @patch("stripe.Webhook.construct_event")
    def test_get_webhook_response_success_updates_order(self, mock_construct):
        mock_construct.return_value = json.loads(self.good_payload)
        resp = WebHookStripeService.get_webhook_response(
            payload=self.good_payload, sig_header=self.sig_header, endpoint_secret="whsec_testsecret"
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "InProgress")
        self.assertIsInstance(resp, HttpResponse)
        self.assertEqual(resp.status_code, 200)

    @patch("stripe.Webhook.construct_event")
    def test_get_webhook_response_order_not_found(self, mock_construct):
        payload = json.dumps({
            "type": "payment_intent.succeeded",
            "data": {"object": {"metadata": {"order_id": "9999"}}}
        }).encode()
        mock_construct.return_value = json.loads(payload)
        resp = WebHookStripeService.get_webhook_response(
            payload=payload, sig_header=self.sig_header, endpoint_secret="whsec_testsecret"
        )
        self.assertIsInstance(resp, JsonResponse)
        self.assertEqual(resp.status_code, 404)
        self.assertJSONEqual(resp.content, {"error": "Order not found"})

    @patch("stripe.Webhook.construct_event")
    def test_set_order_from_web_hook_returns_order(self, mock_construct):
        obj = {"metadata": {"order_id": str(self.order.id)}}
        updated = WebHookStripeService.set_order_from_web_hook(obj)
        self.assertIsNotNone(updated)
        self.assertEqual(updated.id, self.order.id)
        self.assertEqual(updated.status, "InProgress")

    def test_set_order_from_web_hook_none_if_missing(self):
        obj = {"metadata": {}}
        updated = WebHookStripeService.set_order_from_web_hook(obj)
        self.assertIsNone(updated)
