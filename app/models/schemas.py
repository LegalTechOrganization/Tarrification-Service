from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# Auth models (для данных от Gateway на основе Auth Service)
class UserOrganization(BaseModel):
    """Организация пользователя"""
    org_id: str = Field(..., description="ID организации")
    name: str = Field(..., description="Название организации")
    role: str = Field(..., description="Роль пользователя в организации")

class AuthUser(BaseModel):
    """Данные пользователя из Auth Service через Gateway"""
    user_id: str = Field(..., description="ID пользователя")
    email: str = Field(..., description="Email пользователя")
    full_name: Optional[str] = Field(None, description="Полное имя пользователя")
    orgs: List[UserOrganization] = Field(default_factory=list, description="Организации пользователя")
    active_org_id: Optional[str] = Field(None, description="ID активной организации")

class GatewayAuthContext(BaseModel):
    """Контекст аутентификации от Gateway"""
    user: AuthUser = Field(..., description="Данные пользователя")
    jwt_payload: Optional[dict] = Field(None, description="Полезная нагрузка JWT токена")
    token_valid: bool = Field(True, description="Токен валиден")

# Gateway Request schemas (для внешних запросов от Gateway)
class GatewayCheckBalanceRequest(BaseModel):
    # Данные операции
    action: str = Field(..., description="Тип действия")
    units: float = Field(..., gt=0, description="Количество единиц для проверки")
    # Контекст аутентификации от Gateway
    auth_context: GatewayAuthContext = Field(..., description="Данные пользователя от Auth Service")

class GatewayDebitRequest(BaseModel):
    # Данные операции  
    action: str = Field(..., description="Тип действия")
    units: float = Field(..., gt=0, description="Количество единиц для списания")
    ref: Optional[str] = Field(None, description="Внешний ID операции")
    reason: str = Field(..., description="Причина списания")
    # Контекст аутентификации от Gateway
    auth_context: GatewayAuthContext = Field(..., description="Данные пользователя от Auth Service")

class GatewayCreditRequest(BaseModel):
    # Данные операции
    action: str = Field(..., description="Тип действия")
    units: float = Field(..., gt=0, description="Количество единиц для пополнения")
    ref: Optional[str] = Field(None, description="Внешний ID операции")
    source_service: Optional[str] = Field(None, description="Сервис-источник")
    reason: str = Field(..., description="Причина пополнения")
    # Контекст аутентификации от Gateway
    auth_context: GatewayAuthContext = Field(..., description="Данные пользователя от Auth Service")

# Internal Request schemas (для внутренней логики)
class CheckBalanceRequest(BaseModel):
    user_id: str = Field(..., description="ID пользователя")
    units: float = Field(..., gt=0, description="Количество единиц для проверки")

class DebitRequest(BaseModel):
    user_id: str = Field(..., description="ID пользователя")
    units: float = Field(..., gt=0, description="Количество единиц для списания")
    ref: str = Field(..., description="Внешний ID операции")
    reason: str = Field(..., description="Причина списания")

class CreditRequest(BaseModel):
    user_id: str = Field(..., description="ID пользователя")
    units: float = Field(..., gt=0, description="Количество единиц для пополнения")
    ref: str = Field(..., description="Внешний ID операции")
    source_service: Optional[str] = Field(None, description="Сервис-источник")
    reason: str = Field(..., description="Причина пополнения")

class ApplyPlanRequest(BaseModel):
    user_id: str = Field(..., description="ID пользователя")
    plan_code: str = Field(..., description="Код тарифного плана")
    ref: Optional[str] = Field(None, description="ID платежа/заказа")
    auto_renew: bool = Field(False, description="Автопродление")

# Gateway schemas с аутентификацией
class GatewayApplyPlanRequest(BaseModel):
    plan_code: str = Field(..., description="Код тарифного плана")
    ref: Optional[str] = Field(None, description="ID платежа/заказа")
    auto_renew: bool = Field(False, description="Автопродление")
    # Контекст аутентификации от Gateway
    auth_context: GatewayAuthContext = Field(..., description="Данные пользователя от Auth Service")

class GatewayGetBalanceRequest(BaseModel):
    # Контекст аутентификации от Gateway
    auth_context: GatewayAuthContext = Field(..., description="Данные пользователя от Auth Service")

# Response schemas
class CheckBalanceResponse(BaseModel):
    allowed: bool = Field(..., description="Достаточно ли средств")
    balance: float = Field(..., description="Текущий баланс")

class DebitResponse(BaseModel):
    balance: float = Field(..., description="Новый баланс")
    tx_id: str = Field(..., description="ID транзакции")

class CreditResponse(BaseModel):
    balance: float = Field(..., description="Новый баланс")
    tx_id: str = Field(..., description="ID транзакции")

class BalanceResponse(BaseModel):
    balance: float = Field(..., description="Текущий баланс")
    plan: dict = Field(..., description="Информация о плане")

class ApplyPlanResponse(BaseModel):
    plan_id: str = Field(..., description="ID плана")
    new_balance: float = Field(..., description="Новый баланс")

class ErrorResponse(BaseModel):
    code: str = Field(..., description="Код ошибки")
    detail: str = Field(..., description="Описание ошибки")

class HealthResponse(BaseModel):
    status: str = Field(..., description="Статус сервиса")
    version: str = Field(..., description="Версия сервиса")

# Gateway API schemas
class QuotaCheckResponse(BaseModel):
    allowed: bool = Field(..., description="Достаточно ли средств")
    remain: float = Field(..., description="Оставшийся баланс")

class QuotaDebitRequest(BaseModel):
    user_id: str = Field(..., description="ID пользователя")
    action: str = Field(..., description="Тип действия")
    units: float = Field(..., gt=0, description="Количество единиц для списания")
    ref: Optional[str] = Field(None, description="Внешний ID операции")

class QuotaDebitResponse(BaseModel):
    remain: float = Field(..., description="Оставшийся баланс")

class QuotaCreditRequest(BaseModel):
    user_id: str = Field(..., description="ID пользователя")
    action: str = Field(..., description="Тип действия")
    units: float = Field(..., gt=0, description="Количество единиц для пополнения")
    ref: Optional[str] = Field(None, description="Внешний ID операции")

class QuotaCreditResponse(BaseModel):
    remain: float = Field(..., description="Новый баланс")

# Payment schemas (для интеграции с ЮKassa через Pay-Service)
class PaymentWebhookRequest(BaseModel):
    payment_id: str = Field(..., description="ID платежа в ЮKassa")
    user_id: str = Field(..., description="ID пользователя")
    amount: float = Field(..., gt=0, description="Сумма платежа")
    currency: str = Field(default="RUB", description="Валюта платежа")
    payment_status: str = Field(..., description="Статус платежа (succeeded, pending, canceled)")
    plan_code: Optional[str] = Field(None, description="Код тарифного плана (если покупка плана)")
    auto_renew: bool = Field(False, description="Автопродление плана")
    metadata: Optional[dict] = Field(None, description="Дополнительные данные")

class PaymentWebhookResponse(BaseModel):
    success: bool = Field(..., description="Успешность обработки")
    new_balance: float = Field(..., description="Новый баланс пользователя")
    tx_id: Optional[str] = Field(None, description="ID транзакции")
    plan_id: Optional[str] = Field(None, description="ID примененного плана")
    message: str = Field(..., description="Сообщение о результате")

class CreatePaymentRequest(BaseModel):
    user_id: str = Field(..., description="ID пользователя")
    amount: float = Field(..., gt=0, description="Сумма платежа")
    currency: str = Field(default="RUB", description="Валюта платежа")
    plan_code: Optional[str] = Field(None, description="Код тарифного плана")
    description: str = Field(..., description="Описание платежа")
    return_url: str = Field(..., description="URL для возврата после оплаты")
    auto_renew: bool = Field(False, description="Автопродление плана")

class CreatePaymentResponse(BaseModel):
    payment_id: str = Field(..., description="ID платежа")
    payment_url: str = Field(..., description="URL для оплаты")
    amount: float = Field(..., description="Сумма платежа")
    currency: str = Field(..., description="Валюта платежа")
    status: str = Field(..., description="Статус платежа") 