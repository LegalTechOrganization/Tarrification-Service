"""
Клиент для Gateway, который обращается к BillingTariffication-Service
"""
import httpx
import asyncio
from typing import Optional, Dict, Any
from uuid import uuid4
import os
from fastapi import HTTPException

class BillingServiceError(Exception):
    """Базовый класс для ошибок сервиса биллинга"""
    pass

class InsufficientFundsError(BillingServiceError):
    """Недостаточно средств"""
    pass

class BillingServiceClient:
    """Клиент для работы с BillingTariffication-Service"""
    
    def __init__(self, base_url: str = None, token: str = None):
        self.base_url = base_url or os.getenv("BILLING_SERVICE_URL", "http://localhost:8001")
        self.token = token or os.getenv("BILLING_SERVICE_TOKEN", "super-secret-dev")
        self.headers = {"X-Internal-Key": self.token}
    
    async def check_balance(self, user_id: str, units: float) -> Dict[str, Any]:
        """
        Проверить достаточно ли средств у пользователя
        
        Args:
            user_id: ID пользователя
            units: Количество единиц для проверки
            
        Returns:
            Dict с полями allowed (bool) и balance (float)
            
        Raises:
            BillingServiceError: При ошибке сервиса
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/internal/billing/check",
                    json={"user_id": user_id, "units": units},
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    raise BillingServiceError(f"Check balance failed: {response.text}")
                    
            except httpx.RequestError as e:
                raise BillingServiceError(f"Connection error: {e}")
    
    async def debit_balance(self, user_id: str, units: float, ref: str, reason: str) -> Dict[str, Any]:
        """
        Списать средства с баланса пользователя
        
        Args:
            user_id: ID пользователя
            units: Количество единиц для списания
            ref: Внешний ID операции (для идемпотентности)
            reason: Причина списания
            
        Returns:
            Dict с полями balance (float) и tx_id (str)
            
        Raises:
            InsufficientFundsError: При недостатке средств
            BillingServiceError: При других ошибках
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/internal/billing/debit",
                    json={
                        "user_id": user_id,
                        "units": units,
                        "ref": ref,
                        "reason": reason
                    },
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 403:
                    raise InsufficientFundsError("Недостаточно средств")
                else:
                    raise BillingServiceError(f"Debit failed: {response.text}")
                    
            except httpx.RequestError as e:
                raise BillingServiceError(f"Connection error: {e}")
    
    async def credit_balance(self, user_id: str, units: float, ref: str, reason: str, source_service: str = None) -> Dict[str, Any]:
        """
        Пополнить баланс пользователя
        
        Args:
            user_id: ID пользователя
            units: Количество единиц для пополнения
            ref: Внешний ID операции (для идемпотентности)
            reason: Причина пополнения
            source_service: Сервис-источник
            
        Returns:
            Dict с полями balance (float) и tx_id (str)
            
        Raises:
            BillingServiceError: При ошибке сервиса
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/internal/billing/credit",
                    json={
                        "user_id": user_id,
                        "units": units,
                        "ref": ref,
                        "reason": reason,
                        "source_service": source_service
                    },
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    raise BillingServiceError(f"Credit failed: {response.text}")
                    
            except httpx.RequestError as e:
                raise BillingServiceError(f"Connection error: {e}")
    
    async def get_balance(self, user_id: str) -> Dict[str, Any]:
        """
        Получить текущий баланс пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Dict с полями balance (float) и plan (dict)
            
        Raises:
            BillingServiceError: При ошибке сервиса
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/internal/billing/balance",
                    params={"user_id": user_id},
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    raise BillingServiceError(f"Get balance failed: {response.text}")
                    
            except httpx.RequestError as e:
                raise BillingServiceError(f"Connection error: {e}")

# Глобальный экземпляр клиента
billing_client = BillingServiceClient()

# Функции для использования в Gateway эндпоинтах

async def check_user_quota(user_id: str, action: str, units: float) -> Dict[str, Any]:
    """
    Проверить квоту пользователя (для Gateway эндпоинта /billing/quota/check)
    
    Args:
        user_id: ID пользователя
        action: Тип действия (для логирования)
        units: Количество единиц для проверки
        
    Returns:
        Dict с полями allowed (bool) и remain (float)
    """
    try:
        # Получаем текущий баланс
        balance_info = await billing_client.get_balance(user_id)
        current_balance = balance_info.get("balance", 0.0)
        
        # Проверяем достаточно ли средств
        allowed = current_balance >= units
        
        return {
            "allowed": allowed,
            "remain": current_balance
        }
        
    except BillingServiceError as e:
        # В случае ошибки считаем, что средств достаточно (fallback)
        print(f"Billing service error during quota check: {e}")
        return {
            "allowed": True,
            "remain": 100.0  # Fallback значение
        }

async def debit_user_quota(user_id: str, action: str, units: float, ref: Optional[str] = None) -> Dict[str, Any]:
    """
    Списать квоту пользователя (для Gateway эндпоинта /billing/quota/debit)
    
    Args:
        user_id: ID пользователя
        action: Тип действия
        units: Количество единиц для списания
        ref: Внешний ID операции (опционально)
        
    Returns:
        Dict с полем remain (float)
        
    Raises:
        HTTPException: При недостатке средств или ошибке сервиса
    """
    try:
        # Генерируем ref если не передан
        if not ref:
            ref = f"{action}-{uuid4()}"
        
        # Списываем средства
        debit_result = await billing_client.debit_balance(
            user_id=user_id,
            units=units,
            ref=ref,
            reason=action
        )
        
        return {
            "remain": debit_result["balance"]
        }
        
    except InsufficientFundsError:
        raise HTTPException(
            status_code=403,
            detail="Недостаточно средств для выполнения операции"
        )
    except BillingServiceError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка сервиса биллинга: {str(e)}"
        )

async def credit_user_quota(user_id: str, action: str, units: float, ref: Optional[str] = None) -> Dict[str, Any]:
    """
    Пополнить квоту пользователя (для Gateway эндпоинта /billing/quota/credit)
    
    Args:
        user_id: ID пользователя
        action: Тип действия
        units: Количество единиц для пополнения
        ref: Внешний ID операции (опционально)
        
    Returns:
        Dict с полем remain (float)
        
    Raises:
        HTTPException: При ошибке сервиса
    """
    try:
        # Генерируем ref если не передан
        if not ref:
            ref = f"{action}-{uuid4()}"
        
        # Пополняем баланс
        credit_result = await billing_client.credit_balance(
            user_id=user_id,
            units=units,
            ref=ref,
            reason=action,
            source_service="gateway"
        )
        
        return {
            "remain": credit_result["balance"]
        }
        
    except BillingServiceError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка сервиса биллинга: {str(e)}"
        )

# Пример использования в Gateway

"""
# В вашем Gateway файле добавьте:

from examples.gateway_billing_client import check_user_quota, debit_user_quota, credit_user_quota

@router.get("/billing/quota/check", response_model=QuotaCheckResponse)
async def quota_check(user_id: str = Query(...), action: str = Query(...), units: float = Query(...)):
    result = await check_user_quota(user_id, action, units)
    return QuotaCheckResponse(**result)

@router.post("/billing/quota/debit", response_model=QuotaDebitResponse)
async def quota_debit(req: QuotaDebitRequest):
    result = await debit_user_quota(req.user_id, req.action, req.units, req.ref)
    return QuotaDebitResponse(**result)

@router.post("/billing/quota/credit", response_model=QuotaCreditResponse)
async def quota_credit(req: QuotaCreditRequest):
    result = await credit_user_quota(req.user_id, req.action, req.units, req.ref)
    return QuotaCreditResponse(**result)
""" 