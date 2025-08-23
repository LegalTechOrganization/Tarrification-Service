from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_db
from app.services.balance_service import BalanceService
from app.services.plan_service import PlanService
from app.services.user_init_service import UserInitService
from app.models.schemas import (
    GatewayCheckBalanceRequest, GatewayDebitRequest, GatewayCreditRequest, GatewayApplyPlanRequest, GatewayGetBalanceRequest,
    ApplyPlanRequest, CheckBalanceResponse, DebitResponse, CreditResponse, BalanceResponse, 
    ApplyPlanResponse, InitUserResponse, ErrorResponse, PaymentWebhookRequest, PaymentWebhookResponse, 
    CreatePaymentRequest, CreatePaymentResponse, UserSubscriptionResponse, GatewayAuthContext
)
from app.middleware.auth_middleware import verify_gateway_auth, verify_internal_key, get_user_from_context
from app.config import settings
from uuid import uuid4

router = APIRouter(prefix="/internal/billing", tags=["billing"])


# Упрощенная функция для получения sub из JWT токена
async def get_user_sub(auth_context: GatewayAuthContext = Depends(verify_gateway_auth)) -> str:
    """Получить sub пользователя из JWT токена"""
    user = await get_user_from_context(auth_context)
    return user.sub


@router.post("/check", response_model=CheckBalanceResponse)
async def check_balance(
    request: GatewayCheckBalanceRequest,
    session: AsyncSession = Depends(get_db),
    sub: str = Depends(get_user_sub)
):
    """Проверить достаточно ли средств"""
    balance_service = BalanceService()
    from app.models.schemas import CheckBalanceRequest as InternalCheckRequest
    
    internal_request = InternalCheckRequest(
        sub=sub,
        units=request.units
    )
    allowed, balance = await balance_service.check_balance(session, internal_request)
    
    return CheckBalanceResponse(allowed=allowed, balance=balance)


@router.post("/debit", response_model=DebitResponse)
async def debit_balance(
    request: GatewayDebitRequest,
    session: AsyncSession = Depends(get_db),
    sub: str = Depends(get_user_sub)
):
    """Списать средства с баланса"""
    balance_service = BalanceService()
    from app.models.schemas import DebitRequest as InternalDebitRequest
    
    ref = request.ref or f"{request.action}-{uuid4()}"
    internal_request = InternalDebitRequest(
        sub=sub,
        units=request.units,
        ref=ref,
        reason=request.reason
    )
    new_balance, tx_id = await balance_service.debit_balance(session, internal_request)
    
    return DebitResponse(balance=new_balance, tx_id=tx_id)


@router.post("/credit", response_model=CreditResponse)
async def credit_balance(
    request: GatewayCreditRequest,
    session: AsyncSession = Depends(get_db),
    sub: str = Depends(get_user_sub)
):
    """Пополнить баланс"""
    balance_service = BalanceService()
    from app.models.schemas import CreditRequest as InternalCreditRequest
    
    ref = request.ref or f"{request.action}-{uuid4()}"
    internal_request = InternalCreditRequest(
        sub=sub,
        units=request.units,
        ref=ref,
        reason=request.reason,
        source_service=request.source_service or "gateway"
    )
    new_balance, tx_id = await balance_service.credit_balance(session, internal_request)
    
    return CreditResponse(balance=new_balance, tx_id=tx_id)


@router.post("/balance", response_model=BalanceResponse)
async def get_balance(
    request: GatewayGetBalanceRequest,
    session: AsyncSession = Depends(get_db),
    sub: str = Depends(get_user_sub)
):
    """Получить баланс пользователя"""
    balance_service = BalanceService()
    plan_service = PlanService()
    
    balance = await balance_service.get_balance(session, sub)
    plan_info = await plan_service.get_user_plan_info(session, sub)
    
    # Если план не найден, создаем пустой план
    if plan_info is None:
        plan_info = {
            "plan_code": "none",
            "status": "inactive",
            "expires_at": None
        }
    
    return BalanceResponse(balance=balance, plan=plan_info)


@router.post("/user/init", response_model=InitUserResponse)
async def init_user(
    session: AsyncSession = Depends(get_db),
    sub: str = Depends(get_user_sub)
):
    """Инициализировать пользователя с дефолтными данными"""
    user_init_service = UserInitService()
    balance_created, initial_balance = await user_init_service.init_user(session, sub)
    
    if balance_created:
        message = f"User initialized successfully with initial balance: {initial_balance}"
    else:
        message = f"User already initialized. Current balance: {initial_balance}"
    
    return InitUserResponse(
        success=True,
        user_id=sub,
        balance_created=balance_created,
        initial_balance=initial_balance,
        message=message
    )


@router.get("/user/status")
async def get_user_status(
    session: AsyncSession = Depends(get_db),
    sub: str = Depends(get_user_sub)
):
    """Получить статус инициализации пользователя"""
    user_init_service = UserInitService()
    status = await user_init_service.get_user_status(session, sub)
    return status


@router.post("/plan/apply", response_model=ApplyPlanResponse)
async def apply_plan(
    request: GatewayApplyPlanRequest,
    session: AsyncSession = Depends(get_db),
    sub: str = Depends(get_user_sub)
):
    """Применить план к пользователю"""
    plan_service = PlanService()
    from app.models.schemas import ApplyPlanRequest as InternalApplyPlanRequest
    
    ref = request.ref or f"plan-{uuid4()}"
    internal_request = InternalApplyPlanRequest(
        sub=sub,
        plan_code=request.plan_code,
        ref=ref,
        auto_renew=request.auto_renew
    )
    plan_id, new_balance = await plan_service.apply_plan(session, internal_request)
    
    return ApplyPlanResponse(plan_id=plan_id, new_balance=new_balance)


@router.get("/subscription", response_model=UserSubscriptionResponse)
async def get_user_subscription(
    session: AsyncSession = Depends(get_db),
    sub: str = Depends(get_user_sub)
):
    """Получить детальную информацию о подписке пользователя"""
    from app.repositories.plan_dao import PlanDAO
    
    plan_dao = PlanDAO()
    subscription_data = await plan_dao.get_user_subscription_details(session, sub)
    
    if not subscription_data:
        raise HTTPException(
            status_code=404,
            detail="Active subscription not found"
        )
    
    return UserSubscriptionResponse(**subscription_data)


@router.post("/payment/webhook", response_model=PaymentWebhookResponse)
async def payment_webhook(
    request: PaymentWebhookRequest,
    session: AsyncSession = Depends(get_db),
    _: str = Depends(verify_internal_key)
):
    """Вебхук от Pay-Service для подтверждения платежа от ЮKassa"""
    balance_service = BalanceService()
    plan_service = PlanService()
    
    # Проверяем статус платежа
    if request.payment_status != "succeeded":
        raise HTTPException(status_code=400, detail="Payment not succeeded")
    
    # Если это покупка тарифного плана
    if request.plan_code:
        # Применяем план и начисляем средства
        plan_request = ApplyPlanRequest(
            sub=request.sub,
            plan_code=request.plan_code,
            ref=request.payment_id,
            auto_renew=request.auto_renew
        )
        plan_id, new_balance = await plan_service.apply_plan(session, plan_request)
        
        return PaymentWebhookResponse(
            success=True,
            new_balance=new_balance,
            plan_id=plan_id,
            message="Plan applied successfully"
        )
    else:
        # Обычное пополнение баланса
        from app.models.schemas import CreditRequest as InternalCreditRequest
        credit_request = InternalCreditRequest(
            sub=request.sub,
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


@router.post("/payment/create", response_model=CreatePaymentResponse)
async def create_payment(
    request: CreatePaymentRequest,
    session: AsyncSession = Depends(get_db),
    _: str = Depends(verify_internal_key)
):
    """Создание платежа (делегируется в Pay-Service)"""
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