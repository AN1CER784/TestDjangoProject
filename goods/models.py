import stripe
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse

from TestDjangoProject.settings import STRIPE_SECRET_KEY


CURRENCIES_CHOICES = [
    ("usd", "Доллар"),
    ("rub", "Рубль"),
]

ORDER_STATUS_CHOICES = [
    ("Created", "Создан"),
    ("InProgress", "В процессе"),
    ("Done", "Выполнен"),
]


class TimestampedModel(models.Model):
    """Абстрактный класс с полем created_at."""
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Время создания")

    class Meta:
        abstract = True


class StripeEntity(models.Model):
    """
    Абстрактный базовый класс для моделей, которые создают ресурс в Stripe при save().
    Поля: name, percentage + в дочернем классе храним stripe_id и логику создания.
    """
    name = models.CharField(max_length=255, verbose_name="Название")
    percentage = models.PositiveIntegerField(
        validators=[MaxValueValidator(100)],
        verbose_name="Процент",
    )
    stripe_id = models.CharField(max_length=255, blank=True, verbose_name="Stripe ID")

    class Meta:
        abstract = True

    stripe_create_kwargs: dict = {}  # дочерний класс должен определить: что передать в create()

    def save(self, *args, **kwargs):
        stripe.api_key = STRIPE_SECRET_KEY
        if self.percentage is None:
            raise ValidationError("Укажите процент")
        # вызываем соответствующий метод Stripe, настроенный в дочернем классе
        obj = self._stripe_create()
        self.stripe_id = obj.id
        super().save(*args, **kwargs)

    def _stripe_create(self):
        """
        Должен быть переопределён в дочернем классе,
        возвращать объект от Stripe API с атрибутом `.id`.
        """
        raise NotImplementedError("Define `_stripe_create` in subclass")


class Discount(StripeEntity):
    """Модель Discount для задавания скидки, содержит название, скидку в процентном эквиваленте и id купона stripe"""
    class Meta:
        db_table = "discount"
        verbose_name = "Скидка"
        verbose_name_plural = "Скидки"

    stripe_create_kwargs = {
        "duration": "forever",
    }

    def _stripe_create(self) -> stripe.Coupon:
        return stripe.Coupon.create(
            percent_off=self.percentage,
            name=self.name,
            **self.stripe_create_kwargs
        )


class Tax(StripeEntity):
    """Модель Tax для задавания дополнительного сбора, содержит название и процент самого сбора и id налога stripe"""
    class Meta:
        db_table = "tax"
        verbose_name = "Дополнительный сбор"
        verbose_name_plural = "Дополнительные сборы"

    stripe_create_kwargs = {
        "inclusive": False,
    }

    def _stripe_create(self) -> stripe.TaxRate:
        return stripe.TaxRate.create(
            display_name=self.name,
            percentage=self.percentage,
            **self.stripe_create_kwargs
        )


class Item(models.Model):
    """Модель Item для товара подлежащего покупке, содержит название, описание и цену товара"""
    name = models.CharField(max_length=255, verbose_name="Название")
    description = models.TextField(max_length=800, verbose_name="Описание")
    price = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Цена"
    )
    currency = models.CharField(
        max_length=3, choices=CURRENCIES_CHOICES,
        default="usd", verbose_name="Валюта"
    )

    class Meta:
        db_table = "item"
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ("id",)

    def get_absolute_url(self):
        return reverse("goods:item_lookout", kwargs={"id": self.pk})


class Order(TimestampedModel):
    """
    Модель Order для оформления заказа.
    Заказ содержит несколько Item, дату создания, итоговую цену, внешние ключи, которые ссылаются на модель Discount (Скидка) и Tax (Доп. сбор)
    """
    items = models.ManyToManyField(Item, verbose_name="Товары")
    discount = models.ForeignKey(
        Discount, null=True, blank=True, on_delete=models.SET_NULL,
        verbose_name="Скидка"
    )
    tax = models.ForeignKey(
        Tax, null=True, blank=True, on_delete=models.SET_NULL,
        verbose_name="Доп. сбор"
    )
    currency = models.CharField(
        max_length=3, choices=CURRENCIES_CHOICES,
        default="usd", blank=True, verbose_name="Валюта"
    )
    status = models.CharField(
        max_length=15, choices=ORDER_STATUS_CHOICES,
        default="Created", verbose_name="Статус"
    )
    session_key = models.CharField(
        max_length=255, verbose_name="Ключ Сессии"
    )

    class Meta:
        db_table = "order"
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ("id",)
