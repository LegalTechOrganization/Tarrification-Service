from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.database import BalanceTransaction
from app.repositories.base_dao import BaseDAO

class TransactionDAO(BaseDAO[BalanceTransaction]):
    """DAO для работы с транзакциями баланса"""
    
    def __init__(self):
        super().__init__(BalanceTransaction)
    
    async def get_by_ref_and_direction(self, session: AsyncSession, sub: str, 
                                      ref: str, direction: str) -> Optional[BalanceTransaction]:
        """Получить транзакцию по ref и direction (для идемпотентности)"""
        result = await session.execute(
            select(BalanceTransaction).where(
                and_(
                    BalanceTransaction.sub == sub,
                    BalanceTransaction.ref == ref,
                    BalanceTransaction.direction == direction
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def create_transaction(self, session: AsyncSession, sub: str, direction: str,
                               units: float, ref: str, reason: str, 
                               source_service: str = None) -> BalanceTransaction:
        """Создать новую транзакцию"""
        transaction = BalanceTransaction(
            sub=sub,
            direction=direction,
            units=units,
            ref=ref,
            reason=reason,
            source_service=source_service
        )
        
        return await self.create(session, transaction) 