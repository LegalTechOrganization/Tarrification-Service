"""
Пример Gateway с интеграцией BillingTariffication-Service
"""
from fastapi import APIRouter, status, Query, Body, HTTPException
from pydantic import BaseModel
from typing import Optional
import os

# Импортируем функции для работы с биллингом
from gateway_billing_client import check_user_quota, debit_user_quota, credit_user_quota

router = APIRouter()

# Pydantic модели для Gateway API
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

# Gateway эндпоинты с интеграцией BillingTariffication-Service

@router.get("/billing/quota/check", response_model=QuotaCheckResponse)
async def quota_check(user_id: str = Query(...), action: str = Query(...), units: float = Query(...)):
    """
    Проверить квоту пользователя
    
    Args:
        user_id: ID пользователя
        action: Тип действия (например: "chat_message", "template_generation")
        units: Количество единиц для проверки
        
    Returns:
        QuotaCheckResponse с полями allowed и remain
    """
    try:
        result = await check_user_quota(user_id, action, units)
        return QuotaCheckResponse(**result)
    except Exception as e:
        # Fallback в случае ошибки сервиса биллинга
        print(f"Error checking quota: {e}")
        return QuotaCheckResponse(allowed=True, remain=100.0)

@router.post("/billing/quota/debit", response_model=QuotaDebitResponse)
async def quota_debit(req: QuotaDebitRequest):
    """
    Списать квоту пользователя
    
    Args:
        req: QuotaDebitRequest с данными для списания
        
    Returns:
        QuotaDebitResponse с оставшимся балансом
        
    Raises:
        HTTPException: При недостатке средств или ошибке сервиса
    """
    try:
        result = await debit_user_quota(req.user_id, req.action, req.units, req.ref)
        return QuotaDebitResponse(**result)
    except HTTPException:
        # Пробрасываем HTTPException как есть
        raise
    except Exception as e:
        # Обрабатываем другие ошибки
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при списании квоты: {str(e)}"
        )

@router.post("/billing/quota/credit", response_model=QuotaCreditResponse)
async def quota_credit(req: QuotaCreditRequest):
    """
    Пополнить квоту пользователя
    
    Args:
        req: QuotaCreditRequest с данными для пополнения
        
    Returns:
        QuotaCreditResponse с новым балансом
        
    Raises:
        HTTPException: При ошибке сервиса
    """
    try:
        result = await credit_user_quota(req.user_id, req.action, req.units, req.ref)
        return QuotaCreditResponse(**result)
    except HTTPException:
        # Пробрасываем HTTPException как есть
        raise
    except Exception as e:
        # Обрабатываем другие ошибки
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при пополнении квоты: {str(e)}"
        )

# Дополнительные эндпоинты для работы с биллингом

@router.get("/billing/balance/{user_id}")
async def get_user_balance(user_id: str):
    """
    Получить баланс пользователя (дополнительный эндпоинт)
    
    Args:
        user_id: ID пользователя
        
    Returns:
        Информация о балансе и плане пользователя
    """
    from gateway_billing_client import billing_client
    
    try:
        balance_info = await billing_client.get_balance(user_id)
        return {
            "user_id": user_id,
            "balance": balance_info.get("balance", 0.0),
            "plan": balance_info.get("plan"),
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении баланса: {str(e)}"
        )

# Примеры использования в других сервисах

"""
# В Chat Service:
async def send_chat_message(user_id: str, message: str):
    # 1. Проверяем квоту
    check_response = await quota_check(user_id, "chat_message", 1.0)
    if not check_response.allowed:
        raise HTTPException(status_code=403, detail="Недостаточно средств")
    
    # 2. Отправляем сообщение
    try:
        result = await process_chat_message(user_id, message)
        
        # 3. Списываем квоту
        debit_response = await quota_debit(QuotaDebitRequest(
            user_id=user_id,
            action="chat_message",
            units=1.0,
            ref=f"chat-{uuid4()}"
        ))
        
        return {
            "message_id": result["id"],
            "remaining_quota": debit_response.remain
        }
    except Exception as e:
        # Если отправка не удалась, квота не списывается
        raise e

# В Template Service:
async def generate_template(user_id: str, template_type: str):
    # 1. Определяем стоимость
    costs = {"contract": 10.0, "agreement": 5.0, "letter": 3.0}
    units_needed = costs.get(template_type, 2.0)
    
    # 2. Проверяем квоту
    check_response = await quota_check(user_id, f"template_{template_type}", units_needed)
    if not check_response.allowed:
        raise HTTPException(status_code=403, detail="Недостаточно средств")
    
    # 3. Генерируем шаблон
    try:
        result = await process_template_generation(user_id, template_type)
        
        # 4. Списываем квоту
        debit_response = await quota_debit(QuotaDebitRequest(
            user_id=user_id,
            action=f"template_{template_type}",
            units=units_needed,
            ref=f"template-{uuid4()}"
        ))
        
        return {
            "template_id": result["id"],
            "remaining_quota": debit_response.remain
        }
    except Exception as e:
        # Если генерация не удалась, квота не списывается
        raise e
"""

# Конфигурация для Gateway

"""
# В .env файле Gateway добавьте:
BILLING_SERVICE_URL=http://localhost:8001
BILLING_SERVICE_TOKEN=super-secret-dev

# В main.py Gateway добавьте:
from examples.gateway_with_billing import router as billing_router

app.include_router(billing_router, prefix="/api/v1", tags=["billing"])
""" 