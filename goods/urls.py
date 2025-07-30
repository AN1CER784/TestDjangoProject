from django.urls import path

from goods.views import ItemView, ItemBuyView, SuccessView, CancelView, CompleteView

app_name = "goods"

urlpatterns = [
    path('item/<int:id>', ItemView.as_view(), name="item_lookout"),
    path('buy/<int:id>', ItemBuyView.as_view(), name="item_buy"),
    path('complete/', CompleteView.as_view(), name="compete_page"),
    path('success/', SuccessView.as_view(), name="success_page"),
    path('cancel/', CancelView.as_view(), name="cancel_page")
]
