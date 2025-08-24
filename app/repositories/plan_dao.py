from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, join
from app.models.database import UserPlan, TariffPlan, UserBalance, TariffProperty
from app.repositories.base_dao import BaseDAO
from datetime import datetime, timedelta

class PlanDAO(BaseDAO[UserPlan]):
    """DAO для работы с планами пользователей"""
    
    def __init__(self):
        super().__init__(UserPlan)
    
    async def get_active_plan_by_user(self, session: AsyncSession, sub: str) -> Optional[UserPlan]:
        """Получить активный план пользователя"""
        result = await session.execute(
            select(UserPlan).where(
                and_(
                    UserPlan.sub == sub,
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
    
    async def apply_plan(self, session: AsyncSession, sub: str, plan_code: str, 
                        ref: str, auto_renew: bool = False) -> UserPlan:
        """Применить план к пользователю"""
        # Деактивируем старые планы
        await self.deactivate_user_plans(session, sub)
        
        # Получаем тарифный план
        tariff_plan = await self.get_tariff_plan(session, plan_code)
        if not tariff_plan:
            raise ValueError(f"Tariff plan not found: {plan_code}")
        
        # Создаем новый план пользователя
        now = datetime.utcnow()
        expires_at = now + timedelta(days=30)  # Месячный план
        
        user_plan = UserPlan(
            sub=sub,
            plan_code=plan_code,
            started_at=now,
            expires_at=expires_at,
            auto_renew=auto_renew,
            is_active=True
        )
        
        return await self.create(session, user_plan)
    
    async def deactivate_user_plans(self, session: AsyncSession, sub: str) -> None:
        """Деактивировать все планы пользователя"""
        await session.execute(
            UserPlan.__table__.update().where(
                and_(
                    UserPlan.sub == sub,
                    UserPlan.is_active == True
                )
            ).values(is_active=False)
        )
        await session.commit()
    
    async def get_user_subscription_details(self, session: AsyncSession, sub: str) -> Optional[Dict[str, Any]]:
        """Получить детальную информацию о подписке пользователя с JOIN тарифного плана и балансом"""
        # Создаем JOIN между UserPlan и TariffPlan
        j = join(UserPlan, TariffPlan, UserPlan.plan_code == TariffPlan.plan_code)
        
        # Выбираем все нужные поля
        query = select(
            UserPlan.id,
            UserPlan.sub.label('user_id'),
            UserPlan.plan_code,
            UserPlan.started_at,
            UserPlan.expires_at,
            UserPlan.auto_renew,
            UserPlan.created_at,
            TariffPlan.name,
            TariffPlan.monthly_units,
            TariffPlan.price_rub,
            TariffPlan.is_active.label('plan_is_active'),
            TariffPlan.created_at.label('plan_created_at')
        ).select_from(j).where(
            and_(
                UserPlan.sub == sub,
                UserPlan.is_active == True,
                UserPlan.expires_at > datetime.utcnow()
            )
        )
        
        result = await session.execute(query)
        row = result.fetchone()
        
        if not row:
            return None
        
        # Получаем баланс пользователя
        balance_query = select(UserBalance.balance_units).where(UserBalance.sub == sub)
        balance_result = await session.execute(balance_query)
        balance_row = balance_result.scalar_one_or_none()
        remaining_units = balance_row if balance_row is not None else 0.0
        
        # Получаем свойства тарифа для плана пользователя
        tariff_properties_query = select(TariffProperty.plan_property).where(TariffProperty.plan_code == row.plan_code)
        tariff_properties_result = await session.execute(tariff_properties_query)
        tariff_properties = tariff_properties_result.scalars().all()
        
        # Определяем статус подписки
        now = datetime.utcnow()
        # Приводим к наивному datetime для сравнения
        expires_at_naive = row.expires_at.replace(tzinfo=None) if row.expires_at.tzinfo else row.expires_at
        if expires_at_naive <= now:
            status = "expired"
        elif not row.auto_renew:
            status = "cancelled"
        else:
            status = "active"
        
        return {
            "id": str(row.id),
            "user_id": row.user_id,
            "plan_code": row.plan_code,
            "started_at": row.started_at.isoformat() + "Z",
            "expires_at": row.expires_at.isoformat() + "Z",
            "auto_renew": row.auto_renew,
            "status": status,
            "created_at": row.created_at.isoformat() + "Z",
            "remaining_units": remaining_units,
            "next_debit": row.expires_at.isoformat() + "Z",
            "tariff_properties": tariff_properties,
            "plan": {
                "plan_code": row.plan_code,
                "name": row.name,
                "monthly_units": row.monthly_units,
                "price_rub": row.price_rub,
                "is_active": row.plan_is_active,
                "created_at": row.plan_created_at.isoformat() + "Z"
            }
        } 