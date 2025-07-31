from fastapi import APIRouter, status, Query, Body, Depends
from pydantic import BaseModel
from typing import Optional
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
    """Проксирует запрос к микросервису billing для проверки квоты"""
    try:
        params = {"user_id": user_id, "action": action, "units": units}
        result = await microservice_client.proxy_request("billing", "GET", "/billing/quota/check", params=params)
        return QuotaCheckResponse(**result)
    except Exception as e:
        # Fallback в случае ошибки сервиса биллинга
        print(f"Error checking quota: {e}")
        return QuotaCheckResponse(allowed=True, remain=100.0)

@router.post("/billing/quota/debit", response_model=QuotaDebitResponse)
async def quota_debit(req: QuotaDebitRequest):
    """Проксирует запрос к микросервису billing для списания квоты"""
    try:
        result = await microservice_client.proxy_request("billing", "POST", "/billing/quota/debit", data=req.dict())
        return QuotaDebitResponse(**result)
    except Exception as e:
        # Пробрасываем ошибки как есть
        raise

@router.post("/billing/quota/credit", response_model=QuotaCreditResponse)
async def quota_credit(req: QuotaCreditRequest):
    """Проксирует запрос к микросервису billing для пополнения квоты"""
    try:
        result = await microservice_client.proxy_request("billing", "POST", "/billing/quota/credit", data=req.dict())
        return QuotaCreditResponse(**result)
    except Exception as e:
        # Пробрасываем ошибки как есть
        raise 