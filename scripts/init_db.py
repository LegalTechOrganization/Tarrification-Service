#!/usr/bin/env python3
"""
Скрипт для инициализации базы данных
"""

import asyncio
import sys
import os

# Добавляем корневую директорию в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import engine
from app.models.database import Base


async def init_database():
    """Создание всех таблиц в базе данных"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ База данных успешно инициализирована")
    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(init_database()) 