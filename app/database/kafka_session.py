"""
Вспомогательная функция для получения DB сессии в Kafka handlers
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from app.database.connection import engine

# Создаем session maker для Kafka handlers
AsyncSessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

async def get_db_session() -> AsyncSession:
    """Получить новую сессию БД для Kafka обработчиков"""
    async with AsyncSessionLocal() as session:
        return session
