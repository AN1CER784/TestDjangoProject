# TestDjangoProject

Полноценный пример Django-приложения с интеграцией Stripe Checkout и Payment Intent, моделями Item, Order, Discount, Tax, админкой и тестами.

---

## 🔎 Описание

Проект демонстрирует:

* Модели **Item**, **Order**, **Discount**, **Tax**
* CRUD-панель Django-admin для управления товарами, скидками и налогами
* Интеграцию со Stripe Checkout Session и Stripe Payment Intent
* Расчёт итоговой суммы с учётом купонов и налогов
* Тесты на модели, представления и сервисный слой Stripe

---

## ⚙️ Стек технологий

* Python 3.13+
* Django 5.x
* Stripe Python SDK
* PostgreSQL
* Django TestCase

---

## 📦 Установка и запуск

1. **Клонировать репозиторий**

   ```bash
   git clone https://github.com/AN1CER784/TestDjangoProject.git
   cd TestDjangoProject
   ```

2. **Создать файл `.env` и заполните:**

   ```
   STRIPE_PUBLIC_KEY=
   STRIPE_SECRET_KEY=
   STRIPE_WEBHOOK_SECRET=
   SECRET_KEY=
   POSTGRES_DB=
   POSTGRES_USER=
   POSTGRES_PASSWORD=
   ALLOWED_HOSTS=
   ```

3. **Создать и запустить контейнеры**

   ```bash
   docker-compose up --build # для localhost
   ```

   Приложение доступно по адресу: [http://localhost:80/]

4. **Собрать статику**

   ```bash
   docker container exec -it testdjangoproject-web-1 python manage.py collectstatic --noinput
   ```

5. **Создать суперпользователя для управления админ-панелью**

   ```bash
   docker container exec -it testdjangoproject-web-1 python manage.py createsuperuser
   ```

6. **Используя Stripe CLI запустить локальный слушатель вебхуков для обновления статуса заказов (Опционально)**
    ```bash
   stripe listen --forward-to localhost:8000/webhooks/stripe/
   ```
---

## 🛒 Эндпоинты и страницы

* **GET** `/item/<id>/`
  Отображает карточку товара с кнопкой “Купить” и Stripe Elements для оплаты.

* **GET** `/buy/<id>/`
  Возвращает JSON:


 * **При Stripe Payment Intent:**
  ```json
  { "clientSecret": "pi…" }
  ```
* **GET** `/complete/`
  Страница окончания платежа после оплаты по Stripe Payment Intent.


 * **При Stripe Session:**
  ```json
  { "sessionId": "cs…" }
  ```

* **GET** `/success/`
  Страница успешного платежа при Stripe Session.

* **GET** `/cancel/`
  Страница отмены платежа при Stripe Session.

* **POST** `/webhooks/stripe/`
  Обработка вебхука при оплате, обновляет статус заказа при успешной оплате

---

## 🗄️ Модели

### Абстрактные базовые классы

* **`TimestampedModel`**

  * `created_at` — `DateTimeField(auto_now_add=True)`

* **`StripeEntity`**

  * `name` — `CharField`
  * `percentage` — `PositiveIntegerField` (0–100)
  * `stripe_id` — `CharField(blank=True)`
  * при `save()` автоматически создаёт соответствующий ресурс в Stripe и сохраняет его `id`

---

### 🗄️ Модели

### Абстрактные базовые классы

* **`TimestampedModel`**

  * `created_at` — `DateTimeField(auto_now_add=True)`

* **`StripeEntity`**

  * `name` — `CharField`
  * `percentage` — `PositiveIntegerField` (0–100)
  * `stripe_id` — `CharField(blank=True)`
  * при `save()` автоматически создаёт соответствующий ресурс в Stripe и сохраняет его `id`

---

### Конкретные модели

* **`Item`**

  * `name` — `CharField`
  * `description` — `TextField`
  * `price` — `DecimalField`
  * `currency` — `CharField(choices=['usd','rub'])`
  * `get_absolute_url()` → URL просмотра товара

* **`Order`** (наследует `TimestampedModel`)

  * `items` — `ManyToManyField(Item)`
  * `discount` — `ForeignKey(Discount, null=True, blank=True)`
  * `tax` — `ForeignKey(Tax, null=True, blank=True)`
  * `currency` — `CharField(choices=['usd','rub'], default='usd')`
  * `status` — `CharField(choices=['Created','InProgress','Done'], default='Created')`
  * `created_at` (от `TimestampedModel`)
  * **`status`** обновляется по Stripe-вебхукам

* **`Discount`** (наследует `StripeEntity`)

  * `name` — `CharField`
  * `percentage` — `PositiveIntegerField`
  * `stripe_id` — `CharField` (ID купона в Stripe)

* **`Tax`** (наследует `StripeEntity`)

  * `name` — `CharField`
  * `percentage` — `PositiveIntegerField`
  * `stripe_id` — `CharField` (ID ставки налога в Stripe)

---

## 💳 Интеграция со Stripe

* **Checkout Session**: `StripeService.create_checkout_session()`
* **Payment Intent**: `StripeService.create_payment_intent()`
* Линейные позиции формируются в `create_line_items`, скидка и налог подтягиваются через модели Discount/Tax

---

## ✅ Тестирование

```bash
docker container exec -it testdjangoproject-web-1 python manage.py test 
```

Покрыты:

* Модели
* Сервисный слой
* Представления