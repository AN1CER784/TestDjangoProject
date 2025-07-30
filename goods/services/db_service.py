from typing import Optional

from goods.models import Item, Order, Discount, Tax


def create_order(items: list[Item], discount: Optional[Discount] = None, tax: Optional[Tax] = None) -> Order:
    """Создает заказ по списку товаров, применяет скидку и сбор, если они переданы"""
    order = Order.objects.create(discount=discount, tax=tax)
    order.items.add(*items)

    order._prefetched_objects_cache = {"items": items}

    return order
