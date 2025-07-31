# Интеграция Gateway с BillingTariffication-Service

## Обзор

BillingTariffication-Service предоставляет внутренние REST API для управления балансом пользователей. Gateway должен обращаться к этим эндпоинтам для проверки и списания средств.

## Конфигурация

### Переменные окружения для Gateway

```env
BILLING_SERVICE_URL=http://localhost:8001
BILLING_SERVICE_TOKEN=super-secret-dev
```

## API Эндпоинты

### 1. Проверка баланса (Pre-check)

**Эндпоинт:** `POST /internal/billing/check`

**Запрос:**
```json
{
    "user_id": "11111111-1111-1111-1111-111111111111",
    "units": 2.0
}
```

**Ответ:**
```json
{
    "allowed": true,
    "balance": 742.0
}
```

**Использование в Gateway:**
```python
# Пример для Python Gateway
import httpx

async def check_user_balance(user_id: str, units: float) -> bool:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BILLING_SERVICE_URL}/internal/billing/check",
            json={"user_id": user_id, "units": units},
            headers={"X-Internal-Key": BILLING_SERVICE_TOKEN}
        )
        
        if response.status_code == 200:
            data = response.json()
            return data["allowed"]
        else:
            raise Exception(f"Billing check failed: {response.text}")
```

### 2. Списание средств

**Эндпоинт:** `POST /internal/billing/debit`

**Запрос:**
```json
{
    "user_id": "11111111-1111-1111-1111-111111111111",
    "units": 2.0,
    "ref": "req-876c9a1234567890",
    "reason": "chat_message"
}
```

**Ответ:**
```json
{
    "balance": 740.0,
    "tx_id": "b2b2b2b2-b2b2-b2b2-b2b2-b2b2b2b2b2b2"
}
```

**Использование в Gateway:**
```python
async def debit_user_balance(user_id: str, units: float, ref: str, reason: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BILLING_SERVICE_URL}/internal/billing/debit",
            json={
                "user_id": user_id,
                "units": units,
                "ref": ref,
                "reason": reason
            },
            headers={"X-Internal-Key": BILLING_SERVICE_TOKEN}
        )
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 403:
            raise InsufficientFundsError("Недостаточно средств")
        elif response.status_code == 409:
            raise DuplicateTransactionError("Транзакция уже существует")
        else:
            raise Exception(f"Billing debit failed: {response.text}")
```

### 3. Получение баланса

**Эндпоинт:** `GET /internal/billing/balance?user_id=<uuid>`

**Ответ:**
```json
{
    "balance": 742.0,
    "plan": {
        "plan_code": "base750",
        "expires_at": "2025-07-31T10:00:00Z",
        "status": "active"
    }
}
```

**Использование в Gateway:**
```python
async def get_user_balance(user_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BILLING_SERVICE_URL}/internal/billing/balance",
            params={"user_id": user_id},
            headers={"X-Internal-Key": BILLING_SERVICE_TOKEN}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get balance: {response.text}")
```

## Типичные сценарии использования

### Сценарий 1: Отправка сообщения в чате

```python
async def send_chat_message(user_id: str, message: str):
    # 1. Проверяем баланс
    units_needed = calculate_message_cost(message)
    has_funds = await check_user_balance(user_id, units_needed)
    
    if not has_funds:
        raise InsufficientFundsError("Недостаточно средств для отправки сообщения")
    
    # 2. Выполняем операцию
    try:
        result = await process_chat_message(user_id, message)
        
        # 3. Списываем средства
        ref = f"chat-{generate_request_id()}"
        await debit_user_balance(user_id, units_needed, ref, "chat_message")
        
        return result
    except Exception as e:
        # Если операция не удалась, средства не списываются
        raise e
```

### Сценарий 2: Генерация шаблона

```python
async def generate_template(user_id: str, template_type: str):
    # 1. Проверяем баланс
    units_needed = get_template_cost(template_type)
    has_funds = await check_user_balance(user_id, units_needed)
    
    if not has_funds:
        raise InsufficientFundsError("Недостаточно средств для генерации шаблона")
    
    # 2. Выполняем операцию
    try:
        result = await process_template_generation(user_id, template_type)
        
        # 3. Списываем средства
        ref = f"template-{generate_request_id()}"
        await debit_user_balance(user_id, units_needed, ref, "template_generation")
        
        return result
    except Exception as e:
        # Если операция не удалась, средства не списываются
        raise e
```

## Обработка ошибок

### Коды ошибок

- **401 Unauthorized**: Неверный `X-Internal-Key`
- **403 Forbidden**: Недостаточно средств (при debit)
- **409 Conflict**: Дублирование транзакции (idempotency)
- **422 Unprocessable Entity**: Некорректные данные запроса
- **404 Not Found**: План не найден (при apply_plan)
- **500 Internal Server Error**: Внутренняя ошибка сервиса

### Пример обработки ошибок в Gateway

```python
class BillingServiceError(Exception):
    pass

class InsufficientFundsError(BillingServiceError):
    pass

class DuplicateTransactionError(BillingServiceError):
    pass

async def handle_billing_request(method: str, url: str, **kwargs):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                f"{BILLING_SERVICE_URL}{url}",
                headers={"X-Internal-Key": BILLING_SERVICE_TOKEN},
                **kwargs
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                raise InsufficientFundsError("Недостаточно средств")
            elif response.status_code == 409:
                raise DuplicateTransactionError("Транзакция уже существует")
            elif response.status_code == 401:
                raise BillingServiceError("Ошибка аутентификации")
            else:
                raise BillingServiceError(f"Ошибка сервиса: {response.text}")
                
    except httpx.RequestError as e:
        raise BillingServiceError(f"Ошибка соединения: {e}")
```

## Настройка в Docker Compose

Если Gateway и BillingTariffication-Service работают в одной Docker сети:

```yaml
# docker-compose.yml для Gateway
services:
  gateway:
    # ... конфигурация Gateway
    environment:
      - BILLING_SERVICE_URL=http://billing-service:8001
      - BILLING_SERVICE_TOKEN=super-secret-dev
    networks:
      - microservices-network

networks:
  microservices-network:
    external: true
```

## Тестирование интеграции

```python
# test_gateway_billing_integration.py
import pytest
import httpx

@pytest.mark.asyncio
async def test_billing_integration():
    # Тест проверки баланса
    response = await httpx.post(
        "http://localhost:8001/internal/billing/check",
        json={"user_id": "test-user", "units": 1.0},
        headers={"X-Internal-Key": "super-secret-dev"}
    )
    assert response.status_code == 200
    
    # Тест списания средств
    response = await httpx.post(
        "http://localhost:8001/internal/billing/debit",
        json={
            "user_id": "test-user",
            "units": 1.0,
            "ref": "test-ref-123",
            "reason": "test"
        },
        headers={"X-Internal-Key": "super-secret-dev"}
    )
    assert response.status_code == 200
``` 