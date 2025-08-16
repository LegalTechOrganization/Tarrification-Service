# Инициализация пользователя

## Обзор

Сервис тарификации предоставляет endpoints для инициализации новых пользователей с дефолтными данными. При первом обращении пользователя к сервису необходимо создать базовые записи в таблицах.

## Endpoints

### 1. Инициализация пользователя

**POST** `/internal/billing/user/init`

Инициализирует пользователя с дефолтными данными.

#### Запрос

```json
{
  "auth_context": {
    "user": {
      "sub": "unique-user-id-from-jwt",
      "email": "user@example.com",
      "full_name": "User Name",
      "orgs": [],
      "active_org_id": null
    },
    "jwt_payload": {...},
    "token_valid": true
  }
}
```

#### Ответ

```json
{
  "success": true,
  "user_id": "unique-user-id-from-jwt",
  "balance_created": true,
  "initial_balance": 0.0,
  "message": "User initialized successfully with initial balance: 0.0"
}
```

#### Возможные ответы

- **200 OK** - Пользователь успешно инициализирован
- **401 Unauthorized** - Неверный токен аутентификации
- **500 Internal Server Error** - Ошибка сервера

### 2. Получение статуса пользователя

**GET** `/internal/billing/user/status`

Возвращает текущий статус инициализации пользователя.

#### Заголовки

```
X-User-Data: {"jwt_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...", "user_data": {...}}
```

#### Ответ

```json
{
  "sub": "unique-user-id-from-jwt",
  "balance_exists": true,
  "balance_amount": 0.0,
  "has_active_plan": false,
  "active_plan_code": null,
  "is_initialized": true
}
```

## Логика работы

### Инициализация пользователя

1. **Проверка существования** - Проверяется, существует ли уже баланс для данного `sub`
2. **Создание баланса** - Если баланс не существует, создается новая запись с дефолтным значением (0.0)
3. **Идемпотентность** - Повторные вызовы не создают дублирующие записи

### Дефолтные значения

- **Баланс**: 0.0 единиц
- **План**: Не назначается автоматически
- **Другие настройки**: Могут быть добавлены в будущем

## Примеры использования

### Инициализация нового пользователя

```bash
curl -X POST "http://localhost:8001/internal/billing/user/init" \
  -H "Content-Type: application/json" \
  -H "X-User-Data: {\"jwt_token\":\"eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...\",\"user_data\":{}}" \
  -d '{
    "auth_context": {
      "user": {
        "sub": "user-123",
        "email": "user@example.com",
        "full_name": "Test User"
      },
      "token_valid": true
    }
  }'
```

### Проверка статуса

```bash
curl -X GET "http://localhost:8001/internal/billing/user/status" \
  -H "X-User-Data: {\"jwt_token\":\"eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...\",\"user_data\":{}}"
```

## Интеграция с Gateway

Gateway должен передавать JWT токен в заголовке `X-User-Data` в формате:

```json
{
  "jwt_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user_data": {
    "email": "user@example.com",
    "full_name": "User Name",
    "orgs": [],
    "active_org_id": null
  }
}
```

Сервис автоматически извлекает `sub` из JWT токена и использует его для идентификации пользователя.

## Обработка ошибок

### Пользователь уже инициализирован

Если пользователь уже инициализирован, endpoint вернет:

```json
{
  "success": true,
  "user_id": "user-123",
  "balance_created": false,
  "initial_balance": 100.0,
  "message": "User already initialized. Current balance: 100.0"
}
```

### Ошибки аутентификации

- **401 Unauthorized** - Неверный или отсутствующий JWT токен
- **401 Unauthorized** - Отсутствует поле `sub` в JWT токене

### Ошибки сервера

- **500 Internal Server Error** - Ошибки базы данных или другие внутренние ошибки

