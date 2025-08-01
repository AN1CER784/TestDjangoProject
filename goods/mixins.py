from django.core.cache import cache
from django.http import Http404

from TestDjangoProject.settings import STRIPE_PUBLIC_KEY
from goods.models import Item
from goods.utils import get_by_pk


class DataMixin:
    def get_user_context(self, **kwargs):
        """Сохраняем дополнительный контекст"""
        context = kwargs
        public = context.get("stripe_public_key", None)
        if public:
            context["STRIPE_PUBLIC_KEY"] = STRIPE_PUBLIC_KEY
        return context

    def get_item(self, pk: int) -> Item:
        """Получаем товар, если нет возвращаем 404"""
        item = get_by_pk(Item, pk=pk)
        if not item:
            raise Http404("Item not found")
        return item

    def get_session(self, request) -> str:
        if not request.session.session_key:
            request.session.create()
        return request.session.session_key


class CacheMixin:
    def get_cache_key(self, session_key: str, obj_id: int) -> str | None:
        """Генерируем ключ для кэша."""
        return f"session_buy_{session_key}_{obj_id}"

    def get_cached_response(self, session_key: str, obj_id: int) -> dict | None:
        """Получаем кэшированный ответ, если есть."""
        key = self.get_cache_key(session_key, obj_id)
        if key:
            return cache.get(key)

    def set_cached_response(self, session_key: str, obj_id: int, data: dict, timeout: int) -> None:
        """Сохраняем ответ в кэш."""
        key = self.get_cache_key(session_key, obj_id)
        if key:
            cache.set(key, data, timeout=timeout)
