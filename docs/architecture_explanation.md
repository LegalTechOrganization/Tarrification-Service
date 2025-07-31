# Архитектура интеграции Gateway с BillingTariffication-Service

## 🏗️ Правильная архитектура

```
Клиенты → Gateway (порт 8000) → BillingTariffication-Service (порт 8001)
```

### 📋 Роли сервисов:

#### **Gateway (API Gateway)**
- **Назначение**: Прокси-сервис, который принимает запросы от клиентов
- **Публичные эндпоинты**: `/billing/quota/check`, `/billing/quota/debit`, `/billing/quota/credit`
- **Функции**:
  - Аутентификация клиентов
  - Проксирование запросов к микросервисам
  - Преобразование форматов данных
  - Обработка ошибок и fallback

#### **BillingTariffication-Service**
- **Назначение**: Внутренний сервис для управления балансом
- **Внутренние эндпоинты**: `/internal/billing/*`
- **Функции**:
  - Бизнес-логика управления балансом
  - Работа с базой данных
  - Идемпотентность транзакций

## 🔄 Поток запросов

### 1. Проверка квоты
```
Клиент → GET /billing/quota/check?user_id=123&action=chat&units=5
    ↓
Gateway → GET /internal/billing/balance?user_id=123
    ↓
BillingTariffication-Service → База данных
    ↓
Gateway → {allowed: true, remain: 100.0}
    ↓
Клиент ← {allowed: true, remain: 100.0}
```

### 2. Списание квоты
```
Клиент → POST /billing/quota/debit {"user_id": "123", "action": "chat", "units": 5}
    ↓
Gateway → POST /internal/billing/debit {"user_id": "123", "units": 5, "ref": "chat-uuid", "reason": "chat"}
    ↓
BillingTariffication-Service → База данных (списание)
    ↓
Gateway → {remain: 95.0}
    ↓
Клиент ← {remain: 95.0}
```

### 3. Пополнение квоты
```
Клиент → POST /billing/quota/credit {"user_id": "123", "action": "payment", "units": 100}
    ↓
Gateway → POST /internal/billing/credit {"user_id": "123", "units": 100, "ref": "payment-uuid", "reason": "payment", "source_service": "gateway"}
    ↓
BillingTariffication-Service → База данных (пополнение)
    ↓
Gateway → {remain: 195.0}
    ↓
Клиент ← {remain: 195.0}
```

## 📁 Структура файлов

### В Gateway проекте:
```
gateway/
├── services/
│   └── microservice_client.py    # Универсальный клиент для микросервисов
├── controllers/
│   └── billing_controller.py     # Контроллеры для проксирования
├── .env                          # BILLING_SERVICE_URL=http://localhost:8001
└── main.py                       # Подключение роутеров
```

### В BillingTariffication-Service:
```
billing-service/
├── app/
│   ├── api/routes/
│   │   ├── billing.py            # Внутренние эндпоинты /internal/billing/*
│   │   └── health.py             # Health check
│   ├── services/
│   │   ├── balance_service.py    # Бизнес-логика баланса
│   │   └── plan_service.py       # Бизнес-логика планов
│   └── repositories/
│       ├── balance_dao.py        # Работа с балансом
│       └── transaction_dao.py    # Работа с транзакциями
└── docker-compose.yml
```

## 🔧 Настройка

### 1. Gateway (.env)
```env
BILLING_SERVICE_URL=http://localhost:8001
BILLING_SERVICE_TOKEN=super-secret-dev
```

### 2. BillingTariffication-Service (.env)
```env
SERVICE_TOKEN=super-secret-dev
DB_DSN=postgresql+asyncpg://user:pass@localhost:5456/db
```

## ✅ Преимущества такой архитектуры

1. **Разделение ответственности**:
   - Gateway отвечает за маршрутизацию и аутентификацию
   - BillingTariffication-Service отвечает за бизнес-логику

2. **Безопасность**:
   - Внутренние эндпоинты защищены токеном
   - Клиенты не имеют прямого доступа к BillingTariffication-Service

3. **Масштабируемость**:
   - Легко добавлять новые микросервисы
   - Gateway может кэшировать и балансировать нагрузку

4. **Надежность**:
   - Fallback в Gateway при недоступности микросервисов
   - Идемпотентность транзакций в BillingTariffication-Service

## 🚀 Запуск

### 1. Запуск BillingTariffication-Service:
```bash
cd Tarrification-Service
docker-compose up -d
```

### 2. Запуск Gateway:
```bash
cd gateway
uvicorn main:app --reload --port 8000
```

### 3. Тестирование:
```bash
# Проверка квоты
curl "http://localhost:8000/billing/quota/check?user_id=test&action=chat&units=5"

# Списание квоты
curl -X POST "http://localhost:8000/billing/quota/debit" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","action":"chat","units":5}'

# Пополнение квоты
curl -X POST "http://localhost:8000/billing/quota/credit" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","action":"payment","units":100}'
```

## 🎯 Итог

**Да, вы абсолютно правы!** В BillingTariffication-Service нужны только **внутренние эндпоинты** `/internal/billing/*`, а Gateway будет проксировать запросы к ним через свой универсальный клиент. 