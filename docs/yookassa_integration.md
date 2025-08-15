# Интеграция с ЮKassa

## Обзор архитектуры

BillingTariffication-Service интегрируется с ЮKassa через отдельный Pay-Service, который обрабатывает платежи и вебхуки.

```
[Клиент] → [Gateway] → [Pay-Service] → [ЮKassa]
[ЮKassa] → [Pay-Service] → [BillingTariffication-Service]
```

## Компоненты

### 1. BillingTariffication-Service
- **Эндпоинт**: `POST /internal/billing/payment/webhook`
- **Назначение**: Обработка подтвержденных платежей от Pay-Service
- **Функции**: Начисление средств, применение тарифных планов

### 2. Pay-Service
- **Эндпоинт**: `POST /payments/create`
- **Назначение**: Создание платежей в ЮKassa
- **Эндпоинт**: `POST /webhooks/yookassa`
- **Назначение**: Обработка вебхуков от ЮKassa

## Поток платежа

### 1. Создание платежа
```bash
POST /payments/create
{
  "user_id": "user-123",
  "amount": 750.0,
  "plan_code": "base750",
  "description": "Покупка тарифного плана Base 750",
  "return_url": "https://yourapp.com/payment/success",
  "auto_renew": false
}
```

### 2. Обработка вебхука от ЮKassa
```bash
POST /webhooks/yookassa
{
  "id": "yk-26f16e2d-000f-5000-9000-1a2b000c3d4e",
  "status": "succeeded",
  "paid": true,
  "amount": {
    "value": "750.00",
    "currency": "RUB"
  },
  "metadata": {
    "user_id": "user-123",
    "plan_code": "base750"
  }
}
```

### 3. Начисление средств в BillingTariffication-Service
```bash
POST /internal/billing/payment/webhook
{
  "payment_id": "yk-26f16e2d-000f-5000-9000-1a2b000c3d4e",
  "user_id": "user-123",
  "amount": 750.0,
  "currency": "RUB",
  "payment_status": "succeeded",
  "plan_code": "base750",
  "auto_renew": false
}
```

## Конфигурация

### Переменные окружения для Pay-Service
```bash
BILLING_SERVICE_URL=http://localhost:8001
BILLING_SERVICE_TOKEN=super-secret-dev
YOO_KASSA_SHOP_ID=your_shop_id
YOO_KASSA_SECRET_KEY=your_secret_key
```

### Переменные окружения для BillingTariffication-Service
```bash
DB_DSN=postgresql+asyncpg://billing_user:billing_pass@localhost:5456/billing_db
SERVICE_TOKEN=super-secret-dev
```

## Тестирование

### 1. Запуск сервисов
```bash
# BillingTariffication-Service
docker-compose up -d

# Pay-Service (отдельно)
python examples/pay_service_example.py
```

### 2. Создание платежа
```bash
curl -X POST http://localhost:8002/payments/create \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-123",
    "amount": 750.0,
    "plan_code": "base750",
    "description": "Тестовый платеж",
    "return_url": "https://example.com/success"
  }'
```

### 3. Симуляция вебхука
```bash
curl -X POST http://localhost:8002/webhooks/yookassa \
  -H "Content-Type: application/json" \
  -d '{
    "id": "yk-test-payment",
    "status": "succeeded",
    "paid": true,
    "amount": {"value": "750.00", "currency": "RUB"},
    "metadata": {"user_id": "test-user-123", "plan_code": "base750"}
  }'
```

### 4. Проверка баланса
```bash
curl -X GET "http://localhost:8001/internal/billing/balance?user_id=test-user-123" \
  -H "X-Internal-Key: super-secret-dev"
```

## Безопасность

### 1. Верификация вебхуков
- Проверка подписи от ЮKassa
- Валидация данных платежа
- Проверка статуса платежа

### 2. Идемпотентность
- Уникальные ID платежей
- Проверка дублирования транзакций
- Логирование всех операций

### 3. Аутентификация
- X-Internal-Key для межсервисного взаимодействия
- Валидация токенов доступа

## Обработка ошибок

### Типичные ошибки
- `400 Bad Request`: Неверные данные платежа
- `401 Unauthorized`: Неверный внутренний ключ
- `403 Forbidden`: Недостаточно средств
- `409 Conflict`: Дублирование транзакции
- `500 Internal Server Error`: Ошибка сервиса

### Логирование
- Все платежные операции логируются
- Ошибки сохраняются с контекстом
- Метрики для мониторинга

## Мониторинг

### Метрики Prometheus
- `payment_total{status="success|failed"}`
- `payment_amount_total{currency="RUB"}`
- `webhook_processing_duration_seconds`

### Алерты
- Ошибки вебхуков
- Неуспешные платежи
- Высокая задержка обработки 