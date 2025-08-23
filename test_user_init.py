#!/usr/bin/env python3
"""
Тестовый скрипт для проверки инициализации пользователя
"""
import asyncio
import json
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import AsyncSessionLocal
from app.services.user_init_service import UserInitService

async def test_user_init():
    """Тест инициализации пользователя"""
    print("🧪 Тестирование инициализации пользователя...")
    
    # Тестовый sub (в реальности это будет из JWT токена)
    test_sub = "test-user-123"
    
    try:
        async with AsyncSessionLocal() as session:
            user_init_service = UserInitService()
            
            # Проверяем статус до инициализации
            print(f"\n📊 Статус пользователя {test_sub} до инициализации:")
            status_before = await user_init_service.get_user_status(session, test_sub)
            print(json.dumps(status_before, indent=2, ensure_ascii=False))
            
            # Инициализируем пользователя
            print(f"\n🚀 Инициализация пользователя {test_sub}...")
            balance_created, initial_balance = await user_init_service.init_user(session, test_sub)
            print(f"✅ Баланс создан: {balance_created}")
            print(f"💰 Начальный баланс: {initial_balance}")
            
            # Проверяем статус после инициализации
            print(f"\n📊 Статус пользователя {test_sub} после инициализации:")
            status_after = await user_init_service.get_user_status(session, test_sub)
            print(json.dumps(status_after, indent=2, ensure_ascii=False))
            
            # Пробуем инициализировать еще раз (должно вернуть False)
            print(f"\n🔄 Повторная инициализация пользователя {test_sub}...")
            balance_created_again, current_balance = await user_init_service.init_user(session, test_sub)
            print(f"✅ Баланс создан: {balance_created_again}")
            print(f"💰 Текущий баланс: {current_balance}")
            
            print("\n✅ Тест завершен успешно!")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_user_init())







