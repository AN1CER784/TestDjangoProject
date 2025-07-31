from dataclasses import dataclass
from typing import Literal, Optional, TypedDict, List

import stripe
from django.http import JsonResponse, HttpResponse

from TestDjangoProject.settings import STRIPE_SECRET_KEY
from goods.models import Order
from goods.utils import convert_price


class ProductData(TypedDict):
    """Информация о товаре"""
    name: str
    description: str


class PriceData(TypedDict):
    """Цена, валютные данные и данные товара для Stripe"""
    currency: str
    product_data: ProductData
    unit_amount: int


class LineItem(TypedDict):
    """Структура позиции для Stripe Checkout"""
    price_data: PriceData
    quantity: int
    tax_rates: list[str]


@dataclass
class StripeEntity:
    """Структура для ресурса в Stripe """
    stripe_id: str


class SessionParams(TypedDict):
    """Структура параметров сессии"""
    line_items: list[LineItem]
    mode: Literal["payment"]
    success_url: str
    cancel_url: str
    metadata: dict[Literal["order_id"], int]
    discounts: Optional[list[dict[str, str]]]


class StripeService:
    """Сервис для взаимодействия со Stripe"""

    def __init__(self, order: Order):
        self.order = order
        self._items = list(order.items.all())
        stripe.api_key = STRIPE_SECRET_KEY

    def _get_discount(self) -> Optional[StripeEntity]:
        """Возвращает Discount объект для Stripe, если скидка есть."""
        if self.order.discount and self.order.discount.stripe_id:
            return StripeEntity(self.order.discount.stripe_id)
        return None

    def _get_tax(self) -> Optional[StripeEntity]:
        """Возвращает Tax объект для Stripe, если он есть."""
        if self.order.tax and self.order.tax.stripe_id:
            return StripeEntity(self.order.tax.stripe_id)
        return None

    def _create_line_items(self) -> List[LineItem]:
        """Создание списка позиций для Stripe Session Checkout"""
        tax = self._get_tax()
        items: List[LineItem] = []
        for item in self._items:
            li: LineItem = {
                "price_data": {
                    "currency": self.order.currency,
                    "product_data": {"name": item.name, "description": item.description},
                    "unit_amount": convert_price(item.price),
                },
                "quantity": 1,
            }
            if tax:
                li["tax_rates"] = [tax.stripe_id]
            items.append(li)
        return items

    def _build_session_params(self, success_url: str, cancel_url: str, line_items: List[LineItem]) -> SessionParams:
        """Создает параметры для Stripe Checkout Session."""
        params: SessionParams = {
            "line_items": line_items,
            "mode": "payment",
            "success_url": f"{success_url}",
            "cancel_url": f"{cancel_url}",
            "metadata": {"order_id": self.order.id},
            "discounts": None,
        }
        discount = self._get_discount()
        if discount:
            params["discounts"] = [{"coupon": discount.stripe_id}]
        return params

    def create_checkout_session(self, success_url: str, cancel_url: str) -> str:
        """Создает Stripe Checkout Session и возвращает его session_id."""
        params = self._build_session_params(success_url, cancel_url, self._create_line_items())
        session = stripe.checkout.Session.create(**params)
        return session.id

    def _calculate_total(self) -> int:
        """Считает итоговую сумму заказа с учётом купона и налога. Возвращает сумму в центах."""
        total = sum(item.price for item in self._items)
        total_cents = convert_price(total)

        discount = self._get_discount()
        if discount:
            coupon = stripe.Coupon.retrieve(discount.stripe_id)
            if coupon.percent_off:
                total_cents -= int(total_cents * coupon.percent_off / 100)

        tax = self._get_tax()
        if tax:
            tax_rate = stripe.TaxRate.retrieve(tax.stripe_id)
            if tax_rate.percentage:
                total_cents += int(total_cents * tax_rate.percentage / 100)

        return total_cents

    def create_payment_intent(self) -> str:
        """Создает Stripe Payment Intent и возвращает его client_secret."""
        amount = self._calculate_total()
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency=self.order.currency,
            metadata={"order_id": self.order.id},
        )
        return intent.client_secret


class WebHookStripeService:
    @classmethod
    def set_order_from_web_hook(cls, obj_data_from_webhook: dict) -> Order:
        """Находит заказ по order_id из webhook и ставит статус InProgress."""
        order_id = obj_data_from_webhook['metadata'].get('order_id')
        order = Order.objects.filter(id=order_id).first()
        if order:
            order.status = "InProgress"
            order.save(update_fields=["status"])
            return order

    @classmethod
    def get_webhook_response(cls, payload, sig_header, endpoint_secret) -> JsonResponse | HttpResponse:
        """Обрабатывает Stripe webhook, проверяет подпись и обновляет заказ."""
        try:
            event = stripe.Webhook.construct_event(
                payload=payload, sig_header=sig_header, secret=endpoint_secret
            )
        except ValueError:
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError:
            return HttpResponse(status=400)

        if event['type'] == 'checkout.session.completed' or event["type"] == "payment_intent.succeeded":
            obj_data_from_webhook = event['data']['object']
            order = cls.set_order_from_web_hook(obj_data_from_webhook)
            if not order:
                return JsonResponse({"error": "Order not found"}, status=404)
        return HttpResponse(status=200)

