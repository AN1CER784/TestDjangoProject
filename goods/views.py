from django.http import JsonResponse
from django.views import View
from django.views.generic import DetailView, TemplateView

from goods.mixins import DataMixin
from goods.models import Discount, Tax
from goods.utils import get_by_pk
from goods.services.stripe_service import StripeService
from goods.services.db_service import create_order


class ItemView(DataMixin, DetailView):
    template_name = 'item.html'
    context_object_name = "item"

    def get_object(self, queryset=None):
        item = self.get_item(pk=int(self.kwargs.get("id")))
        return item

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_context = self.get_user_context(title="Страница товара", host=self.request.get_host(), stripe_public_key=True)
        return context | user_context


class ItemBuyView(DataMixin, View):
    def get(self, request, id):
        item = self.get_item(pk=id)
        # TODO: В продакшене тут логика получения скидки (из корзины/по купону и др.) и доп сбора (по типу товара, фиксированный и др.), для теста берем первую скидку и доп сбор по pk=1.
        discount = get_by_pk(Discount, pk=1)
        tax = get_by_pk(Tax, pk=1)

        # TODO: В продакшене тут логика составления заказа, например, по корзине с последующей привязкой по пользователю, для теста берем тот item, по которому поступил get запрос.
        order = create_order(items=[item], discount=discount, tax=tax)

        stripe_service = StripeService(order=order)

        # Реализация со stripe session
        # host = request.get_host()
        # session_id = stripe_service.create_checkout_session(host)
        # return JsonResponse(data={"id": session_id})

        # Реализация со stripe payment intent
        client_secret = stripe_service.create_payment_intent()
        return JsonResponse(data={"clientSecret": client_secret})


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
