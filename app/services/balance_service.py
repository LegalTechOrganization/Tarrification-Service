from typing import Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.balance_dao import BalanceDAO
from app.repositories.transaction_dao import TransactionDAO
from app.models.schemas import CheckBalanceRequest, DebitRequest, CreditRequest
from fastapi import HTTPException

class BalanceService:
    """Сервис для работы с балансом пользователей"""
    
    def __init__(self):
        self.balance_dao = BalanceDAO()
        self.transaction_dao = TransactionDAO()
    
    async def check_balance(self, session: AsyncSession, request: CheckBalanceRequest) -> Tuple[bool, float]:
        """Проверить достаточно ли средств"""
        balance = await self.balance_dao.get_or_create_balance(session, request.sub)
        return balance.balance_units >= request.units, balance.balance_units
    
    async def debit_balance(self, session: AsyncSession, request: DebitRequest) -> Tuple[float, str]:
        """Списать средства с баланса"""
        # Проверяем идемпотентность
        existing_tx = await self.transaction_dao.get_by_ref_and_direction(
            session, request.sub, request.ref, "debit"
        )
        if existing_tx:
            # Возвращаем существующую транзакцию
            balance = await self.balance_dao.get_by_sub(session, request.sub)
            return balance.balance_units, existing_tx.id
        
        # Получаем баланс с блокировкой
        balance = await self.balance_dao.get_or_create_balance(session, request.sub)
        
        # Проверяем достаточно ли средств
        if balance.balance_units < request.units:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "quota_exceeded",
                    "detail": f"Insufficient balance. Required: {request.units}, available: {balance.balance_units}"
                }
            )
        
        # Списываем средства
        new_balance = balance.balance_units - request.units
        await self.balance_dao.update_balance(session, request.sub, new_balance)
        
        # Создаем транзакцию
        transaction = await self.transaction_dao.create_transaction(
            session=session,
            sub=request.sub,
            direction="debit",
            units=request.units,
            ref=request.ref,
            reason=request.reason
        )
        
        return new_balance, transaction.id
    
    async def credit_balance(self, session: AsyncSession, request: CreditRequest) -> Tuple[float, str]:
        """Пополнить баланс"""
        # Проверяем идемпотентность
        existing_tx = await self.transaction_dao.get_by_ref_and_direction(
            session, request.sub, request.ref, "credit"
        )
        if existing_tx:
            # Возвращаем существующую транзакцию
            balance = await self.balance_dao.get_by_sub(session, request.sub)
            return balance.balance_units, existing_tx.id
        
        # Получаем или создаем баланс
        balance = await self.balance_dao.get_or_create_balance(session, request.sub)
        
        # Пополняем баланс
        new_balance = balance.balance_units + request.units
        await self.balance_dao.update_balance(session, request.sub, new_balance)
        
        # Создаем транзакцию
        transaction = await self.transaction_dao.create_transaction(
            session=session,
            sub=request.sub,
            direction="credit",
            units=request.units,
            ref=request.ref,
            reason=request.reason,
            source_service=request.source_service
        )
        
        return new_balance, transaction.id
    
    async def get_balance(self, session: AsyncSession, sub: str) -> float:
        """Получить текущий баланс пользователя"""
        balance = await self.balance_dao.get_or_create_balance(session, sub)
        return balance.balance_units 