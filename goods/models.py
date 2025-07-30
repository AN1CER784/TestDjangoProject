import stripe
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from TestDjangoProject.settings import STRIPE_SECRET_KEY

CURRENCIES_CHOICES = {
    "usd": "Доллар",
    "rub": "Рубль"
}


class Item(models.Model):
    """Модель Item для товара подлежащего покупке, содержит название, описание и цену товара"""

    name = models.CharField(max_length=255, verbose_name="Название")
    description = models.TextField(max_length=800, verbose_name="Описание")
    price = models.DecimalField(verbose_name="Цена", validators=[MinValueValidator(0)], default=0.00, max_digits=10,
                                decimal_places=2)
    currency = models.CharField(max_length=3, default="usd", choices=CURRENCIES_CHOICES, verbose_name="Валюта")

    class Meta:
        db_table = "item"
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ("id",)


class Order(models.Model):
    """Модель Order для оформления заказа. Заказ содержит несколько Item, дату создания, итоговую цену, внешние ключи, которые ссылаются на модель Discount (Скидка) и Tax (Доп. сбор)"""
    items = models.ManyToManyField('Item', verbose_name="Товары")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Время создания")
    discount = models.ForeignKey("Discount", null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Скидка")
    tax = models.ForeignKey("Tax", null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Дополнительный сбор")
    currency = models.CharField(max_length=3, default="usd", choices=CURRENCIES_CHOICES, verbose_name="Валюта",
                                blank=True)

    class Meta:
        db_table = "order"
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ("id",)


class Discount(models.Model):
    """Модель Discount для задавания скидки, содержит название, скидку в процентном эквиваленте и id купона stripe"""
    name = models.CharField(max_length=255, verbose_name="Название")
    percentage = models.PositiveIntegerField(null=True, blank=True, verbose_name="Скидка в процентном эквиваленте",
                                             validators=[MaxValueValidator(100)])
    stripe_coupon_id = models.CharField(max_length=255, blank=True, verbose_name="id купона stripe")

    class Meta:
        db_table = "discount"
        verbose_name = "Скидка"
        verbose_name_plural = "Скидки"
        ordering = ("id",)

    def save(self, *args, **kwargs):
        """Создаем купон по введенным параметрам пользователя и сохраняем его id"""
        stripe.api_key = STRIPE_SECRET_KEY
        if self.percentage:
            coupon = stripe.Coupon.create(
                percent_off=self.percentage,
                duration="forever",
                name=self.name
            )
        else:
            raise ValidationError("Укажите скидку")
        self.stripe_coupon_id = coupon.id
        super().save(*args, **kwargs)


class Tax(models.Model):
    """Модель Tax для задавания дополнительного сбора, содержит название и процент самого сбора"""
    name = models.CharField(max_length=255, verbose_name="Название")
    percentage = models.PositiveIntegerField(verbose_name="Сбор в процентном эквиваленте",
                                             validators=[MaxValueValidator(100)])
    stripe_tax_rate_id = models.CharField(max_length=255, blank=True, verbose_name="id сбора stripe")

    class Meta:
        db_table = "tax"
        verbose_name = "Дополнительный сбор"
        verbose_name_plural = "Дополнительные сборы"
        ordering = ("id",)

    def save(self, *args, **kwargs):
        """Создаем сбор по введенным параметрам пользователя и сохраняем его id"""
        stripe.api_key = STRIPE_SECRET_KEY
        tax_rate = stripe.TaxRate.create(
            display_name=self.name,
            inclusive=False,
            percentage=self.percentage,
        )
        self.stripe_tax_rate_id = tax_rate.id
        super().save(*args, **kwargs)
