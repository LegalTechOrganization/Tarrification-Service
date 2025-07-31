from fastapi import FastAPI
from app.api.routes import billing, health
from app.database.connection import init_db, close_db
from app.config import settings

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
    await init_db()

@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при остановке"""
    await close_db()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    ) 