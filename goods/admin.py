from django.contrib import admin

from .models import Item, Order, Discount, Tax


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "price")
    search_fields = ("name", "description")
    list_filter = ("price",)
    ordering = ("id",)


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "percentage", "stripe_id")
    search_fields = ("name", "stripe_id")
    readonly_fields = ("stripe_id",)
    ordering = ("id",)


@admin.register(Tax)
class TaxAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "percentage", "stripe_id")
    search_fields = ("name", "percentage", "stripe_id")
    readonly_fields = ("stripe_id",)
    ordering = ("id",)


class ItemInline(admin.TabularInline):
    model = Order.items.through
    extra = 1


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "discount", "tax", 'status', 'session_key')
    list_filter = ("created_at", "discount", "tax")
    search_fields = ("id",)
    ordering = ("id",)
    date_hierarchy = "created_at"

    inlines = [ItemInline]
    exclude = ("items",)
