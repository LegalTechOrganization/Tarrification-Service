# Пошаговая инструкция по настройке интеграции Gateway с BillingTariffication-Service

## Шаг 1: Настройка переменных окружения в Gateway

Добавьте в `.env` файл вашего Gateway сервиса:

```env
# URL и токен для BillingTariffication-Service
BILLING_SERVICE_URL=http://localhost:8001
BILLING_SERVICE_TOKEN=super-secret-dev
```

## Шаг 2: Установка зависимостей в Gateway

Добавьте в `requirements.txt` вашего Gateway:

```txt
httpx>=0.24.0
```

## Шаг 3: Копирование клиента в Gateway

Скопируйте файл `examples/gateway_billing_client.py` в ваш Gateway проект (например, в папку `utils/` или `clients/`).

## Шаг 4: Обновление вашего Gateway кода

Замените ваш текущий код на следующий:

```python
from fastapi import APIRouter, status, Query, Body, HTTPException
from pydantic import BaseModel
from typing import Optional
from uuid import uuid4

# Импортируем функции для работы с биллингом
from utils.gateway_billing_client import check_user_quota, debit_user_quota, credit_user_quota

router = APIRouter()

# Pydantic модели
class QuotaCheckResponse(BaseModel):
    allowed: bool
    remain: float

class QuotaDebitRequest(BaseModel):
    user_id: str
    action: str
    units: float
    ref: Optional[str] = None

class QuotaDebitResponse(BaseModel):
    remain: float

class QuotaCreditRequest(BaseModel):
    user_id: str
    action: str
    units: float
    ref: Optional[str] = None

class QuotaCreditResponse(BaseModel):
    remain: float

# Эндпоинты с интеграцией BillingTariffication-Service

@router.get("/billing/quota/check", response_model=QuotaCheckResponse)
async def quota_check(user_id: str = Query(...), action: str = Query(...), units: float = Query(...)):
    """Проверить квоту пользователя"""
    try:
        result = await check_user_quota(user_id, action, units)
        return QuotaCheckResponse(**result)
    except Exception as e:
        # Fallback в случае ошибки сервиса биллинга
        print(f"Error checking quota: {e}")
        return QuotaCheckResponse(allowed=True, remain=100.0)

@router.post("/billing/quota/debit", response_model=QuotaDebitResponse)
async def quota_debit(req: QuotaDebitRequest):
    """Списать квоту пользователя"""
    try:
        result = await debit_user_quota(req.user_id, req.action, req.units, req.ref)
        return QuotaDebitResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при списании квоты: {str(e)}"
        )

@router.post("/billing/quota/credit", response_model=QuotaCreditResponse)
async def quota_credit(req: QuotaCreditRequest):
    """Пополнить квоту пользователя"""
    try:
        result = await credit_user_quota(req.user_id, req.action, req.units, req.ref)
        return QuotaCreditResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при пополнении квоты: {str(e)}"
        )
```

## Шаг 5: Подключение роутера в main.py

В вашем `main.py` добавьте:

```python
from fastapi import FastAPI
from your_billing_router import router as billing_router

app = FastAPI()

# Подключаем роутер биллинга
app.include_router(billing_router, prefix="/api/v1", tags=["billing"])
```

## Шаг 6: Тестирование интеграции

### Запуск сервисов

1. **Запустите BillingTariffication-Service:**
```bash
cd Tarrification-Service
docker-compose up -d
```

2. **Запустите ваш Gateway:**
```bash
cd your-gateway-service
uvicorn main:app --reload --port 8000
```

### Тестирование API

1. **Проверка квоты:**
```bash
curl -X GET "http://localhost:8000/api/v1/billing/quota/check?user_id=test-user&action=chat_message&units=5.0"
```

2. **Пополнение квоты:**
```bash
curl -X POST "http://localhost:8000/api/v1/billing/quota/credit" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test-user","action":"manual_credit","units":100.0}'
```

3. **Списание квоты:**
```bash
curl -X POST "http://localhost:8000/api/v1/billing/quota/debit" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test-user","action":"chat_message","units":2.0}'
```

## Шаг 7: Использование в других сервисах

### Пример для Chat Service:

```python
from fastapi import HTTPException
from uuid import uuid4

async def send_chat_message(user_id: str, message: str):
    # 1. Проверяем квоту через Gateway
    async with httpx.AsyncClient() as client:
        check_response = await client.get(
            "http://localhost:8000/api/v1/billing/quota/check",
            params={
                "user_id": user_id,
                "action": "chat_message",
                "units": 1.0
            }
        )
        
        if check_response.status_code != 200:
            raise HTTPException(status_code=500, detail="Ошибка проверки квоты")
        
        check_data = check_response.json()
        if not check_data["allowed"]:
            raise HTTPException(status_code=403, detail="Недостаточно средств")
    
    # 2. Отправляем сообщение
    try:
        result = await process_chat_message(user_id, message)
        
        # 3. Списываем квоту через Gateway
        debit_response = await client.post(
            "http://localhost:8000/api/v1/billing/quota/debit",
            json={
                "user_id": user_id,
                "action": "chat_message",
                "units": 1.0,
                "ref": f"chat-{uuid4()}"
            }
        )
        
        return {
            "message_id": result["id"],
            "remaining_quota": debit_response.json()["remain"]
        }
    except Exception as e:
        # Если отправка не удалась, квота не списывается
        raise e
```

### Пример для Template Service:

```python
async def generate_template(user_id: str, template_type: str):
    # 1. Определяем стоимость
    costs = {"contract": 10.0, "agreement": 5.0, "letter": 3.0}
    units_needed = costs.get(template_type, 2.0)
    
    # 2. Проверяем квоту через Gateway
    async with httpx.AsyncClient() as client:
        check_response = await client.get(
            "http://localhost:8000/api/v1/billing/quota/check",
            params={
                "user_id": user_id,
                "action": f"template_{template_type}",
                "units": units_needed
            }
        )
        
        if check_response.status_code != 200:
            raise HTTPException(status_code=500, detail="Ошибка проверки квоты")
        
        check_data = check_response.json()
        if not check_data["allowed"]:
            raise HTTPException(status_code=403, detail="Недостаточно средств")
    
    # 3. Генерируем шаблон
    try:
        result = await process_template_generation(user_id, template_type)
        
        # 4. Списываем квоту через Gateway
        debit_response = await client.post(
            "http://localhost:8000/api/v1/billing/quota/debit",
            json={
                "user_id": user_id,
                "action": f"template_{template_type}",
                "units": units_needed,
                "ref": f"template-{uuid4()}"
            }
        )
        
        return {
            "template_id": result["id"],
            "remaining_quota": debit_response.json()["remain"]
        }
    except Exception as e:
        # Если генерация не удалась, квота не списывается
        raise e
```

## Шаг 8: Настройка Docker Compose (опционально)

Если вы используете Docker Compose, добавьте в ваш `docker-compose.yml`:

```yaml
services:
  gateway:
    # ... ваша конфигурация Gateway
    environment:
      - BILLING_SERVICE_URL=http://billing-service:8001
      - BILLING_SERVICE_TOKEN=super-secret-dev
    networks:
      - microservices-network
    depends_on:
      - billing-service

  billing-service:
    image: tarrification-service-billing-service
    ports:
      - "8001:8001"
    environment:
      - DB_DSN=postgresql+asyncpg://billing_user:billing_pass@postgres:5432/billing_db
      - SERVICE_TOKEN=super-secret-dev
    networks:
      - microservices-network
    depends_on:
      - postgres

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=billing_db
      - POSTGRES_USER=billing_user
      - POSTGRES_PASSWORD=billing_pass
    ports:
      - "5456:5432"
    networks:
      - microservices-network

networks:
  microservices-network:
    driver: bridge
```

## Проверка работоспособности

После настройки проверьте:

1. **BillingTariffication-Service работает:**
```bash
curl http://localhost:8001/health
```

2. **Gateway отвечает:**
```bash
curl http://localhost:8000/docs
```

3. **Интеграция работает:**
```bash
curl -X GET "http://localhost:8000/api/v1/billing/quota/check?user_id=test-user&action=test&units=1.0"
```

## Устранение неполадок

### Ошибка подключения к BillingTariffication-Service:
- Проверьте, что сервис запущен на порту 8001
- Проверьте переменную `BILLING_SERVICE_URL`
- Проверьте сеть Docker (если используете)

### Ошибка аутентификации:
- Проверьте переменную `BILLING_SERVICE_TOKEN`
- Убедитесь, что токен совпадает в обоих сервисах

### Ошибка базы данных:
- Проверьте, что PostgreSQL запущен
- Проверьте переменную `DB_DSN`
- Проверьте логи BillingTariffication-Service 