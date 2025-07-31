from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_db
from app.services.balance_service import BalanceService
from app.services.plan_service import PlanService
from app.models.schemas import (
    GatewayCheckBalanceRequest, GatewayDebitRequest, GatewayCreditRequest, ApplyPlanRequest,
    CheckBalanceResponse, DebitResponse, CreditResponse, BalanceResponse, ApplyPlanResponse, ErrorResponse
)
from app.config import settings

router = APIRouter(prefix="/internal/billing", tags=["billing"])

async def verify_internal_key(x_internal_key: str = Header(None)):
    """Проверка внутреннего ключа"""
    # Временно отключена проверка токена
    # if x_internal_key != settings.service_token:
    #     raise HTTPException(status_code=401, detail="Invalid internal key")
    return x_internal_key

@router.post("/check", response_model=CheckBalanceResponse)
async def check_balance(
    request: GatewayCheckBalanceRequest,
    session: AsyncSession = Depends(get_db),
    _: str = Depends(verify_internal_key)
):
    """Проверить достаточно ли средств"""
    try:
        balance_service = BalanceService()
        # Создаем внутренний запрос для check_balance
        from app.models.schemas import CheckBalanceRequest as InternalCheckRequest
        internal_request = InternalCheckRequest(
            user_id=request.user_id,
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
    _: str = Depends(verify_internal_key)
):
    """Списать средства с баланса"""
    try:
        balance_service = BalanceService()
        # Создаем внутренний запрос для debit_balance
        from app.models.schemas import DebitRequest as InternalDebitRequest
        from uuid import uuid4
        
        ref = request.ref or f"{request.action}-{uuid4()}"
        internal_request = InternalDebitRequest(
            user_id=request.user_id,
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

@router.get("/balance", response_model=BalanceResponse)
async def get_balance(
    user_id: str = Query(..., description="ID пользователя"),
    session: AsyncSession = Depends(get_db),
    _: str = Depends(verify_internal_key)
):
    """Получить баланс пользователя"""
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
    request: ApplyPlanRequest,
    session: AsyncSession = Depends(get_db),
    _: str = Depends(verify_internal_key)
):
    """Применить план к пользователю"""
    try:
        plan_service = PlanService()
        # Создаем внутренний запрос для apply_plan
        from app.models.schemas import ApplyPlanRequest as InternalApplyPlanRequest
        from uuid import uuid4
        
        ref = request.ref or f"plan-{uuid4()}"
        internal_request = InternalApplyPlanRequest(
            user_id=request.user_id,
            plan_code=request.plan_id,  # Используем plan_id как plan_code
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