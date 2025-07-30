import json

from django.test import TestCase
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

