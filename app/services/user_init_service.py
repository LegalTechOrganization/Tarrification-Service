from typing import Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.balance_dao import BalanceDAO
from app.repositories.plan_dao import PlanDAO
from app.models.database import UserBalance, UserPlan
from fastapi import HTTPException

class UserInitService:
    """Сервис для инициализации пользователя с дефолтными данными"""
    
    def __init__(self):
        self.balance_dao = BalanceDAO()
        self.plan_dao = PlanDAO()
    
    async def init_user(self, session: AsyncSession, sub: str) -> Tuple[bool, float]:
        """
        Инициализировать пользователя с дефолтными данными
        
        Args:
            session: Сессия базы данных
            sub: Уникальный идентификатор пользователя из JWT токена
            
        Returns:
            Tuple[bool, float]: (создан_ли_баланс, начальный_баланс)
        """
        try:
            # Проверяем, существует ли уже баланс пользователя
            existing_balance = await self.balance_dao.get_by_sub(session, sub)
            
            if existing_balance:
                # Пользователь уже инициализирован
                return False, existing_balance.balance_units
            
            # Создаем новый баланс с дефолтными значениями
            initial_balance = 0.0  # Можно изменить на другое значение по умолчанию
            
            new_balance = UserBalance(
                sub=sub,
                balance_units=initial_balance
            )
            
            await self.balance_dao.create(session, new_balance)
            
            # Создаем дефолтный план пользователя
            now = datetime.utcnow()
            expires_at = now + timedelta(days=365)  # Текущая дата + год
            
            default_plan = UserPlan(
                sub=sub,
                plan_code="0000",  # Дефолтный план
                started_at=now,
                expires_at=expires_at,
                auto_renew=True,
                is_active=True
            )
            
            await self.plan_dao.create(session, default_plan)
            
            return True, initial_balance
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize user: {str(e)}"
            )
    
    async def get_user_status(self, session: AsyncSession, sub: str) -> dict:
        """
        Получить статус инициализации пользователя
        
        Args:
            session: Сессия базы данных
            sub: Уникальный идентификатор пользователя из JWT токена
            
        Returns:
            dict: Статус пользователя
        """
        try:
            balance = await self.balance_dao.get_by_sub(session, sub)
            active_plan = await self.plan_dao.get_active_plan_by_user(session, sub)
            
            return {
                "sub": sub,
                "balance_exists": balance is not None,
                "balance_amount": balance.balance_units if balance else 0.0,
                "has_active_plan": active_plan is not None,
                "active_plan_code": active_plan.plan_code if active_plan else None,
                "is_initialized": balance is not None
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get user status: {str(e)}"
            )







