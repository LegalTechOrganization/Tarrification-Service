"""
Пример Pay-Service для интеграции с ЮKassa
Этот сервис обрабатывает платежи и вебхуки от ЮKassa
"""

import httpx
import asyncio
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import os
from uuid import uuid4

app = FastAPI(title="Pay-Service Example", version="1.0.0")

# Конфигурация
BILLING_SERVICE_URL = os.getenv("BILLING_SERVICE_URL", "http://localhost:8001")
BILLING_SERVICE_TOKEN = os.getenv("BILLING_SERVICE_TOKEN", "super-secret-dev")
YOO_KASSA_SHOP_ID = os.getenv("YOO_KASSA_SHOP_ID", "your_shop_id")
YOO_KASSA_SECRET_KEY = os.getenv("YOO_KASSA_SECRET_KEY", "your_secret_key")

class CreatePaymentRequest(BaseModel):
    user_id: str
    amount: float
    plan_code: Optional[str] = None
    description: str
    return_url: str
    auto_renew: bool = False

class PaymentResponse(BaseModel):
    payment_id: str
    payment_url: str
    amount: float
    status: str

class BillingServiceClient:
    """Клиент для взаимодействия с BillingTariffication-Service"""
    
    def __init__(self):
        self.base_url = BILLING_SERVICE_URL
        self.headers = {"X-Internal-Key": BILLING_SERVICE_TOKEN}
    
    async def credit_balance(self, user_id: str, amount: float, payment_id: str, plan_code: Optional[str] = None) -> Dict[str, Any]:
        """Пополнить баланс пользователя после успешного платежа"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/internal/billing/payment/webhook",
                headers=self.headers,
                json={
                    "payment_id": payment_id,
                    "user_id": user_id,
                    "amount": amount,
                    "currency": "RUB",
                    "payment_status": "succeeded",
                    "plan_code": plan_code,
                    "auto_renew": False
                }
            )
            response.raise_for_status()
            return response.json()

class YooKassaClient:
    """Клиент для работы с ЮKassa API"""
    
    def __init__(self):
        self.shop_id = YOO_KASSA_SHOP_ID
        self.secret_key = YOO_KASSA_SECRET_KEY
        self.base_url = "https://api.yookassa.ru/v3"
    
    async def create_payment(self, amount: float, description: str, return_url: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Создать платеж в ЮKassa"""
        # В реальном проекте здесь будет вызов API ЮKassa
        # Пока возвращаем заглушку
        payment_id = f"yk-{uuid4()}"
        
        return {
            "id": payment_id,
            "status": "pending",
            "paid": False,
            "amount": {
                "value": str(amount),
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "confirmation_url": f"https://yoomoney.ru/checkout/payments/v2/contract?orderId={payment_id}"
            },
            "description": description,
            "metadata": metadata
        }
    
    def verify_webhook(self, request: Request) -> Dict[str, Any]:
        """Верифицировать вебхук от ЮKassa"""
        # В реальном проекте здесь будет проверка подписи
        # Пока возвращаем заглушку
        return {
            "id": "yk-test-payment-id",
            "status": "succeeded",
            "paid": True,
            "amount": {
                "value": "750.00",
                "currency": "RUB"
            },
            "metadata": {
                "user_id": "test-user-123",
                "plan_code": "base750"
            }
        }

# Инициализация клиентов
billing_client = BillingServiceClient()
yoo_kassa_client = YooKassaClient()

@app.post("/payments/create", response_model=PaymentResponse)
async def create_payment(request: CreatePaymentRequest):
    """Создать платеж"""
    try:
        # Создаем платеж в ЮKassa
        metadata = {
            "user_id": request.user_id,
            "plan_code": request.plan_code
        }
        
        payment = await yoo_kassa_client.create_payment(
            amount=request.amount,
            description=request.description,
            return_url=request.return_url,
            metadata=metadata
        )
        
        return PaymentResponse(
            payment_id=payment["id"],
            payment_url=payment["confirmation"]["confirmation_url"],
            amount=request.amount,
            status=payment["status"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webhooks/yookassa")
async def yookassa_webhook(request: Request):
    """Вебхук от ЮKassa"""
    try:
        # Верифицируем вебхук
        payment_data = yoo_kassa_client.verify_webhook(request)
        
        if payment_data["status"] == "succeeded" and payment_data["paid"]:
            # Получаем данные из метаданных
            metadata = payment_data.get("metadata", {})
            user_id = metadata.get("user_id")
            plan_code = metadata.get("plan_code")
            amount = float(payment_data["amount"]["value"])
            
            # Пополняем баланс в BillingTariffication-Service
            result = await billing_client.credit_balance(
                user_id=user_id,
                amount=amount,
                payment_id=payment_data["id"],
                plan_code=plan_code
            )
            
            return {
                "success": True,
                "message": "Payment processed successfully",
                "billing_result": result
            }
        else:
            return {
                "success": False,
                "message": "Payment not succeeded"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {"status": "healthy", "service": "pay-service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002) 