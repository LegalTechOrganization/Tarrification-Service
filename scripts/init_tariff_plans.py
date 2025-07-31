import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import AsyncSessionLocal
from app.models.database import TariffPlan
from app.repositories.base_dao import BaseDAO

async def init_tariff_plans():
    """Инициализация тарифных планов"""
    print("🚀 Инициализация тарифных планов...")
    
    try:
        async with AsyncSessionLocal() as session:
            dao = BaseDAO(TariffPlan)
            
            # Создаем базовые планы
            plans = [
                {
                    "plan_code": "free",
                    "name": "Бесплатный план",
                    "monthly_units": 10.0,
                    "price_rub": 0
                },
                {
                    "plan_code": "base750",
                    "name": "Базовый план",
                    "monthly_units": 750.0,
                    "price_rub": 29900  # 299 рублей в копейках
                },
                {
                    "plan_code": "pro1500",
                    "name": "Про план",
                    "monthly_units": 1500.0,
                    "price_rub": 49900  # 499 рублей в копейках
                }
            ]
            
            for plan_data in plans:
                # Проверяем существует ли план
                existing = await session.execute(
                    f"SELECT id FROM tariff_plans WHERE plan_code = '{plan_data['plan_code']}'"
                )
                
                if not existing.scalar():
                    plan = TariffPlan(**plan_data)
                    await dao.create(session, plan)
                    print(f"✅ Создан план: {plan_data['name']}")
                else:
                    print(f"ℹ️  План {plan_data['name']} уже существует")
            
            print("✅ Инициализация завершена!")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(init_tariff_plans()) 