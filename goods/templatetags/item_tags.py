from typing import Literal

from django import template

register = template.Library()


@register.filter()
def convert_currency_to_fancy_format(value: Literal["usd"] | Literal["rub"]) -> Literal["$"] | Literal["₽"] | str:
    """Шаблонный фильтр: по коду валюты возвращает её символ."""
    currencies = {
        "usd": "$",
        "rub": "₽"
    }
    return currencies.get(value, value)
