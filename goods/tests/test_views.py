import json
from unittest.mock import patch

from django.http import HttpResponse, JsonResponse
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from goods.models import Item


class ItemViewTestCase(TestCase):
    def setUp(self):
        self.item = Item.objects.create(
            name="Test Item",
            description="Test Description",
            price=100,
            currency="rub"
        )

    def test_valid_item(self):
        response = self.client.get(reverse("goods:item_lookout", kwargs={"id": self.item.id}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "item.html")
        self.assertContains(response, self.item.name)
        self.assertContains(response, self.item.description)
        self.assertContains(response, self.item.price)
        self.assertContains(response, "₽")

    def test_invalid_item(self):
        response = self.client.get(reverse("goods:item_lookout", kwargs={"id": self.item.id + 213}))
        self.assertEqual(response.status_code, 404)


class ItemBuyViewTestCase(TestCase):
    def setUp(self):
        self.item = Item.objects.create(
            name="Test Item",
            description="Test Description",
            price=100,
            currency="rub"
        )

    def test_valid_item(self):
        response = self.client.get(reverse("goods:item_buy", kwargs={"id": self.item.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "clientSecret")
        data = json.loads(response.content)
        self.assertTrue(
            data['clientSecret'].startswith('pi_'),
        )

    def test_invalid_item(self):
        response = self.client.get(reverse("goods:item_buy", kwargs={"id": self.item.id + 213}))
        self.assertEqual(response.status_code, 404)


@override_settings(STRIPE_WEBHOOK_SECRET="whsec_testsecret")
class StripeWebhookViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("goods:stripe_webhook")
        self.payload = json.dumps({"test": "data"}).encode()
        self.sig_header = "t=123,v1=signature"

    @patch("goods.views.WebHookStripeService.get_webhook_response")
    def test_webhook_view_returns_service_response(self, mock_service):
        mock_resp = HttpResponse(status=200)
        mock_service.return_value = mock_resp

        resp = self.client.post(
            self.url,
            data=self.payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=self.sig_header
        )

        mock_service.assert_called_once()
        args, kwargs = mock_service.call_args
        self.assertEqual(args[0], self.payload)
        self.assertEqual(args[1], self.sig_header)
        self.assertEqual(resp.status_code, 200)

    @patch("goods.views.WebHookStripeService.get_webhook_response")
    def test_webhook_view_no_signature_header(self, mock_service):
        mock_service.return_value = HttpResponse(status=400)

        resp = self.client.post(
            self.url,
            data=self.payload,
            content_type="application/json"
        )

        args, kwargs = mock_service.call_args
        self.assertIsNone(args[1])
        self.assertEqual(resp.status_code, 400)
