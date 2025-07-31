from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from .models import Order


@receiver(m2m_changed, sender=Order.items.through)
def update_order_currency(sender, instance: Order, action, **kwargs):
    """
    Когда список items в заказе меняется, проверяем валюты и сохраняем currency.
    """
    if action in ("post_add", "post_remove", "post_clear"):
        currencies = list(instance.items.values_list("currency", flat=True).distinct())
        unique = set(currencies)
        if len(unique) > 1:
            raise ValueError("Все товары в заказе должны быть в одной валюте")

        new_currency = unique.pop() if unique else None
        if instance.currency != new_currency:
            if instance.currency != new_currency:
                instance.currency = new_currency
                instance.save(update_fields=["currency"])
