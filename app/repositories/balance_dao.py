from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.database import UserBalance
from app.repositories.base_dao import BaseDAO

class BalanceDAO(BaseDAO[UserBalance]):
    """DAO для работы с балансом пользователей"""
    
    def __init__(self):
        super().__init__(UserBalance)
    
    async def get_by_sub(self, session: AsyncSession, sub: str) -> Optional[UserBalance]:
        """Получить баланс пользователя по sub"""
        result = await session.execute(
            select(UserBalance).where(UserBalance.sub == sub)
        )
        return result.scalar_one_or_none()
    
    async def get_or_create_balance(self, session: AsyncSession, sub: str) -> UserBalance:
        """Получить или создать баланс пользователя"""
        balance = await self.get_by_sub(session, sub)
        
        if not balance:
            balance = UserBalance(
                sub=sub,
                balance_units=0.0
            )
            balance = await self.create(session, balance)
        
        return balance
    
    async def update_balance(self, session: AsyncSession, sub: str, new_balance: float) -> UserBalance:
        """Обновить баланс пользователя"""
        await session.execute(
            UserBalance.__table__.update().where(
                UserBalance.sub == sub
            ).values(balance_units=new_balance)
        )
        await session.commit()
        
        return await self.get_by_sub(session, sub) 