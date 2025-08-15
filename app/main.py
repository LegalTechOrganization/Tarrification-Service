from fastapi import FastAPI
from app.api.routes import billing, health
from app.database.connection import init_db, close_db
from app.config import settings
from app.services.kafka_service import kafka_service
from app.handlers.billing_handlers import billing_handler
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создание FastAPI приложения
app = FastAPI(
    title="BillingTariffication-Service",
    description="Внутренний микросервис для управления тарификацией",
    version=settings.service_version
)

# Подключение роутеров
app.include_router(health.router)
app.include_router(billing.router)

# События жизненного цикла
@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    logger.info("Starting Billing Service...")
    
    # Инициализация БД
    await init_db()
    logger.info("Database initialized")
    
    # Инициализация Kafka
    try:
        await kafka_service.start()
        
        # Регистрируем consumers для billing топиков
        await kafka_service.start_consumer(
            topic="billing-balance-check",
            group_id="billing-service",
            handler=billing_handler.handle_balance_check
        )
        
        await kafka_service.start_consumer(
            topic="billing-debit",
            group_id="billing-service",
            handler=billing_handler.handle_debit
        )
        
        await kafka_service.start_consumer(
            topic="billing-credit",
            group_id="billing-service",
            handler=billing_handler.handle_credit
        )
        
        await kafka_service.start_consumer(
            topic="billing-plan-apply",
            group_id="billing-service",
            handler=billing_handler.handle_plan_apply
        )
        
        logger.info("Kafka consumers started for all billing topics")
        
    except Exception as e:
        logger.error(f"Failed to start Kafka: {e}")
        # Можно продолжить работу без Kafka для HTTP fallback
        
    logger.info("Billing Service startup completed")

@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при остановке"""
    logger.info("Shutting down Billing Service...")
    
    # Остановка Kafka
    try:
        await kafka_service.stop()
        logger.info("Kafka service stopped")
    except Exception as e:
        logger.error(f"Error stopping Kafka: {e}")
    
    # Закрытие БД
    await close_db()
    logger.info("Database closed")
    
    logger.info("Billing Service shutdown completed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    ) 