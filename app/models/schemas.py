from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# Gateway Request schemas (для внешних запросов)
class GatewayCheckBalanceRequest(BaseModel):
    user_id: str = Field(..., description="ID пользователя")
    action: str = Field(..., description="Тип действия")
    units: float = Field(..., gt=0, description="Количество единиц для проверки")

class GatewayDebitRequest(BaseModel):
    user_id: str = Field(..., description="ID пользователя")
    action: str = Field(..., description="Тип действия")
    units: float = Field(..., gt=0, description="Количество единиц для списания")
    ref: Optional[str] = Field(None, description="Внешний ID операции")
    reason: str = Field(..., description="Причина списания")

class GatewayCreditRequest(BaseModel):
    user_id: str = Field(..., description="ID пользователя")
    action: str = Field(..., description="Тип действия")
    units: float = Field(..., gt=0, description="Количество единиц для пополнения")
    ref: Optional[str] = Field(None, description="Внешний ID операции")
    source_service: Optional[str] = Field(None, description="Сервис-источник")
    reason: str = Field(..., description="Причина пополнения")

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
    plan_id: str = Field(..., description="ID тарифного плана")
    ref: Optional[str] = Field(None, description="ID платежа/заказа")
    auto_renew: bool = Field(False, description="Автопродление")

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