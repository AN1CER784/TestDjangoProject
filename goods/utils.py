from typing import Type


def convert_price(price: float) -> int:
    """Переводит цену в нужные единицы (копейки или центы)"""
    return int(price * 100)

