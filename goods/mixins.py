from django.http import Http404

from TestDjangoProject.settings import STRIPE_PUBLIC_KEY
from goods.models import Item
from goods.utils import get_by_pk


class DataMixin:
    def get_user_context(self, **kwargs):
        context = kwargs
        public = context["stripe_public_key"]
        if public:
            context["STRIPE_PUBLIC_KEY"] = STRIPE_PUBLIC_KEY
        return context

    def get_item(self, pk):
        item = get_by_pk(Item, pk=pk)
        if not item:
            raise Http404("Item not found")
        return item
