from fastapi import APIRouter, status, Query, Body, Depends
from pydantic import BaseModel
from typing import Optional
from uuid import uuid4
from gateway_microservice_client import microservice_client

router = APIRouter()

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

@router.get("/billing/quota/check", response_model=QuotaCheckResponse)
async def quota_check(user_id: str = Query(...), action: str = Query(...), units: float = Query(...)):
    """
    Проверить квоту пользователя
    Проксирует запрос к внутреннему эндпоинту BillingTariffication-Service
    """
    try:
        # Получаем баланс пользователя через внутренний эндпоинт
        balance_result = await microservice_client.proxy_request(
            "billing", "GET", "/internal/billing/balance", 
            params={"user_id": user_id}
        )
        
        current_balance = balance_result.get("balance", 0.0)
        allowed = current_balance >= units
        
        return QuotaCheckResponse(allowed=allowed, remain=current_balance)
        
    except Exception as e:
        # Fallback в случае ошибки сервиса биллинга
        print(f"Error checking quota: {e}")
        return QuotaCheckResponse(allowed=True, remain=100.0)

@router.post("/billing/quota/debit", response_model=QuotaDebitResponse)
async def quota_debit(req: QuotaDebitRequest):
    """
    Списать квоту пользователя
    Проксирует запрос к внутреннему эндпоинту списания BillingTariffication-Service
    """
    try:
        # Генерируем ref если не передан
        ref = req.ref or f"{req.action}-{uuid4()}"
        
        # Списываем средства через внутренний эндпоинт
        debit_result = await microservice_client.proxy_request(
            "billing", "POST", "/internal/billing/debit",
            data={
                "user_id": req.user_id,
                "units": req.units,
                "ref": ref,
                "reason": req.action
            }
        )
        
        return QuotaDebitResponse(remain=debit_result["balance"])
        
    except Exception as e:
        # Пробрасываем ошибки как есть
        raise

@router.post("/billing/quota/credit", response_model=QuotaCreditResponse)
async def quota_credit(req: QuotaCreditRequest):
    """
    Пополнить квоту пользователя
    Проксирует запрос к внутреннему эндпоинту пополнения BillingTariffication-Service
    """
    try:
        # Генерируем ref если не передан
        ref = req.ref or f"{req.action}-{uuid4()}"
        
        # Пополняем баланс через внутренний эндпоинт
        credit_result = await microservice_client.proxy_request(
            "billing", "POST", "/internal/billing/credit",
            data={
                "user_id": req.user_id,
                "units": req.units,
                "ref": ref,
                "reason": req.action,
                "source_service": "gateway"
            }
        )
        
        return QuotaCreditResponse(remain=credit_result["balance"])
        
    except Exception as e:
        # Пробрасываем ошибки как есть
        raise 