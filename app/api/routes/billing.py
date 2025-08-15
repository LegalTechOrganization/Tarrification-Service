from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_db
from app.services.balance_service import BalanceService
from app.services.plan_service import PlanService
from app.models.schemas import (
    GatewayCheckBalanceRequest, GatewayDebitRequest, GatewayCreditRequest, GatewayApplyPlanRequest, GatewayGetBalanceRequest,
    ApplyPlanRequest, CheckBalanceResponse, DebitResponse, CreditResponse, BalanceResponse, ApplyPlanResponse, ErrorResponse,
    PaymentWebhookRequest, PaymentWebhookResponse, CreatePaymentRequest, CreatePaymentResponse,
    GatewayAuthContext
)
from app.middleware.auth_middleware import verify_gateway_auth, verify_internal_key, get_user_from_context
from app.config import settings
from uuid import uuid4

router = APIRouter(prefix="/internal/billing", tags=["billing"])

# Legacy function - moved to middleware
# Используется verify_internal_key из middleware для обратной совместимости

@router.post("/check", response_model=CheckBalanceResponse)
async def check_balance(
    request: GatewayCheckBalanceRequest,
    session: AsyncSession = Depends(get_db),
    auth_context: GatewayAuthContext = Depends(verify_gateway_auth)
):
    """Проверить достаточно ли средств (через Gateway аутентификацию)"""
    try:
        # Получаем пользователя из контекста
        user = await get_user_from_context(auth_context)
        
        balance_service = BalanceService()
        # Создаем внутренний запрос для check_balance
        from app.models.schemas import CheckBalanceRequest as InternalCheckRequest
        internal_request = InternalCheckRequest(
            user_id=user.user_id,
            units=request.units
        )
        allowed, balance = await balance_service.check_balance(session, internal_request)
        
        return CheckBalanceResponse(
            allowed=allowed,
            balance=balance
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/debit", response_model=DebitResponse)
async def debit_balance(
    request: GatewayDebitRequest,
    session: AsyncSession = Depends(get_db),
    auth_context: GatewayAuthContext = Depends(verify_gateway_auth)
):
    """Списать средства с баланса (через Gateway аутентификацию)"""
    try:
        # Получаем пользователя из контекста
        user = await get_user_from_context(auth_context)
        
        balance_service = BalanceService()
        # Создаем внутренний запрос для debit_balance
        from app.models.schemas import DebitRequest as InternalDebitRequest
        from uuid import uuid4
        
        ref = request.ref or f"{request.action}-{uuid4()}"
        internal_request = InternalDebitRequest(
            user_id=user.user_id,
            units=request.units,
            ref=ref,
            reason=request.reason
        )
        new_balance, tx_id = await balance_service.debit_balance(session, internal_request)
        
        return DebitResponse(
            balance=new_balance,
            tx_id=tx_id
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/credit", response_model=CreditResponse)
async def credit_balance(
    request: GatewayCreditRequest,
    session: AsyncSession = Depends(get_db),
    _: str = Depends(verify_internal_key)
):
    """Пополнить баланс"""
    try:
        balance_service = BalanceService()
        # Создаем внутренний запрос для credit_balance
        from app.models.schemas import CreditRequest as InternalCreditRequest
        from uuid import uuid4
        
        ref = request.ref or f"{request.action}-{uuid4()}"
        internal_request = InternalCreditRequest(
            user_id=request.user_id,
            units=request.units,
            ref=ref,
            reason=request.reason,
            source_service=request.source_service or "gateway"
        )
        new_balance, tx_id = await balance_service.credit_balance(session, internal_request)
        
        return CreditResponse(
            balance=new_balance,
            tx_id=tx_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/balance", response_model=BalanceResponse)
async def get_balance(
    request: GatewayGetBalanceRequest,
    session: AsyncSession = Depends(get_db),
    auth_context: GatewayAuthContext = Depends(verify_gateway_auth)
):
    """Получить баланс пользователя (через Gateway аутентификацию)"""
    try:
        # Получаем пользователя из контекста
        user = await get_user_from_context(auth_context)
        
        balance_service = BalanceService()
        plan_service = PlanService()
        
        balance = await balance_service.get_balance(session, user.user_id)
        plan_info = await plan_service.get_user_plan_info(session, user.user_id)
        
        # Если план не найден, создаем пустой план
        if plan_info is None:
            plan_info = {
                "plan_code": "none",
                "status": "inactive",
                "expires_at": None
            }
        
        return BalanceResponse(
            balance=balance,
            plan=plan_info
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Legacy endpoint для обратной совместимости
@router.get("/balance", response_model=BalanceResponse)
async def get_balance_legacy(
    user_id: str = Query(..., description="ID пользователя"),
    session: AsyncSession = Depends(get_db),
    _: str = Depends(verify_internal_key)
):
    """Получить баланс пользователя (legacy endpoint)"""
    try:
        balance_service = BalanceService()
        plan_service = PlanService()
        
        balance = await balance_service.get_balance(session, user_id)
        plan_info = await plan_service.get_user_plan_info(session, user_id)
        
        # Если план не найден, создаем пустой план
        if plan_info is None:
            plan_info = {
                "plan_code": "none",
                "status": "inactive",
                "expires_at": None
            }
        
        return BalanceResponse(
            balance=balance,
            plan=plan_info
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/plan/apply", response_model=ApplyPlanResponse)
async def apply_plan(
    request: GatewayApplyPlanRequest,
    session: AsyncSession = Depends(get_db),
    auth_context: GatewayAuthContext = Depends(verify_gateway_auth)
):
    """Применить план к пользователю (через Gateway аутентификацию)"""
    try:
        # Получаем пользователя из контекста
        user = await get_user_from_context(auth_context)
        
        plan_service = PlanService()
        # Создаем внутренний запрос для apply_plan
        from app.models.schemas import ApplyPlanRequest as InternalApplyPlanRequest
        from uuid import uuid4
        
        ref = request.ref or f"plan-{uuid4()}"
        internal_request = InternalApplyPlanRequest(
            user_id=user.user_id,
            plan_code=request.plan_code,
            ref=ref,
            auto_renew=request.auto_renew
        )
        plan_id, new_balance = await plan_service.apply_plan(session, internal_request)
        
        return ApplyPlanResponse(
            plan_id=plan_id,
            new_balance=new_balance
        )
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                code="plan_not_found",
                detail=str(e)
            ).dict()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 

@router.post("/payment/webhook", response_model=PaymentWebhookResponse)
async def payment_webhook(
    request: PaymentWebhookRequest,
    session: AsyncSession = Depends(get_db),
    _: str = Depends(verify_internal_key)
):
    """Вебхук от Pay-Service для подтверждения платежа от ЮKassa"""
    try:
        balance_service = BalanceService()
        plan_service = PlanService()
        
        # Проверяем статус платежа
        if request.payment_status != "succeeded":
            raise HTTPException(status_code=400, detail="Payment not succeeded")
        
        # Если это покупка тарифного плана
        if request.plan_code:
            # Применяем план и начисляем средства
            plan_request = ApplyPlanRequest(
                user_id=request.user_id,
                plan_code=request.plan_code,
                ref=request.payment_id,
                auto_renew=request.auto_renew
            )
            plan_result = await plan_service.apply_plan(session, plan_request)
            
            return PaymentWebhookResponse(
                success=True,
                new_balance=plan_result["new_balance"],
                plan_id=plan_result["plan_id"],
                message="Plan applied successfully"
            )
        else:
            # Обычное пополнение баланса
            from app.models.schemas import CreditRequest as InternalCreditRequest
            credit_request = InternalCreditRequest(
                user_id=request.user_id,
                units=request.amount,
                ref=request.payment_id,
                reason=f"payment_{request.payment_id}",
                source_service="payment"
            )
            new_balance, tx_id = await balance_service.credit_balance(session, credit_request)
            
            return PaymentWebhookResponse(
                success=True,
                new_balance=new_balance,
                tx_id=tx_id,
                message="Balance credited successfully"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/payment/create", response_model=CreatePaymentResponse)
async def create_payment(
    request: CreatePaymentRequest,
    session: AsyncSession = Depends(get_db),
    _: str = Depends(verify_internal_key)
):
    """Создание платежа (делегируется в Pay-Service)"""
    try:
        # Здесь должна быть логика создания платежа через Pay-Service
        # Пока возвращаем заглушку
        payment_id = f"yk-{uuid4()}"
        
        return CreatePaymentResponse(
            payment_id=payment_id,
            payment_url="https://yoomoney.ru/checkout/payments/v2/contract",
            amount=request.amount,
            currency="RUB",
            status="pending"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 