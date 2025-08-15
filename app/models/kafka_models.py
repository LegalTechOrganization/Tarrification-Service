from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

# Kafka Event Models для интеграции с Gateway

class EventStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"

class EventType(str, Enum):
    BALANCE_CHECK = "balance_check"
    DEBIT = "debit"
    CREDIT = "credit"
    PLAN_APPLY = "plan_apply"
    BALANCE_CHECK_RESPONSE = "balance_check_response"
    DEBIT_RESPONSE = "debit_response"
    CREDIT_RESPONSE = "credit_response"
    PLAN_APPLY_RESPONSE = "plan_apply_response"

# User Context Models
class UserContext(BaseModel):
    """Контекст пользователя от Auth Service через Gateway"""
    email: str = Field(..., description="Email пользователя")
    full_name: Optional[str] = Field(None, description="Полное имя пользователя")
    active_org_id: Optional[str] = Field(None, description="ID активной организации")
    org_role: Optional[str] = Field(None, description="Роль в организации")
    is_org_owner: bool = Field(False, description="Является ли владельцем организации")

class RequestMetadata(BaseModel):
    """Метаданные запроса"""
    source_ip: Optional[str] = Field(None, description="IP адрес источника")
    user_agent: Optional[str] = Field(None, description="User Agent")
    gateway_request_id: Optional[str] = Field(None, description="ID запроса в Gateway")
    timestamp: Optional[str] = Field(None, description="Временная метка запроса")

# Incoming Kafka Event Models (Gateway → Billing Service)
class BalanceCheckPayload(BaseModel):
    """Payload для проверки баланса"""
    user_id: str = Field(..., description="ID пользователя")
    action: str = Field(..., description="Тип действия")
    units: float = Field(..., gt=0, description="Количество единиц для проверки")
    user_context: UserContext = Field(..., description="Контекст пользователя")
    request_metadata: Optional[RequestMetadata] = Field(None, description="Метаданные запроса")

class DebitPayload(BaseModel):
    """Payload для списания средств"""
    user_id: str = Field(..., description="ID пользователя")
    action: str = Field(..., description="Тип действия")
    units: float = Field(..., gt=0, description="Количество единиц для списания")
    ref: str = Field(..., description="Внешний ID операции")
    reason: str = Field(..., description="Причина списания")
    user_context: UserContext = Field(..., description="Контекст пользователя")
    operation_context: Optional[Dict[str, Any]] = Field(None, description="Контекст операции")
    request_metadata: Optional[RequestMetadata] = Field(None, description="Метаданные запроса")

class CreditPayload(BaseModel):
    """Payload для пополнения баланса"""
    user_id: str = Field(..., description="ID пользователя")
    action: str = Field(..., description="Тип действия")
    units: float = Field(..., gt=0, description="Количество единиц для пополнения")
    ref: str = Field(..., description="Внешний ID операции")
    reason: str = Field(..., description="Причина пополнения")
    user_context: UserContext = Field(..., description="Контекст пользователя")
    payment_context: Optional[Dict[str, Any]] = Field(None, description="Контекст платежа")
    request_metadata: Optional[RequestMetadata] = Field(None, description="Метаданные запроса")

class PlanApplyPayload(BaseModel):
    """Payload для применения плана"""
    user_id: str = Field(..., description="ID пользователя")
    plan_id: str = Field(..., description="ID тарифного плана")
    user_context: UserContext = Field(..., description="Контекст пользователя")
    plan_context: Optional[Dict[str, Any]] = Field(None, description="Контекст плана")
    request_metadata: Optional[RequestMetadata] = Field(None, description="Метаданные запроса")

# Base Kafka Event Model
class KafkaEvent(BaseModel):
    """Базовая модель Kafka события"""
    message_id: str = Field(..., description="Уникальный ID сообщения")
    request_id: str = Field(..., description="ID запроса для корреляции")
    operation: EventType = Field(..., description="Тип операции")
    timestamp: str = Field(..., description="Временная метка в ISO формате")
    payload: Dict[str, Any] = Field(..., description="Полезная нагрузка события")

# Response Payload Models
class BalanceCheckResponsePayload(BaseModel):
    """Ответ на проверку баланса"""
    allowed: bool = Field(..., description="Достаточно ли средств")
    balance: float = Field(..., description="Текущий баланс")
    quota_info: Optional[Dict[str, Any]] = Field(None, description="Информация о квотах")

class TransactionDetails(BaseModel):
    """Детали транзакции"""
    amount_debited: Optional[float] = Field(None, description="Сумма списания")
    amount_credited: Optional[float] = Field(None, description="Сумма пополнения")
    currency: str = Field(default="credits", description="Валюта")
    timestamp: str = Field(..., description="Временная метка транзакции")
    ref: str = Field(..., description="Внешний ID операции")

class DebitResponsePayload(BaseModel):
    """Ответ на списание средств"""
    balance: float = Field(..., description="Новый баланс")
    tx_id: str = Field(..., description="ID транзакции")
    transaction_details: TransactionDetails = Field(..., description="Детали транзакции")

class CreditResponsePayload(BaseModel):
    """Ответ на пополнение баланса"""
    balance: float = Field(..., description="Новый баланс")
    tx_id: str = Field(..., description="ID транзакции")
    transaction_details: TransactionDetails = Field(..., description="Детали транзакции")

class PlanDetails(BaseModel):
    """Детали примененного плана"""
    name: str = Field(..., description="Название плана")
    billing_cycle: Optional[str] = Field(None, description="Биллинговый цикл")
    effective_date: str = Field(..., description="Дата вступления в силу")
    expires_at: Optional[str] = Field(None, description="Дата истечения")

class CreditAdjustment(BaseModel):
    """Корректировка кредитов"""
    prorated_amount: float = Field(..., description="Пропорциональная сумма")
    tx_id: str = Field(..., description="ID транзакции корректировки")

class PlanApplyResponsePayload(BaseModel):
    """Ответ на применение плана"""
    plan_id: str = Field(..., description="ID примененного плана")
    new_balance: float = Field(..., description="Новый баланс")
    plan_details: PlanDetails = Field(..., description="Детали плана")
    credit_adjustment: Optional[CreditAdjustment] = Field(None, description="Корректировка кредитов")

# Response Event Model
class KafkaResponse(BaseModel):
    """Модель ответа в Kafka"""
    message_id: str = Field(..., description="Уникальный ID ответа")
    request_id: str = Field(..., description="ID оригинального запроса")
    operation: EventType = Field(..., description="Тип операции ответа")
    timestamp: str = Field(..., description="Временная метка ответа")
    status: EventStatus = Field(..., description="Статус обработки")
    payload: Optional[Dict[str, Any]] = Field(None, description="Полезная нагрузка ответа")
    error: Optional[str] = Field(None, description="Сообщение об ошибке при status=error")

# Audit Event Models для отправки в billing-events топик
class AuditEventType(str, Enum):
    BALANCE_CHECK_REQUESTED = "balance_check_requested"
    DEBIT_PROCESSED = "debit_processed"
    CREDIT_PROCESSED = "credit_processed"
    PLAN_APPLIED = "plan_applied"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    USER_NOT_FOUND = "user_not_found"
    VALIDATION_ERROR = "validation_error"

class AuditEventData(BaseModel):
    """Данные для аудит события"""
    user_id: str = Field(..., description="ID пользователя")
    org_id: Optional[str] = Field(None, description="ID организации")
    action: Optional[str] = Field(None, description="Тип действия")
    amount: Optional[float] = Field(None, description="Сумма операции")
    balance_before: Optional[float] = Field(None, description="Баланс до операции")
    balance_after: Optional[float] = Field(None, description="Баланс после операции")
    tx_id: Optional[str] = Field(None, description="ID транзакции")
    ref: Optional[str] = Field(None, description="Внешняя ссылка")
    reason: Optional[str] = Field(None, description="Причина операции")
    plan_id: Optional[str] = Field(None, description="ID плана")
    error_details: Optional[str] = Field(None, description="Детали ошибки")

class AuditEvent(BaseModel):
    """Событие для аудита"""
    event_type: AuditEventType = Field(..., description="Тип аудит события")
    timestamp: float = Field(..., description="Unix timestamp")
    data: AuditEventData = Field(..., description="Данные события")
