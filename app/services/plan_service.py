from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.plan_dao import PlanDAO
from app.services.balance_service import BalanceService
from app.models.schemas import ApplyPlanRequest, CreditRequest

class PlanService:
    """Сервис для работы с планами пользователей"""
    
    def __init__(self):
        self.plan_dao = PlanDAO()
        self.balance_service = BalanceService()
    
    async def apply_plan(self, session: AsyncSession, request: ApplyPlanRequest) -> Tuple[str, float]:
        """Применить план к пользователю"""
        # Получаем тарифный план
        tariff_plan = await self.plan_dao.get_tariff_plan(session, request.plan_code)
        if not tariff_plan:
            raise ValueError(f"Tariff plan not found: {request.plan_code}")
        
        # Применяем план
        user_plan = await self.plan_dao.apply_plan(
            session, request.sub, request.plan_code, request.ref, request.auto_renew
        )
        
        # Начисляем месячные единицы
        credit_request = CreditRequest(
            sub=request.sub,
            units=tariff_plan.monthly_units,
            ref=request.ref,
            source_service="plan_activation",
            reason=f"plan_{request.plan_code}"
        )
        
        new_balance, _ = await self.balance_service.credit_balance(session, credit_request)
        
        return user_plan.id, new_balance
    
    async def get_user_plan_info(self, session: AsyncSession, sub: str) -> Optional[dict]:
        """Получить информацию о плане пользователя"""
        user_plan = await self.plan_dao.get_active_plan_by_user(session, sub)
        
        if not user_plan:
            return None
        
        return {
            "plan_code": user_plan.plan_code,
            "expires_at": user_plan.expires_at.isoformat(),
            "status": "active" if user_plan.is_active else "inactive"
        } 