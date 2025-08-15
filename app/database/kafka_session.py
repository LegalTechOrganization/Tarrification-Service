"""
Вспомогательная функция для получения DB сессии в Kafka handlers
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import async_engine
from sqlalchemy.orm import sessionmaker

# Создаем session maker для Kafka handlers
async_session = sessionmaker(
    async_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

async def get_db_session() -> AsyncSession:
    """Получить новую сессию БД для Kafka обработчиков"""
    session = async_session()
    return session
