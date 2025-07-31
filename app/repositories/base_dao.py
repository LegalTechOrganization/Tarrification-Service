from typing import TypeVar, Generic, Type, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.database.connection import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseDAO(Generic[ModelType]):
    """Базовый DAO класс с общими операциями CRUD"""
    
    def __init__(self, model: Type[ModelType]):
        self.model = model
    
    async def get_by_id(self, session: AsyncSession, id: str) -> Optional[ModelType]:
        """Получить запись по ID"""
        result = await session.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()
    
    async def get_all(self, session: AsyncSession, limit: int = 100) -> List[ModelType]:
        """Получить все записи с лимитом"""
        result = await session.execute(select(self.model).limit(limit))
        return result.scalars().all()
    
    async def create(self, session: AsyncSession, obj: ModelType) -> ModelType:
        """Создать новую запись"""
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj
    
    async def update(self, session: AsyncSession, id: str, **kwargs) -> Optional[ModelType]:
        """Обновить запись"""
        await session.execute(
            update(self.model).where(self.model.id == id).values(**kwargs)
        )
        await session.commit()
        return await self.get_by_id(session, id)
    
    async def delete(self, session: AsyncSession, id: str) -> bool:
        """Удалить запись"""
        result = await session.execute(
            delete(self.model).where(self.model.id == id)
        )
        await session.commit()
        return result.rowcount > 0 