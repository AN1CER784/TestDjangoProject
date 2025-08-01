from typing import Optional

from goods.models import Item, Order, Discount, Tax


def get_order_by_user_data(items: list[Item], session_key: str, discount: Optional[Discount] = None,
                           tax: Optional[Tax] = None) -> Order | None:
    """Проверяет есть ли заказ созданный заказ не находящийся в исполнении с этими данными"""
    qs = (
        Order.objects
        .filter(status="Created", session_key=session_key, discount=discount, tax=tax).select_related('discount','tax').prefetch_related("items")
    )
    wanted = {item.pk for item in items}

    for order in qs:
        if {it.pk for it in order.items.all()} == wanted:
            return order


def create_or_get_order(items: list[Item], session_key: str, discount: Optional[Discount] = None,
                        tax: Optional[Tax] = None) -> Order:
    """Создает заказ по списку товаров, применяет скидку и сбор, если они переданы"""
    order = get_order_by_user_data(items, session_key, discount, tax)
    if not order:
        order = Order.objects.create(session_key=session_key, discount=discount, tax=tax)
        order.items.add(*items)

        order = (
            Order.objects
            .select_related('discount', 'tax')
            .prefetch_related('items')
            .get(pk=order.pk)
        )

    return order
