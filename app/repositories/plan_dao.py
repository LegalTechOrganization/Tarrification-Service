from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.database import UserPlan, TariffPlan
from app.repositories.base_dao import BaseDAO
from datetime import datetime, timedelta

class PlanDAO(BaseDAO[UserPlan]):
    """DAO для работы с планами пользователей"""
    
    def __init__(self):
        super().__init__(UserPlan)
    
    async def get_active_plan_by_user(self, session: AsyncSession, user_id: str) -> Optional[UserPlan]:
        """Получить активный план пользователя"""
        result = await session.execute(
            select(UserPlan).where(
                and_(
                    UserPlan.user_id == user_id,
                    UserPlan.is_active == True,
                    UserPlan.expires_at > datetime.utcnow()
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_tariff_plan(self, session: AsyncSession, plan_code: str) -> Optional[TariffPlan]:
        """Получить тарифный план по коду"""
        result = await session.execute(
            select(TariffPlan).where(
                and_(
                    TariffPlan.plan_code == plan_code,
                    TariffPlan.is_active == True
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def apply_plan(self, session: AsyncSession, user_id: str, plan_code: str, 
                        ref: str, auto_renew: bool = False) -> UserPlan:
        """Применить план к пользователю"""
        # Деактивируем старые планы
        await self.deactivate_user_plans(session, user_id)
        
        # Получаем тарифный план
        tariff_plan = await self.get_tariff_plan(session, plan_code)
        if not tariff_plan:
            raise ValueError(f"Tariff plan not found: {plan_code}")
        
        # Создаем новый план пользователя
        now = datetime.utcnow()
        expires_at = now + timedelta(days=30)  # Месячный план
        
        user_plan = UserPlan(
            user_id=user_id,
            plan_code=plan_code,
            started_at=now,
            expires_at=expires_at,
            auto_renew=auto_renew,
            is_active=True
        )
        
        return await self.create(session, user_plan)
    
    async def deactivate_user_plans(self, session: AsyncSession, user_id: str) -> None:
        """Деактивировать все планы пользователя"""
        await session.execute(
            UserPlan.__table__.update().where(
                and_(
                    UserPlan.user_id == user_id,
                    UserPlan.is_active == True
                )
            ).values(is_active=False)
        )
        await session.commit() 