from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.database import TariffProperty
from app.repositories.base_dao import BaseDAO

class TariffPropertyDAO(BaseDAO[TariffProperty]):
    """DAO для работы со свойствами тарифов"""
    
    def __init__(self):
        super().__init__(TariffProperty)
    
    async def get_tariff_properties_by_plan_code(self, session: AsyncSession, plan_code: str) -> List[TariffProperty]:
        """Получить все свойства тарифа для конкретного плана"""
        result = await session.execute(
            select(TariffProperty).where(TariffProperty.plan_code == plan_code)
        )
        return result.scalars().all()
    
    async def get_tariff_property_by_plan_and_property(self, session: AsyncSession, plan_code: str, plan_property: str) -> Optional[TariffProperty]:
        """Получить свойство тарифа по коду плана и свойству"""
        result = await session.execute(
            select(TariffProperty).where(
                and_(
                    TariffProperty.plan_code == plan_code,
                    TariffProperty.plan_property == plan_property
                )
            )
        )
        return result.scalar_one_or_none()
