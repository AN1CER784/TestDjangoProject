from django.http import JsonResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import DetailView, TemplateView

from TestDjangoProject import settings
from goods.mixins import DataMixin, CacheByIPMixin
from goods.models import Discount, Tax
from goods.services.db_service import create_or_get_order
from goods.services.stripe_service import StripeService, WebHookStripeService
from goods.utils import get_by_pk


class ItemView(DataMixin, DetailView):
    template_name = 'item.html'
    context_object_name = "item"

    def get_object(self, queryset=None):
        item = self.get_item(pk=int(self.kwargs.get("id")))
        return item

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_context = self.get_user_context(title="Страница товара", stripe_public_key=True,
                                             item_buy_url=self.request.build_absolute_uri(
                                                 reverse('goods:item_buy', kwargs={"id": self.object.pk})),
                                             complete_url=self.request.build_absolute_uri(
                                                 reverse('goods:complete_page')))
        return context | user_context


class ItemBuyView(CacheByIPMixin, DataMixin, View):
    """Обработка покупки при помощи StripeService; получает id возвращает либо сlientSecret либо sessionId"""

    def get(self, request, id):

        session_key = self.get_session(request)

        cached_response = self.get_cached_response(session_key, id)
        if cached_response:
            return JsonResponse(cached_response)

        # TODO: В продакшене тут логика получения скидки (из корзины/по купону и др.) и доп сбора (по типу товара, фиксированный и др.), для теста берем первую скидку и доп сбор по pk=1.
        item = self.get_item(pk=id)
        discount = get_by_pk(Discount, pk=1)
        tax = get_by_pk(Tax, pk=1)

        # TODO: В продакшене тут логика составления заказа, например, по корзине с последующей привязкой по пользователю, для теста берем тот item, по которому поступил get запрос.
        order = create_or_get_order(items=[item], session_key=session_key, discount=discount, tax=tax)

        stripe_service = StripeService(order=order)

        # Реализация со stripe session
        # session_id = stripe_service.create_checkout_session(
        #     success_url=request.build_absolute_uri(reverse('goods:success_page')),
        #     cancel_url=request.build_absolute_uri(reverse('goods:cancel_page')))
        # response_data = {"sessionId": session_id}

        # Реализация со stripe payment intent
        client_secret = stripe_service.create_payment_intent()
        response_data = {"clientSecret": client_secret}
        self.set_cached_response(session_key, id, response_data, 60)
        return JsonResponse(response_data)


class CompleteView(DataMixin, TemplateView):
    template_name = "complete.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_context = self.get_user_context(title="Оплата завершена", stripe_public_key=True)
        return context | user_context


class SuccessView(DataMixin, TemplateView):
    template_name = "success.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_context = self.get_user_context(title="Спасибо за заказ")
        return context | user_context


class CancelView(DataMixin, TemplateView):
    template_name = "cancel.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_context = self.get_user_context(title="Покупка была отменена")
        return context | user_context


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(View):
    """
    Обработка Stripe вебхуков.
    """

    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
        result = WebHookStripeService().get_webhook_response(payload, sig_header, endpoint_secret)
        return result
