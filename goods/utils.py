from typing import TypeVar, Type

from django.db.models import Model


def convert_price(price: float) -> int:
    """Переводит цену в нужные единицы (копейки или центы)"""
    return int(price * 100)


M = TypeVar('M', bound=Model)


def get_by_pk(model: Type[M], pk: int) -> M | None:
    """Получает модель по pk или возвращает None"""
    return model.objects.filter(pk=pk).first()
