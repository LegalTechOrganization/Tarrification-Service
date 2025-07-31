# BillingTariffication-Service

Внутренний микросервис для управления тарификацией и квотами пользователей в системе LegaTech.

> **Внимание**: Это внутренний сервис, предназначенный только для межсервисного взаимодействия. Внешние HTTP запросы обрабатываются через Gateway.

## 🎯 Назначение

Сервис решает следующие задачи:
- **Учёт тарифов/лимитов** пользователей (Chat- и Template-квоты)
- **Списание** квоты при каждом платном вызове
- **Пополнение** баланса после успешной оплаты
- **Авто-reset** дневных/месячных лимитов
- **Отчётность и метрики** через Prometheus

> **Важно**: Это внутренний сервис, который не обрабатывает внешние HTTP запросы. Все внешние запросы проходят через Gateway, который затем вызывает внутренние эндпоинты этого сервиса.

## 🏗️ Архитектура

### Многослойная архитектура:

```
┌─────────────────┐
│   REST API      │ ← FastAPI контроллеры
├─────────────────┤
│   Services      │ ← Бизнес-логика
├─────────────────┤
│  Repositories   │ ← DAO слой
├─────────────────┤
│   Database      │ ← SQLAlchemy + PostgreSQL
└─────────────────┘
```

### Основные компоненты:

- **REST Layer**: `BillingController` (внутренние эндпоинты), `HealthController`
- **Service Layer**: `QuotaManager`, `PaymentWebhook`
- **Repository Layer**: `PlanDAO`, `UsageDAO`, `ReceiptDAO`
- **Task Layer**: `CounterResetTask` (cron)

### Архитектура взаимодействия:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Gateway   │───▶│   Chat-svc  │───▶│   Billing   │
│             │    │             │    │   Service   │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   ▲
       │                   │                   │
       ▼                   ▼                   │
┌─────────────┐    ┌─────────────┐            │
│  Template   │───▶│   Pay-svc   │────────────┘
│    -svc     │    │             │
└─────────────┘    └─────────────┘
```

> Gateway обрабатывает внешние запросы и вызывает внутренние эндпоинты Billing Service

## 🚀 Быстрый старт

### 📋 Доступные команды

#### Основные команды:
```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск тестов
pytest tests/ -v

# Запуск сервиса локально
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# Запуск с Docker
docker-compose up -d

# Остановка Docker
docker-compose down

# Демонстрация API
python scripts/demo.py
```

### Локальная разработка

#### Linux/macOS:
1. **Клонирование и установка зависимостей:**
```bash
git clone <repository>
cd Tarrification-Service
pip install -r requirements.txt
```

2. **Запуск с Docker Compose:**
```bash
docker-compose up -d
```

3. **Или локальный запуск:**
```bash
# Настройте переменные окружения
export DB_DSN="postgresql+asyncpg://user:pass@localhost:5456/billing_db"
export SERVICE_TOKEN="your-secret-token"

# Запуск
uvicorn app.main:app --reload --port 8001
```

#### Windows:
1. **Клонирование и установка зависимостей:**
```powershell
git clone <repository>
cd Tarrification-Service
pip install -r requirements.txt
```

2. **Запуск с Docker Compose:**
```powershell
docker-compose up -d
```

3. **Или локальный запуск:**
```powershell
# Настройте переменные окружения в .env файле
# Затем запуск:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# Сервис будет доступен на http://localhost:8001
# База данных PostgreSQL будет доступна на localhost:5456
```

### Переменные окружения

```bash
# База данных
DB_DSN=postgresql+asyncpg://billing_user:billing_pass@localhost:5456/billing_db

# Безопасность
SERVICE_TOKEN=super-secret-dev

# Сервис
SERVICE_NAME=billing-tariffication
SERVICE_VERSION=1.0.0
```

## 📡 API Endpoints

### Внутренние эндпоинты (только для межсервисного взаимодействия)

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/internal/billing/quota/check/{user_id}` | Проверить остаток квот |
| `POST` | `/internal/billing/quota/debit` | Списать квоту |
| `POST` | `/internal/billing/quota/credit` | Пополнить квоту |
| `POST` | `/internal/billing/webhook/payment` | Webhook от Pay-svc |

> **Важно**: Все эндпоинты требуют `X-Internal-Key` заголовок и предназначены только для внутреннего использования другими микросервисами. Внешние запросы обрабатываются через Gateway.

### Health check

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/health` | Статус сервиса |
| `GET` | `/ready` | Readiness check |
| `GET` | `/metrics` | Prometheus метрики |

### Примеры внутренних запросов

#### Проверка квот (вызывается из Gateway)
```bash
curl -X GET "http://localhost:8000/internal/billing/quota/check/user-123" \
  -H "X-Internal-Key: super-secret"
```

**Ответ:**
```json
{
  "remain_chat": 54,
  "remain_tpl": 19,
  "plan_code": "free"
}
```

#### Списание квоты (вызывается из Chat-svc)
```bash
curl -X POST "http://localhost:8000/internal/billing/quota/debit" \
  -H "X-Internal-Key: super-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "5cdb...",
    "action": "chat_tokens",
    "units": 1,
    "ref": "msg-7f2e4b"
  }'
```

#### Списание квоты (вызывается из Template-svc)
```bash
curl -X POST "http://localhost:8000/internal/billing/quota/debit" \
  -H "X-Internal-Key: super-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "5cdb...",
    "action": "tpl_run",
    "units": 1,
    "ref": "req-876c9a"
  }'
```

#### Пополнение квоты (вызывается из Pay-svc)
```bash
curl -X POST "http://localhost:8000/internal/billing/quota/credit" \
  -H "X-Internal-Key: super-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "yka-123",
    "user_id": "5cdb...",
    "plan_code": "pro_month",
    "units_chat": 10000,
    "units_tpl": 200
  }'
```

## 🗄️ Модель данных

### Таблицы

1. **user_plans** - Тарифные планы пользователей
2. **usage_counters** - Счетчики использования
3. **payment_receipts** - Чеки платежей

### Схема БД

```sql
-- Тарифные планы
CREATE TABLE user_plans (
    id UUID PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    plan_code VARCHAR NOT NULL,
    chat_limit INTEGER NOT NULL DEFAULT 0,
    template_limit INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

-- Счетчики использования
CREATE TABLE usage_counters (
    id UUID PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    user_plan_id UUID REFERENCES user_plans(id),
    counter_type VARCHAR NOT NULL, -- daily, monthly
    chat_used INTEGER DEFAULT 0,
    template_used INTEGER DEFAULT 0,
    reset_date TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

-- Чеки платежей
CREATE TABLE payment_receipts (
    id UUID PRIMARY KEY,
    order_id VARCHAR UNIQUE NOT NULL,
    user_id VARCHAR NOT NULL,
    plan_code VARCHAR NOT NULL,
    amount INTEGER NOT NULL,
    currency VARCHAR DEFAULT 'RUB',
    chat_units_added INTEGER DEFAULT 0,
    template_units_added INTEGER DEFAULT 0,
    payment_status VARCHAR DEFAULT 'pending',
    receipt_data TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);
```

## 🔧 Разработка

### Структура проекта

```
Tarrification-Service/
├── app/
│   ├── main.py                 # FastAPI приложение
│   ├── config.py              # Конфигурация
│   ├── api/                   # REST API
│   │   └── routes/
│   │       ├── billing.py     # Бизнес-эндпоинты
│   │       └── health.py      # Health check
│   ├── services/              # Бизнес-логика
│   │   ├── quota_manager.py   # Управление квотами
│   │   └── payment_webhook.py # Обработка платежей
│   ├── models/                # Модели данных
│   │   ├── database.py        # SQLAlchemy модели
│   │   └── schemas.py         # Pydantic схемы
│   ├── repositories/          # DAO слой
│   │   ├── base_dao.py        # Базовый DAO
│   │   ├── plan_dao.py        # DAO планов
│   │   ├── usage_dao.py       # DAO счетчиков
│   │   └── receipt_dao.py     # DAO чеков
│   ├── database/              # Подключение к БД
│   │   └── connection.py      # SQLAlchemy setup
│   └── tasks/                 # Фоновые задачи
│       └── counter_reset.py   # Сброс счетчиков
├── tests/                     # Тесты
├── requirements.txt           # Зависимости
├── Dockerfile                 # Docker образ
├── docker-compose.yml         # Docker Compose
└── README.md                  # Документация
```

### Запуск тестов

#### Linux/macOS:
```bash
# Установка тестовых зависимостей
pip install pytest pytest-asyncio pytest-mock

# Запуск тестов
pytest tests/ -v

# С покрытием
pytest tests/ --cov=app --cov-report=html
```

#### Windows:
```powershell
# Запуск всех тестов
.\run.ps1 test
# или
run.bat test

# Запуск unit тестов
.\run.ps1 test-unit
# или
run.bat test-unit

# Запуск тестов с покрытием
.\run.ps1 test-cov
# или
run.bat test-cov
```

### Миграции БД

```bash
# Инициализация Alembic
alembic init alembic

# Создание миграции
alembic revision --autogenerate -m "Initial migration"

# Применение миграций
alembic upgrade head
```

## 📊 Мониторинг

### Prometheus метрики

- `billing_quota_remaining{type="chat|template", user_id="..."}` - Остаток квот
- `billing_deduct_total{result="ok|fail"}` - Количество списаний
- `billing_credit_total` - Количество пополнений

### Health check

```bash
# Проверка статуса
curl http://localhost:8000/health

# Проверка готовности
curl http://localhost:8000/ready

# Метрики
curl http://localhost:8000/metrics
```

## 🔒 Безопасность

### Межсервисное взаимодействие

- **X-Internal-Key** - секретный токен для внутренних вызовов
- **JWT** - валидация токенов от Gateway
- **RSA-SHA-256** - подпись webhook'ов от ЮKassa

### Рекомендации по безопасности

1. Используйте HTTPS в продакшене
2. Храните секреты в Vault/Kubernetes Secrets
3. Ограничьте доступ к БД
4. Настройте CORS для конкретных доменов

## 🚀 Развертывание

### Docker

```bash
# Сборка образа
docker build -t billing-service .

# Запуск
docker run -p 8000:8000 \
  -e DB_DSN="postgresql+asyncpg://..." \
  -e SERVICE_TOKEN="..." \
  billing-service
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: billing-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: billing-service
  template:
    metadata:
      labels:
        app: billing-service
    spec:
      containers:
      - name: billing-service
        image: billing-service:latest
        ports:
        - containerPort: 8000
        env:
        - name: DB_DSN
          valueFrom:
            secretKeyRef:
              name: billing-secrets
              key: db-dsn
        - name: SERVICE_TOKEN
          valueFrom:
            secretKeyRef:
              name: billing-secrets
              key: service-token
```

## 🤝 Интеграция с другими сервисами

### В Chat-svc

```python
import httpx

async def deduct_chat_quota(user_id: str, units: int, ref: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://billing-service:8000/internal/billing/quota/debit",
            headers={"X-Internal-Key": "super-secret"},
            json={
                "user_id": user_id,
                "action": "chat_tokens",
                "units": units,
                "ref": ref
            }
        )
        return response.json()
```

### В Template-svc

```python
async def deduct_template_quota(user_id: str, units: int, ref: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://billing-service:8000/internal/billing/quota/debit",
            headers={"X-Internal-Key": "super-secret"},
            json={
                "user_id": user_id,
                "action": "tpl_run",
                "units": units,
                "ref": ref
            }
        )
        return response.json()
```

### В Pay-svc

```python
async def credit_quota(order_id: str, user_id: str, plan_code: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://billing-service:8000/internal/billing/quota/credit",
            headers={"X-Internal-Key": "super-secret"},
            json={
                "order_id": order_id,
                "user_id": user_id,
                "plan_code": plan_code,
                "units_chat": 10000,
                "units_tpl": 200
            }
        )
        return response.json()
```

### В Gateway

```python
async def check_user_quota(user_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://billing-service:8000/internal/billing/quota/check/{user_id}",
            headers={"X-Internal-Key": "super-secret"}
        )
        return response.json()
```

## 📝 TODO

- [ ] Реализовать проверку RSA-SHA-256 подписи ЮKassa
- [ ] Добавить dead-letter queue для невалидных webhook'ов
- [ ] Выбрать валюту планов (RUB/USD)
- [ ] Добавить баг-bounty на гонки FOR UPDATE SKIP LOCKED
- [ ] Реализовать кэширование с Redis
- [ ] Добавить API для управления тарифными планами
- [ ] Создать дашборд для мониторинга

## 📄 Лицензия

MIT License 